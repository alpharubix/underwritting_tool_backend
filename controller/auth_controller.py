import json
import random
from datetime import timedelta
import asyncpg
from bson import ObjectId
from fastapi import HTTPException, BackgroundTasks, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from config.config import SiteCode, AnchorRole
from utils.auth_utility import hash_password, get_auth_dict, verify_password, create_access_token, generate_unique_id, \
    get_decoded_jwt_token
from utils.user_utility import get_user_dict
from controller.backgroud_task_controller import send_reset_email_to_user
import dotenv
dotenv.load_dotenv()
import os
from datetime import datetime, timezone
import uuid
from pymongo.errors import DuplicateKeyError
from config.config import AdminStatus,AdminRole,AnchorRole
from utils.auth_utility import is_password_valid
import secrets 
import string



async def register_user(
    input_data: dict,
    postgres_conn: asyncpg.Connection,
    mongodb_database: AsyncIOMotorDatabase,
    background_tasks: BackgroundTasks,
    jwt_token = None
) -> JSONResponse:


    company_name = input_data.get('company_name')
    gst_number = input_data.get('gst_number',None)
    email_id = input_data.get('email_id')
    account_owner_id = os.getenv("ACCOUNT_OWNER_ID")
    created_by_id = os.getenv("CREATED_BY_ID")
    phone_no = input_data.get("phone_no")
    customer_name = input_data.get('customer_name')
    password = input_data.get('password')
    site_code = input_data.get('site_code')
    anchor_id = input_data.get('anchor_id')

    try:
        user_collection = mongodb_database['users']
        auth_collection = mongodb_database['auth']
        user = await user_collection.find_one({'phone': phone_no})

        if user:
            return JSONResponse(status_code=409, content={'message': 'User already exists!'})

        else:
            #check if the site_code is matching the system sitecode
           if site_code not in (SiteCode.R1X01.value,SiteCode.PCX01.value,SiteCode.ACX01.value):
                return JSONResponse(status_code=400, content={'message': 'Invalid site code!'})

            # check if the user registration request is coming from the anchor
           if site_code == SiteCode.ACX01.value:
                #check if the request is from anchor or super anchor
                if not jwt_token:
                    return JSONResponse(status_code=401,content={"messgae":"Forbidden access"})
                decoded_jwt_token = get_decoded_jwt_token(jwt_token)
                user_id = decoded_jwt_token['user_id']
                role = decoded_jwt_token['role']
                if role == AnchorRole.ANCHOR.value:
                    anchor_id = user_id
                elif role == AnchorRole.SUPER_ANCHOR.value and anchor_id is None:
                    return JSONResponse(status_code=400,content={"message":"anchor_id is required"})

           existing_account = await postgres_conn.fetchrow(
                f"""
                SELECT id FROM {os.getenv("ACCOUNTS_TABLE_NAME")}
                WHERE RIGHT(phone, 10) = RIGHT($1, 10)
                """,
                phone_no
            )
           print("Existing_accounts", existing_account)

        if existing_account:
            account_id = existing_account['id']
        else:
            account_id = await postgres_conn.fetchval(
                f"""
                INSERT INTO {os.getenv("ACCOUNTS_TABLE_NAME")}(
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

        user = get_user_dict(account_id,email_id, phone_no, company_name, gst_number, customer_name,site_code=site_code,anchor_id=anchor_id)
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
                "message": "Login successful"}
        )

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",)

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
        samesite="lax"  # or "lax" depending on your setup
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
    except HTTPException as e:
        raise e
    except Exception as e:
        print("Error in get_current_user:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error please contact admin for support"
        )


"""--------PRATHAMESH-----admin portfolio codes"""
async def create_admin(request: Request):

    try:
        db = request.app.state.mongo_db
        mongo_client = db.client
        body = await request.json()
        password = body.get("password")

        requester_role = request.state.role
        print("Requester role : ",requester_role)
        # print(role)
        if requester_role!= AdminRole.SUPER_ADMIN.value:
            return JSONResponse(
                content={"message":"Only super admins can create the admins"},
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        if not password:
            return JSONResponse(
                content={"message": "Password is required"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Generate 6-digit login ID
        # login_id = secrets.randbelow(900000) + 100000
        # login_id = db.admin.find_one({"login_id":login_id})

        # Password hashing does not need a DB transaction
        password_hash = hash_password(password)
        now = datetime.now(timezone.utc)
        letters = ''.join(
            secrets.choice(string.ascii_uppercase)
            for _ in range(4)
        )
        digits = ''.join(
            secrets.choice(string.digits)
            for _ in range(2)
        )
        
        login_id=letters+digits
        role = AdminRole.ADMIN.value
        admin_doc = {
            "login_id": login_id,
            "admin_status": AdminStatus.ACTIVE.value,
            "role": (
                AdminRole.SUPER_ADMIN.value
                if role == AdminRole.SUPER_ADMIN.value
                else AdminRole.ADMIN.value
            ),
            "created_at": now,
            "updated_at": now
        }

        auth_doc = {
            "user_id": login_id,
            "password_hash": password_hash,
            "password_changed_at": now
        }

        async with await mongo_client.start_session() as session:
            async with session.start_transaction():
                # Create admin
                admin_result = await db.admins.insert_one(
                    admin_doc,
                    session=session
                )
                auth_doc = {
                            "user_id": str(admin_result.inserted_id),
                            "password_hash": password_hash,
                            "password_changed_at": now
                        }
                # Create authentication record
                auth_result = await db.auth.insert_one(
                    auth_doc,
                    session=session
                )
        return JSONResponse(
            content={
                "message": f"{admin_doc.get("role")} created successfully",
                "data": {
                    "login_id": login_id,
                    "admin_id": str(admin_result.inserted_id),
                    "auth_id": str(auth_result.inserted_id)
                }
            },
            status_code=status.HTTP_201_CREATED
        )

    except DuplicateKeyError as e:

        print("Duplicate key while creating admin:", e)

        return JSONResponse(
            content={
                "message": "Admin creation failed because the generated login ID already exists"
            },
            status_code=status.HTTP_409_CONFLICT
        )

    except Exception as e:

        print("Error while creating admin:", e)

        return JSONResponse(
            content={
                "message": "Failed to create admin"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def login_admin(request:Request):

    try:
        db = request.app.state.mongo_db 
        body = await request.json()
        login_id = body.get("login_id")
        incoming_password = body.get("password")

        admin = await db.admins.find_one(
            {"login_id":login_id}
        )

        if admin is None:
            return JSONResponse(
                content={"message":"User doesnt exist"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        else:
            user_id = str(admin["_id"])
            print(admin)
            print(user_id)
            admin_role = admin.get("role")

            auth_doc= await db.auth.find_one({
                "user_id":user_id
            })
            print(type(user_id))
            
            stored_password = auth_doc.get("password_hash")
            if not verify_password(incoming_password,stored_password):
                return JSONResponse(
                    content={"message":"Password is incorrect"},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            token = create_access_token({
                        "user_id": str(admin["_id"]),
                        "role": admin_role
                    })
            

            response = JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "status": True,
                            "message": f"Login successful "}
                    )
    
            response.set_cookie(
                        key="access_token",
                        value=token,
                        httponly=True,
                        secure=False,
                        samesite="lax")
            return response

    except HTTPException:
        raise
    except Exception as e:
            print("Error raised in login part:", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error contact admin for support"
            )


async def create_anchor(request: Request):
    try:
        user_role = request.state.role
        user_id = request.state.user_id
        # Only ADMIN and SUPER_ADMIN can create an anchor
        if user_role not in (
            AdminRole.SUPER_ADMIN.value,
            AdminRole.ADMIN.value,
            AnchorRole.SUPER_ANCHOR.value
        ):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"message": "Forbidden access"}
            )

        database = request.app.state.mongo_db

        body = await request.json()

        anchor_name = body.get("anchor_name")
        anchor_code = body.get("anchor_code")
        password = body.get("password")

        if anchor_name is None:
            return JSONResponse(
                content={"message": "Anchor Name is required"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if anchor_code is None and user_role in (AdminRole.SUPER_ADMIN.value, AdminRole.ADMIN.value):
            return JSONResponse(
                content={"message": "Anchor code is required"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if user_role == AnchorRole.SUPER_ANCHOR.value:
            anchor = await database["anchors"].find_one({"_id":ObjectId(user_id)},{"anchor_code":1})

            anchor_code = anchor.get("anchor_code")


        if password is None:
            return JSONResponse(
                content={"message": "Password is required"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate password
        is_password_validation, message = is_password_valid(password)

        if not is_password_validation:
            return JSONResponse(
                content={"message": message},
                status_code=status.HTTP_400_BAD_REQUEST
            )


        # Generate unique login ID
        login_id = generate_unique_id()[:5]

        # Hash password
        hashed_password = hash_password(password)

        current_time = datetime.now(timezone.utc)

        anchor_doc = {
            "anchor_name": anchor_name,
            "anchor_code": anchor_code,
            "login_id": login_id,
            "is_active": True,

             #meta fields for auditing
            "created_at": current_time,
            "modified_at": current_time,

            # User who created the anchor
            "created_by": ObjectId(request.state.user_id),
            "modified_by": ObjectId(request.state.user_id),

            #additional - prathamesh modified
            "role":AnchorRole.ANCHOR.value,
        }

        result = await database["anchors"].insert_one(anchor_doc)

        if result:
            anchor_id = result.inserted_id
            auth_doc = {
                "user_id": str(anchor_id),
                "password_hash": hashed_password,
                "password_changed_at":None
            }
            result = await database["auth"].insert_one(auth_doc)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Anchor created successfully",
                "data":{"login_id":login_id}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to create anchor",
                "error": str(e)
            }
        )

async def anchor_login(request: Request):
    try:
        body = await request.json()

        login_id = body.get("login_id")
        password = body.get("password")

        if login_id is None or login_id == '':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,content={"message": "login id is required"}
            )

        if password is None or password == '' :
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"message": "password is required"})

        database = request.app.state.mongo_db

        user = await database["anchors"].find_one({"login_id": login_id})

        if not user:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message":"User not found please register"}
            )
        auth_doc = await database["auth"].find_one({"user_id": str(user["_id"])})

        hashed_password = auth_doc["password_hash"]

        if not verify_password(password,hashed_password):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message":"Invalid credentials"}
            )

        token = create_access_token({
            "user_id": str(user["_id"]),
            "role": user.get("role", "ANCHOR")
        })

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": True,
                "message": "Login successful"}
        )

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax", )

        return response

    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error contact admin for support"},
        )



async def dashboard_admins(request:Request):
    db = request.app.state.mongo_db
    requester_role = request.state.role
    # if super-admin - admins and super-anchors and anchors
    # if admin - super-anchors , anchors and users
    # if super-anchors - anchors , users
    # if anchors - users
    print("Requester Role : ",requester_role)

    ALLOWED_ROLES = {"SUPER_ADMIN","ADMIN","SUPER_ANCHOR","ANCHOR"}

    if requester_role not in ALLOWED_ROLES:
        return JSONResponse(
            content={"message":"Forbidden access !"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    user_id = request.state.user_id
    users =  await db.users.find({"anchor_id":user_id},{"_id":0}).to_list(length=None)

    if requester_role == "SUPER_ADMIN":
        # admins, super_anchors, anchors,users
        admins = await db.admins.find({"role":"ADMIN"},{"_id":0}).to_list(length=None)
        super_anchors = await db.anchors.find({"role":"SUPER_ANCHOR"},{"_id":0}).to_list(length=None)
        anchors = await db.anchors.find({"role":"ANCHOR"},{"_id":0}).to_list(length=None)
        data = {"role":requester_role,"super_anchors":super_anchors,"admins":admins,"anchors":anchors,"users":users}
        return data

    elif requester_role == "ADMIN":
        #super_anchors, anchors,users
        super_anchors = await db.anchors.find({"role":"SUPER_ANCHOR"},{"_id":0}).to_list(length=None)
        anchors = await db.anchors.find({"role":"ANCHOR"},{"_id":0}).to_list(length=None)
        data = {"role":requester_role,"super_anchors":super_anchors,"anchors":anchors,"users":users}
        return data

    elif requester_role == "SUPER_ANCHOR":
        # anchors, users
        anchors = await db.anchors.find({"role":"ANCHOR"},{"_id":0}).to_list(length=None)
        data = {"role":requester_role,"anchors":anchors,"users":users}
        return data

    else:
        #anchor
        #view USERS info, he is admin
        data={"role":requester_role,"users":users}
        return data


async def update_admin(request:Request,incoming_login_id:str):
    #ONLY SUPER ADMIN PREVILEGE
    requested_role = request.state.role

    body = await request.json()
    keys = body.keys() #ATTRIBUTE checking

    if not incoming_login_id:
        return JSONResponse(
            content={"message": "Please provide the login ID"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if requested_role!="SUPER_ADMIN":
        return JSONResponse(
            content={"message":"Forbidden access !"},
            status_code=status.HTTP_403_FORBIDDEN
        )

    ALLOWED_ATTR = {"admin_status","role","login_id"}
    CLOSEST_ATTR = {}

    db = request.app.state.mongo_db

    invalid_keys = set(keys) - ALLOWED_ATTR

    if invalid_keys:
        CLOSEST_ATTR = {
            key: actual
            for key in invalid_keys
            for actual in ALLOWED_ATTR
            if actual in key or key in actual
        }
        return JSONResponse(
            content={"message":f"Invalid keys found : {list(invalid_keys)}","Closest keys":CLOSEST_ATTR},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    now = datetime.now(timezone.utc)

    target_admin = await db.admins.find_one({
        "login_id":incoming_login_id

    })

    if not target_admin :
        return JSONResponse(
            content={"message":"Admin not found | Please recheck the login-id"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    old_data = {
        key:target_admin.get(key)
        for key in keys
    }
    redundant_data = {
        key:value
        for key,value in body.items()
        if old_data.get(key) == value
    }

    update_data = {
        key: value
        for key, value in body.items()
        if key not in redundant_data
    }
    update_data["updated_at"]=now.isoformat()
    print("Redundant data : ",redundant_data)
    print("Update data : ",update_data)
    admin_result = await db.admins.update_one(
        {"_id": target_admin["_id"]},
        {"$set":update_data}
    )

    if admin_result.matched_count==0:
        return JSONResponse(
            content={"message":"Failed to update - "},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    final_updated_data = {
        "login_id":incoming_login_id,
        f"old data":old_data,
        f"updated data":update_data
    }
    print(admin_result)

    return JSONResponse(
        content={"message":f"Admin with the login-id : {incoming_login_id} has been updated successfully",**final_updated_data},
        status_code=status.HTTP_200_OK
    )

async def create_super_admin(request:Request,incoming_super_key:str):
    super_admin_key = os.getenv("SUPER_ADMIN_KEY")

    if incoming_super_key!=super_admin_key:
        return JSONResponse(
            content={"message":"Please provide the valid super admin key"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    #create
    db = request.app.state.mongo_db
    body = await request.json()

    letters = ''.join(
                secrets.choice(string.ascii_uppercase)
                for _ in range(4)
            )
    digits = ''.join(
        secrets.choice(string.digits)
        for _ in range(2)
    )

    login_id = letters+digits
    password = body.get("password")
    hashed_password = hash_password(password)
    admin_result = await db.admins.insert_one({
        "login_id":login_id,
        "password":hashed_password,
        "role":AdminRole.SUPER_ADMIN.value
    })
    if admin_result.inserted_id is None:
        return JSONResponse(
            content={"message":"Error while creating the super-admin"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return JSONResponse(
        content={"message":"Super admin credentials created | Please remember the password given","login_id":login_id,"password":hashed_password},
        status_code=status.HTTP_201_CREATED
    )

async def create_super_anchor(request: Request):
    requester_role = request.state.role

    ROLES = {
        AdminRole.SUPER_ADMIN.value,
        AdminRole.ADMIN.value
    }

    if requester_role not in ROLES:
        return JSONResponse(
            content={"message": "Forbidden access !"},
            status_code=status.HTTP_403_FORBIDDEN
        )

    db = request.app.state.mongo_db
    body = await request.json()

    password = body.get("password")

    result, message = is_password_valid(password)

    if not result:
        return JSONResponse(
            content=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    letters = ''.join(
        secrets.choice(string.ascii_uppercase)
        for _ in range(4)
    )

    digits = ''.join(
        secrets.choice(string.digits)
        for _ in range(2)
    )

    login_id = letters + digits

    hashed_password = hash_password(password)
    now = datetime.now(timezone.utc)

    client = request.app.state.mongo_client

    try:
        async with await client.start_session() as session:

            async with session.start_transaction():

                # 1. Create anchor
                anchor_result = await db.anchors.insert_one(
                    {
                        "login_id": login_id,
                        "password": hashed_password,
                        "role": "SUPER_ANCHOR"
                    },
                    session=session
                )

                # Make sure anchor was actually created
                if not anchor_result.inserted_id:
                    raise Exception("Failed to create anchor")

                # 2. Create auth record
                auth_result = await db.auth.insert_one(
                    {
                        "user_id": anchor_result.inserted_id,
                        "password_hash": hashed_password,
                        "password_changed_at": now
                    },
                    session=session
                )

                # Make sure auth was actually created
                if not auth_result.inserted_id:
                    raise Exception("Failed to create auth record")

                # Transaction automatically commits here

        return JSONResponse(
            content={
                "message": "Super anchor credentials created | Please remember the password given",
                "login_id": login_id,
                "password": password
            },
            status_code=status.HTTP_201_CREATED
        )

    except Exception as e:
        return JSONResponse(
            content={
                "message": "Error while creating the super-anchor"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def anchor_create_user(request:Request,_id:str=None):
    #admin creates the user
    requester_role=request.state.role
    
    ALLOWED_ROLES = {"SUPER_ANCHOR","ANCHOR"}

    user_id = request.state.user_id
    role = request.state.role
    
    if role not in ALLOWED_ROLES:
        return JSONResponse(
            content={"message":f"Forbidden access ! Your role is {role} "},
            status_code=status.HTTP_403_FORBIDDEN
        )
    else:
        db = request.app.state.mongo_db
        user_data = await request.json()
        

        email_id = user_data["email_id"].strip().lower()
        phone = user_data["phone_no"]
        password = user_data["password"]
        result,message = is_password_valid(password)
        existing_user = await db.users.find_one({"email_id":email_id})

        if not result:
            return JSONResponse(
                content={"message":message},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if existing_user:
            return JSONResponse(
                content={"message":"User by the email-id already exists"},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        existing_phone = await db.users.find_one({"phone":phone})
        if existing_phone:
            return JSONResponse(
                            content={"message":"User by the phone already exists"},
                            status_code=status.HTTP_400_BAD_REQUEST
                        )

        user_doc = get_user_dict(
            account_id=user_data["account_id"],
            email_id=email_id,
            phone_no=user_data["phone_no"],
            company_name=user_data["company_name"],
            gst_number=user_data["gst_number"],
            customer_name=user_data["customer_name"],
            site_code=None
        )
        user_doc["role"]="user"
        hashed_password=hash_password(password)
        now = datetime.now(timezone.utc)

        if role!="ANCHOR":
            anchor = await db.anchors.find_one({"_id":ObjectId(_id)}) #assigning the anchor

        if not anchor:
            return JSONResponse(
                content={"message":"Assignable anchor not found !"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        user_doc["anchor_id"]=ObjectId(_id) if requester_role == "SUPER_ANCHOR" else ObjectId(user_id)
        user_result = await db.users.insert_one(user_doc)

        auth_doc = {
            "user_id":user_result.inserted_id,
            "password_hash":hashed_password,
            "password_changed_at":now
        }
        
        auth_result = await db.auth.insert_one(auth_doc)

        if not auth_result.inserted_id or not user_result.inserted_id :
            return JSONResponse(
                content={"message":"User couldnt be created !"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return JSONResponse(
            content={
                "message":"User created succesfully",
                "data":{
                    "auth-user_id":str(user_result.inserted_id),
                    "user_id":str(user_result.inserted_id),
                    "password":password
                }

                },
            status_code=status.HTTP_201_CREATED,
            
        )
        
