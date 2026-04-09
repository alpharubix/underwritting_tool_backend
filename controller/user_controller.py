from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.responses import JSONResponse
from starlette import status


async def get_current_user(user_id, mongodb_connection:AsyncIOMotorClient)->dict:
    try:
        user_collection = mongodb_connection["users"]
        user = await user_collection.find_one(
            {"_id": ObjectId(user_id)},
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

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "success", "data": user})
    except HTTPException:
        raise
    except Exception as e:
        print("Error in get_current_user:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error please contact admin for support")




