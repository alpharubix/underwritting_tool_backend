import json
import random
from asyncio import start_server
from datetime import datetime, timezone, timedelta
import asyncpg
from bson import ObjectId
from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from utils.auth_utility import hash_password, get_auth_dict,verify_password, create_access_token,is_password_valid
from utils.user_utility import get_user_dict
from controller.backgroud_task_controller import send_reset_email_to_user
import dotenv
dotenv.load_dotenv()
import os
from datetime import datetime, timezone
import uuid

async def register_user(
    input_data: dict,
    postgres_conn: asyncpg.Connection,
    mongodb_database: AsyncIOMotorDatabase,
    background_tasks: BackgroundTasks
) -> dict:


    company_name = input_data.get('company_name')
    gst_number = input_data.get('gst_number',None)
    email_id = input_data.get('email_id')
    account_owner_id = os.getenv("ACCOUNT_OWNER_ID")
    created_by_id = os.getenv("CREATED_BY_ID")
    phone_no = input_data.get("phone_no")
    customer_name = input_data.get('customer_name')
    password = input_data.get('password')
    is_from_crm = input_data.get('is_from_crm_account', False)

    try:
        user_collection = mongodb_database['users']
        auth_collection = mongodb_database['auth']
        user = await user_collection.find_one({'phone': phone_no})
        print("This is user", user)

        if user:
            return JSONResponse(status_code=409, content={'message': 'User already exists!'})

        if is_from_crm:
            account_id = input_data.get('account_id')
            if not account_id:
                return HTTPException(status_code=400, detail={"message": "account_id is required"})

            hashed_password = hash_password(password)

            user = get_user_dict(account_id, email_id, phone_no, company_name, gst_number, customer_name)
            auth = get_auth_dict(user.get("_id"), hashed_password)

            await user_collection.insert_one(user)
            await auth_collection.insert_one(auth)

            return JSONResponse(  # FIX: was missing closing parenthesis
                status_code=201,
                content={
                    'message': 'User registered successfully!',
                    'data': {'email': f"{email_id}", 'password': f"{password}"}
                }
            )

        else:
            existing_account = await postgres_conn.fetchrow(
                """
                SELECT id FROM accounts
                WHERE RIGHT(phone, 10) = RIGHT($1, 10)
                """,
                phone_no
            )
            print("Existing_accounts", existing_account)

            if existing_account:
                account_id = existing_account['id']
            else:
                account_id = await postgres_conn.fetchval(
                    """
                    INSERT INTO accounts (
                        account_name,
                        email,
                        phone,
                        account_owner_id,
                        created_time,
                        custom_fields,
                        created_by_id
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                    RETURNING id
                    """,
                    company_name,
                    email_id,
                    phone_no,
                    int(account_owner_id),
                    datetime.now(timezone.utc),
                    json.dumps({"gst_number": gst_number, "customer_name": customer_name}),
                    int(created_by_id)
                )

            hashed_password = hash_password(password)

            user = get_user_dict(account_id,email_id, phone_no, company_name, gst_number, customer_name)
            auth = get_auth_dict(user.get("_id"), hashed_password,email_id)

            await user_collection.insert_one(user)
            await auth_collection.insert_one(auth)

            # background_tasks.add_task(
            #     send_registration_mail_to_user,
            #     email_id,
            #     {"name": company_name, "login_id": login_id, "password": password}
            # )

            return JSONResponse(
                status_code=201,
                content={'message': 'User registration successful, please login to continue!'}
            )

    except Exception as e:
        print("Error while creating user 5pointcreditsupport:", str(e))
        raise HTTPException(status_code=500, detail="Error while creating user contact 5pointcreditsupport")


async def user_login(mongodb_connection, input_data: dict):
    try:
        email_id = input_data.get("email_id")
        password = input_data.get("password")
        

        if not email_id or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="login_id and password required"
            )

        users_collection = mongodb_connection["users"]
        auth_collection = mongodb_connection["auth"]

        user = await users_collection.find_one({"email_id":email_id})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found please register"
            )
        company_name = user.get("company_name") 
        auth = await auth_collection.find_one({"user_id":ObjectId(user['_id'])})
        print(auth['password_hash'])

        if not verify_password(password, auth["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        token = create_access_token({
            "user_id": str(user["_id"]),
            "role": user.get("role", "user")
        })

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": True,
                "message": "Login successful",
                "data": {
                    "user_id": str(user["_id"]),
                    "company_name": company_name,
                    "email_id": email_id,
                    "token": token
                }
            }
        )

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="None",)

        return response

    except HTTPException:
        raise  # re-raise known errors

    except Exception as e:
        print("Error raised in login part:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error contact admin for support"
        )


async def user_logout():
    response = JSONResponse(status_code=status.HTTP_200_OK, content={"message":"Logout successful"})
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=True,  # only if using HTTPS
        samesite="none"  # or "lax" depending on your setup
    )
    return response



