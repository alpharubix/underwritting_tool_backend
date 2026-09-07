from fastapi import Request,Response,APIRouter
from fastapi.responses import JSONResponse
from controller.log_controller.logs import view_logs

log_router = APIRouter(prefix="/v1/logs")


ALLOWED_ROLES = ('ADMIN')

view_log_projection = {
    "_id":0,
    "timestamp":1
}

@log_router.get("/view")
async def view_logs_route(request:Request,page:int=1):
    return await view_logs(request,page)