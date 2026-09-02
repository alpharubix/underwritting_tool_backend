from fastapi import APIRouter, Request
from controller.access_money_controller.access_money import request_loan

access_money_router = APIRouter(prefix="/v1/access-money")

@access_money_router.post("/loan-request")
async def request_loan_route(request: Request):
    return await request_loan(request=request)