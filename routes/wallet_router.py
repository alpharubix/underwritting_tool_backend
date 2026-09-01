from fastapi import APIRouter
from starlette.requests import Request
from controller.payments_controller.wallet_contoller import get_service_balance
wallet_router = APIRouter(prefix="/v1/wallet", tags=["wallet"])


@wallet_router.post("/balance/{service}")
async def wallet_balance(request: Request, service: str):
    return await get_service_balance(request,service)