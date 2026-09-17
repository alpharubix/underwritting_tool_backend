from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from controller.log_controller.logs import view_logs

log_router = APIRouter(prefix="/v1/logs")


ALLOWED_ROLES = ('ADMIN')

view_log_projection = {
    "_id":0,
    "timestamp":1
}

@log_router.get("/view")
async def view_logs_route(
    request: Request,
    page: int = Query(1, ge=1),
    path: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    service: str | None = None,
    method: str | None = None,
    user_id: str | None = None,
    role: str | None = None,
    status_code: int | None = None,
    ):
    return await view_logs(
        request=request,
        page=page,
        status_filter=status_filter,
        service=service,
        method=method,
        path=path,
        user_id=user_id,
        role=role,
        status_code=status_code,
    )
