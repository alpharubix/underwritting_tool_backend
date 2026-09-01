from fastapi import APIRouter,Request
from controller.rectify_money_controller.rectify_money import get_rectify_money

rectify_money_router = APIRouter(
    prefix="/v1/rectify"
)

@rectify_money_router.get("/{cust_id}")
async def rectify_money(cust_id: str, request: Request, reference_id: str):
    return await get_rectify_money(cust_id, request, reference_id)

from pydantic import BaseModel
from typing import List

class SelectedAccount(BaseModel):
    account_number: str
    lender_name: str

class SubmitRectifySelectionsRequest(BaseModel):
    reference_id: str
    selected_accounts: List[SelectedAccount]

from controller.rectify_money_controller.rectify_money import submit_rectify_money_selections

@rectify_money_router.post("/{cust_id}/submit-selections")
async def submit_rectify_selections(cust_id: str, request: Request, data: SubmitRectifySelectionsRequest):
    selected_accounts_dict = [{"account_number": acc.account_number, "lender_name": acc.lender_name} for acc in data.selected_accounts]
    return await submit_rectify_money_selections(cust_id, request, data.reference_id, selected_accounts_dict)