from fastapi import APIRouter, Request,Response
from fastapi.responses import JSONResponse
from controller.demographics_controller import get_total_super_anchors

demographics_router = APIRouter(prefix='/v1/demographics',tags='demographics')

@demographics_router.get('/total-anchors')
async def get_total_super_anchors_route(request:Request):
    return await get_total_super_anchors(request)
