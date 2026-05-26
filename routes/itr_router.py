from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from controller.itr_controller.itr_analyzer_controller import is_itr_report_already_there

itr_router = APIRouter(prefix="/v1/itr")


@itr_router.get('/data-precheck')
async def post_itr_route(request: Request):
    return await is_itr_report_already_there(request)

