from fastapi import APIRouter
from starlette.requests import Request
from controller.payments_controller.payments_controller import get_create_order, get_user_pending_payments,get_validate_payment

payments_router = APIRouter(prefix="/v1/payments", tags=["payments"])


@payments_router.post("/create-order")
async def create_order(request: Request):
    return await get_create_order(request)

@payments_router.post("/validate-payment")
async def validate_payment(request: Request):
    return await get_validate_payment(request)

@payments_router.get("/pending")
async def get_user_pending_payments_route(request:Request,service:str):
    return await get_user_pending_payments(request,service)