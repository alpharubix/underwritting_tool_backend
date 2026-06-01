from fastapi import HTTPException,BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from controller.gst_contoller.gst_analyser_controller import gst_webhook_consumer
from controller.itr_controller.itr_analyzer_controller import itr_webhook_consumer


async def gst_webhook_receiver(input_data:dict,database:AsyncIOMotorDatabase,backgroud_task:BackgroundTasks)->JSONResponse:
    try:
        if not input_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Body should not be empty")

        gst_statements_coll= database["gststatements"]

        await gst_statements_coll.insert_one(input_data)

        return await gst_webhook_consumer(webhook_data=input_data,database=database,background_task=backgroud_task)

    except HTTPException as e:
        raise e

    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal Server Error"})




async def itr_webhook_receiver(input_data:dict,database:AsyncIOMotorDatabase,background_task:BackgroundTasks)->JSONResponse:
    try:
        if not input_data:
            HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Body should not be empty")

        itr_collection = database["itr_webhook_data"]

        await itr_collection.insert_one(input_data)

        return await itr_webhook_consumer(webhook_data=input_data,database=database,background_task=background_task)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal Server Error"})

