from fastapi import APIRouter, BackgroundTasks
from starlette.requests import Request
from starlette.responses import JSONResponse
from controller.bank_credit_controller.bank_credit import create_credit_template
bank_credit_router = APIRouter(prefix="/v1/bank-credit")


@bank_credit_router.post("/create-credit-template")
async def create_credit_template(request:Request):
    return await create_credit_template(request)