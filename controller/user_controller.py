from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.responses import JSONResponse
from starlette import status


async def get_current_user(user_id,role,mongodb_connection:AsyncIOMotorClient)->dict:
    try:
        user=None
        print(role)
        print(user_id)
        if role in ("SUPER_ADMIN","ADMIN"):
            user = await mongodb_connection.admins.find_one(
                {"_id":ObjectId(user_id)},
                {
                    "_id":0,
                    "login_id":1,
                    "admin_status":1,
                    "role":1
                }
                )

        elif role in ("SUPER_ANCHOR","ANCHOR"):
            user = await mongodb_connection.anchors.find_one(
                {"_id": ObjectId(user_id)},
                {
                    "_id": 1,
                    "anchor_name": 1,
                    "anchor_code": 1,
                    "login_id":1,
                    "is_active":1,
                    "role":1
                })
            if user and "_id" in user:
                user["user_id"] = str(user["_id"])
                del user["_id"]


        else:   
            user_collection = mongodb_connection["users"]
            user = await user_collection.find_one(
                {"_id": ObjectId(user_id)},
                {
                    "_id": 1,
                    "email_id": 1,
                    "login_id": 1,
                    "customer_name": 1,
                    "phone": 1,
                    "company_name": 1,
                    "gst_number": 1,
                    "status": 1
                })
            if user and "_id" in user:
                user["user_id"] = str(user["_id"])
                del user["_id"]

        if not user:
           raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Requested User Not Found please contact admin for support")

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "success", "data": user})
    except HTTPException:
        raise
    except Exception as e:
        print("Error in get_current_user:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error please contact admin for support")


async def update_current_user(user_id, body, mongodb_connection: AsyncIOMotorClient):
    data = body.model_dump()
    print(data)

    try:
        user_collection = mongodb_connection["users"]

        result = await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": data}
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        updated_user = await user_collection.find_one(
            {"_id": ObjectId(user_id)},
            {
                "_id": 0,
                "email_id": 1,
                "customer_name": 1,
                "phone": 1,
                "company_name": 1,
                "gst_number": 1,
                "status": 1
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "success",
                "data": updated_user
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        print("Error in update_current_user:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error please contact admin for support"
        )


async def give_service_consent(request:Request,service:str):
    try:
        db = request.app.state.mongo_db
        service = service.lower()
        # input_body = await request.json()
        # if service == "user_policy":
        #     if input_body.get("user_id"):
        #         user_id = input_body.get("user_id")
        #     else:
        #         return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"message":"user_id is required"})
        # else:
        #     user_id = request.state.user_id

        # user_id = request.state.user_id if service != "user_policy" else None


        # if user_id is None:
        #     user = await request.json()
        #     user_id = user.get("user_id")
        #     print("USer id ",user_id)


        ALLOWED_SERVICES={'gst','cibil'}
        user_id = request.state.user_id
        if service not in ALLOWED_SERVICES:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message":"Invalid service for the consent . Please give valid service"
                }
            )
        else:

            #check for already given consents :

            existing_consent = await db.user_policy_service_consents.find_one({
                "user_id":user_id,
                "service":service,
                "consent":True
            })

            if existing_consent:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "message":"Consent is already given by the user",
                        "data":{
                            "consent":True,
                            "service":service
                        }
                    }
                )

        
            consent_doc = {
                "user_id":user_id,
                "service":service,
                "created_at":datetime.now(timezone.utc),
                "consent":True
            }
            consent_result = await db.user_policy_service_consents.insert_one(consent_doc)

            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "message":"Consent given successfully",
                    "data":{
                        "user_id":user_id,
                        "service":service
                    }
                }
            )
    except Exception as e:
        raise e

async def check_service_consent(request:Request,service:str):
    try:
        db = request.app.state.mongo_db
        user_id = request.state.user_id if service != "user_policy" else None
        ALLOWED_SERVICES={'gst','cibil','user_policy'}

        if user_id is None:
            user = await request.json()
            user_id = user.get("user_id")
            print("User id ",user_id)

        if service not in ALLOWED_SERVICES:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message":"Invalid service for checking the consent"
                }
            )
        else:

            consent = await db.user_policy_service_consents.find_one({
                "user_id":user_id,
                "service":service
            })

            if not consent:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "message":"Consent is not given for the service",
                        "data":{
                            "service":service,
                            "consent":False
                        }
                    }
                )

            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message":"Consent is given for the service",
                    "data":{
                        "consent":True,
                        "service":service
                    }
                }
            )
    except Exception as e:
        raise e