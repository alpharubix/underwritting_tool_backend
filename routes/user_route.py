from http.client import HTTPException

from fastapi import APIRouter
from starlette.requests import Request
from controller.user_controller import get_current_user

user_router = APIRouter(prefix="/v1/user", tags=["user"])

@user_router.get("/me")
async def get_current_user_route(request: Request):
    try:
        current_user = await get_current_user(request.state.user_id, request.app.state.mongo_db)
        return current_user
    except HTTPException as e:
        raise e