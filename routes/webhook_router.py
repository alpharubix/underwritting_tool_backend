from json import JSONDecodeError
from fastapi import HTTPException, BackgroundTasks
from fastapi.routing import APIRouter
from fastapi.requests import Request
from starlette import status
from controller.webhook.scoreme_webhook_controller import gst_webhook_receiver,itr_webhook_receiver,credit_bureau_webhook_receiver

webhook_router = APIRouter(prefix='/webhook',tags=['Webhook'])



@webhook_router.post('/gst-statements')
async def webhook_route(request: Request,background_tasks:BackgroundTasks):
    try:
        request_body = await request.json()
        mongodb_database = request.app.state.mongo_db
        return await gst_webhook_receiver(input_data=request_body,database=mongodb_database,backgroud_task=background_tasks)
    except JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid Json Body")


@webhook_router.post('/itr-service')
async def itr_route(request: Request,background_tasks:BackgroundTasks):
    try:
        request_body = await request.json()
        mongodb_database = request.app.state.mongo_db
        return await itr_webhook_receiver(input_data=request_body,database=mongodb_database,background_task=background_tasks)
    except JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Json Body")
    except HTTPException as e:
        raise e

@webhook_router.post('/credit-bureau')
async def itr_route(request: Request,background_tasks:BackgroundTasks):
    try:
        request_body = await request.json()
        mongodb_database = request.app.state.mongo_db
        return await credit_bureau_webhook_receiver(input_data=request_body,database=mongodb_database,background_task=background_tasks)
    except JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Json Body")
    except HTTPException as e:
        raise e

