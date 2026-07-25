from fastapi import APIRouter,Request
from controller.lender_eligibility.lender_control import get_lender_eligibility

lending_router = APIRouter(prefix='/v1/lending')

@lending_router.get("/check-eligibility")
async def check_eligibility(request:Request):
    return await get_lender_eligibility(request)
