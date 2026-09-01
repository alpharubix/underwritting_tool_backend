from fastapi import APIRouter, Request
from controller.save_money_controller.save_money import get_save_money

save_money_router = APIRouter(prefix="/v1/save-money", tags=["Save Money"])

@save_money_router.get("/{cust_id}")
async def save_money(cust_id: str, reference_id: str, request: Request):
    return await get_save_money(cust_id, request, reference_id)

from pydantic import BaseModel
from typing import List

class SelectedAccount(BaseModel):
    account_number: str
    lender_name: str

class SubmitSelectionsRequest(BaseModel):
    reference_id: str
    selected_accounts: List[SelectedAccount]

from controller.save_money_controller.save_money import submit_save_money_selections

@save_money_router.post("/{cust_id}/submit-selections")
async def submit_selections(cust_id: str, request: Request, data: SubmitSelectionsRequest):
    selected_accounts_dict = [{"account_number": acc.account_number, "lender_name": acc.lender_name} for acc in data.selected_accounts]
    return await submit_save_money_selections(cust_id, request, data.reference_id, selected_accounts_dict)