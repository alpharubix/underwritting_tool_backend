from fastapi import APIRouter, Request
from controller.save_money_controller.save_money import get_save_money,submit_save_money_selections


save_money_router = APIRouter(prefix="/v1/save-money", tags=["Save Money"])

@save_money_router.get("/{cust_id}")
async def save_money(cust_id: str, reference_id: str, request: Request):
    return await get_save_money(cust_id, request, reference_id)


@save_money_router.post("/{cust_id}/submit-selections")
async def submit_selections(cust_id: str, request: Request):
    data = await request.json()
    reference_id = data.get("reference_id")
    selected_accounts = data.get("selected_accounts", [])
    return await submit_save_money_selections(cust_id, request, reference_id, selected_accounts)