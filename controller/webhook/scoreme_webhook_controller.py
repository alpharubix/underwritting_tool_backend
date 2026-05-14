from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse


async def gst_webhook_receiver(input_data:dict,database:AsyncIOMotorDatabase):
    try:
        if not input_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Body should not be empty")

        gst_statements_coll= database["gststatements"]

        await gst_statements_coll.insert_one(input_data)

        return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"webhook response received successfully"})

    except HTTPException as e:
        raise e

    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal Server Error"})