async def user_reset_password(current_user, mongodb_connection, input_data: dict):
    try:
        new_password = input_data.get("new_password")
        if not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password required"
            )

        auth_collection = mongodb_connection["auth"]
        print("current_user:",current_user)

        # fetch auth record
        auth = await auth_collection.find_one({"user_id":ObjectId(current_user)})

        if not auth:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auth record not found"
            )

        # hash new password
        hashed_password = hash_password(new_password)

        # update password
        await auth_collection.update_one(
            {"user_id":ObjectId(current_user)},
            {
                "$set": {
                    "password_hash": hashed_password,
                    "password_changed_at": datetime.now(timezone.utc)
                }
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Password updated successfully"}
        )
    except HTTPException as e:
        raise e  #capture and raise the HTTP exceptions
    except Exception as e:
        print("Error in reset_password:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="please contact admin for support"
        )


async def forget_password(email_id, mongodb_connection,background_task):
        #step 1:check if user exist in our system  if doesn't exist send response user not found create a new user or if you forget your username pls contact admin for support

        #step 2 : if user exist send a temp 4 digit system gen code and send and store that code timestamp and mail_address

        try:
            if not email_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Email id required"}
                )
            users_collection = mongodb_connection["users"]
            reset_collection = mongodb_connection["password_resets"]

            # Step 1: Check if user exists
            user = await users_collection.find_one({"email_id": email_id})

            # IMPORTANT: Do NOT reveal if user exists (security best practice)
            if not user:
                return {
                    "status": "success",
                    "message": "If this email is registered, a reset code has been sent."
                }

            # Step 2: Generate 4-digit OTP
            otp = str(random.randint(1000, 9999))

            # Expiry time (e.g., 10 minutes)
            expiry_time = datetime.now(timezone.utc) + timedelta(minutes=5)

            # Store OTP in DB (upsert to overwrite old ones)
            await reset_collection.update_one(
                {"email": email_id},
                {
                    "$set": {
                        "otp": otp,
                        "expires_at": expiry_time,
                        "created_at": datetime.now(timezone.utc),
                        "is_verified": False,  #initailly the flag will be
                        "reset_token": None,
                        "verified_at": None
                    }
                },
                upsert=True
            )

            # Step 3: Send email in background
            background_task.add_task(send_reset_email_to_user, email_id, otp)

            return {
                "status": "success",
                "message": "If this email is registered, a reset code has been sent."
            }

        except HTTPException as e:
            raise e

async def validate_forgot_password_otp(email_id:str, otp:str, mongodb_connection):
    try:
        reset_collection = mongodb_connection["password_resets"]

        # Step 1: Fetch record
        record = await reset_collection.find_one({"email": email_id})

        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message":"Invalid or expired OTP"}
            )

        # Step 2: Check OTP match
        if record.get("otp") != otp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message":"Invalid OTP"}
            )

        # Step 3: Check expiry
        expires_at = record.get("expires_at")

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={"message": "OTP has expired"}
            )

        # Step 4: Generate reset token for security reasons
        reset_token = str(uuid.uuid4())

        await reset_collection.update_one(
            {"email": email_id},
            {
                "$set": {
                    "is_verified": True,
                    "reset_token": reset_token,
                    "verified_at": datetime.now(timezone.utc)
                }
            }
        )

        # Step 5: Success response
        return JSONResponse(status_code=status.HTTP_200_OK,content={
            "message": "OTP verified successfully",
            "reset_token": reset_token
        })

    except HTTPException as e:
        # Re-raise FastAPI exceptions directly
        print(str(e))
        raise e

    except Exception as e:
        # Internal server error
        print(str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message":"Internal server error please contact admin"}
        )

async def reset_password_(reset_token: str, new_password: str, mongodb_connection):
    try:
        reset_collection = mongodb_connection["password_resets"]

        doc = await reset_collection.find_one({"reset_token": reset_token})

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "UnAuthorized"}
            )

        if not doc.get("is_verified"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "otp verification failed"}
            )

        # Hash password
        hashed_password = hash_password(new_password)

        auth_collection = mongodb_connection["auth"]
        print(doc.get("email"))
        # Update password
        await auth_collection.update_one(
            {"email_id": doc.get("email")},
            {
                "$set": {
                    "password_hash": hashed_password,
                    "password_changed_at": datetime.now(timezone.utc)
                }
            }
        )

        # Invalidate reset token
        await reset_collection.update_one(
            {"email_id": doc["email"]},
            {
                "$set": {
                    "reset_token": None,
                    "is_verified": False
                }
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Password updated successfully"}
        )

    except HTTPException as e:
        print(e)
        raise e

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Internal server error please contact admin"}
        )


async def check_r1xchange_account_controller(acc_id:str,request):
    
    mongodb_connection = request.app.state.mongo_db
    
    try:
        user_collection = mongodb_connection["users"]
        user = await user_collection.find_one(
            {"account_id": acc_id},
            {
                "_id": 0,
                "login_id": 1,
                "email": 1,
                "customer_name": 1,
                "phone": 1,
                "company_name": 1,
                "gst_number": 1,
                "status": 1
            })

        if not user:
           raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Requested User Not Found please contact admin for support")

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "success","user_exist":True, "data": user})
    except HTTPException:
        raise
    except Exception as e:
        print("Error in get_current_user:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error please contact admin for support"
        )