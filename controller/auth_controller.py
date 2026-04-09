import json
from datetime import datetime, timezone
import asyncpg
from bson import ObjectId
from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from utils.auth_utility import generate_login_id, generate_secure_password, hash_password, get_auth_dict, \
    verify_password, create_access_token
from utils.user_utility import get_user_dict
from controller.backgroud_task_controller import send_registration_mail_to_user
import dotenv
dotenv.load_dotenv()
import os

async def register_user(input_data:dict,postgres_conn:asyncpg.Connection,mongodb_database:AsyncIOMotorDatabase,background_tasks:BackgroundTasks)->dict:


    if input_data.get('phone_no'):#check if the user is already registered or not using phone number
        company_name = input_data.get('company_name')
        gst_number = input_data.get('gst_number')
        email_id = input_data.get('email_id')
        account_owner_id = os.getenv("ACCOUNT_OWNER_ID")#initailly for all user account owner will be the manager
        created_by_id = os.getenv("CREATED_BY_ID")
        phone_no = input_data.get("phone_no")
        customer_name = input_data.get('customer_name')

        #query the users db for this phone_no
        try:
             user_collection = mongodb_database['users']
             auth_collection = mongodb_database['auth']
             user = await user_collection.find_one({'phone':phone_no})
             print("This is user",user)

             if user: # if user exist redirect the customer to login page
                 return JSONResponse(status_code=409, content={'message':'User already exists!'})
             else:
                 #if user doesnt exist check if the user has a account in crm or not
                    existing_account = await postgres_conn.fetchrow(
                        """
                        SELECT id FROM accounts
                        WHERE RIGHT(phone, 10) = RIGHT($1, 10)
                        """,
                        phone_no
                    )
                    print("Existing_accounts",existing_account)
                    if existing_account:
                        account_id = existing_account['id']

                        login_id = generate_login_id(company_name=company_name,phone=phone_no)
                        password = generate_secure_password(length=8)
                        hashed_password = hash_password(password)

                        user = get_user_dict(account_id,login_id,email_id,phone_no,company_name,gst_number,customer_name)
                        auth = get_auth_dict(user.get("_id"),hashed_password)

                        await user_collection.insert_one(user)
                        await auth_collection.insert_one(auth)

                    else: #account does'nt exists create account then create user and auth

                        account_id=await postgres_conn.fetchval(
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
                                VALUES ($1, $2, $3, $4, $5, $6::jsonb,$7)
                                RETURNING id
                                """,
                                company_name,
                                email_id,
                                phone_no,
                                int(account_owner_id),
                                datetime.now(timezone.utc),
                                json.dumps({"gst_number":gst_number,"customer_name":customer_name}),
                                int(created_by_id)

                            )
                        login_id = generate_login_id(company_name=company_name, phone=phone_no)
                        password = generate_secure_password(length=8)
                        hashed_password = hash_password(password)

                        user = get_user_dict(account_id, login_id, email_id, phone_no, company_name, gst_number,customer_name)
                        auth = get_auth_dict(user.get("_id"), hashed_password)

                        await user_collection.insert_one(user)
                        await auth_collection.insert_one(auth)

                    #send mail once after the response is sent to the user so the latency will became less
                    background_tasks.add_task(send_registration_mail_to_user,email_id,{"name":company_name,"login_id":login_id,"password":password})

                    return JSONResponse(status_code=201, content={'message':'User registeration successful please check your mail for login credentails!'})
        except Exception as e:
         print("Error while creating user 5pointcreditsupport:", str(e))
         raise HTTPException(status_code=500, detail="Error while creating user contact 5pointcreditsupport")
    return None


async def user_login(mongodb_connection, input_data: dict):
    try:
        login_id = input_data.get("login_id")
        password = input_data.get("password")

        if not login_id or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="login_id and password required"
            )

        users_collection = mongodb_connection["users"]
        auth_collection = mongodb_connection["auth"]

        user = await users_collection.find_one({"login_id":login_id})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found please register"
            )

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
                "message": "Login successful"
            }
        )

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="None",
            max_age=3600
        )

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


