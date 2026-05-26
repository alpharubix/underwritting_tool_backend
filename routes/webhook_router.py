from json import JSONDecodeError
from fastapi import HTTPException
from fastapi.routing import APIRouter
from fastapi.requests import Request
from starlette import status
from controller.webhook.scoreme_webhook_controller import gst_webhook_receiver,itr_webhook_receiver

webhook_router = APIRouter(prefix='/webhook',tags=['Webhook'])



@webhook_router.post('/gst-statements')
async def webhook_route(request: Request):
    try:
        request_body = await request.json()
        mongodb_database = request.app.state.mongo_db
        return await gst_webhook_receiver(input_data=request_body,database=mongodb_database)
    except JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid Json Body")


@webhook_router.post('/itr-service')
async def itr_route(request: Request):
    try:
        request_body = await request.json()
        mongodb_database = request.app.state.mongo_db
        return await itr_webhook_receiver(input_data=request_body,database=mongodb_database)
    except JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Json Body")
    except HTTPException as e:
        raise e