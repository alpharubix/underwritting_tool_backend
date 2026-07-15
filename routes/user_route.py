from http.client import HTTPException

from fastapi import APIRouter
from starlette.requests import Request
from controller.user_controller import get_current_user
from controller.user_controller import update_current_user
from pydantic import BaseModel

class UpdateUserRequest(BaseModel):
    customer_name: str
    phone: str
    email_id: str
    company_name: str
    gst_number: str | None = None

user_router = APIRouter(prefix="/v1/user", tags=["user"])

@user_router.get("/me")
async def get_current_user_route(request: Request):
    try:
        current_user = await get_current_user(request.state.user_id, request.app.state.mongo_db)
        return current_user
    except HTTPException as e:
        raise e


@user_router.put("/me")
async def update_current_user_route(request:Request,body: UpdateUserRequest):
    try:
        current_user = await update_current_user(request.state.user_id, body ,request.app.state.mongo_db)
        return current_user

    except HTTPException as e:
        raise e