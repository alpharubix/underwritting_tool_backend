from fastapi import APIRouter,Request
from controller.rectify_money_controller.rectify_money import get_rectify_money,submit_rectify_money_selections

rectify_money_router = APIRouter(
    prefix="/v1/rectify"
)

@rectify_money_router.get("/{cust_id}")
async def rectify_money(cust_id: str, request: Request, reference_id: str):
    return await get_rectify_money(cust_id, request, reference_id)



@rectify_money_router.post("/{cust_id}/submit-selections")
async def submit_rectify_selections(cust_id: str, request: Request):
    data = await request.json()
    reference_id = data.get("reference_id")
    selected_accounts = data.get("selected_accounts", [])
    return await submit_rectify_money_selections(cust_id, request, reference_id, selected_accounts)