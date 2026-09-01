from fastapi import APIRouter
from controllers.rectify_money_controller import get_rectify_money

rectify_money_router = APIRouter(
    prefix="/rectify-money"
)


@rectify_money_router.get("/{reference_id}")
async def rectify_money(reference_id: str):
    return await get_rectify_money(reference_id)