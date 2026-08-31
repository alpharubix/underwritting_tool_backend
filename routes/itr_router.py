from typing import Optional

from controller.itr_controller.itr_analyzer_controller import get_r1xcrm_tax_calculation,get_r1xcrm_balance_sheet,get_r1xcrm_profit_and_loss_statement,get_r1xcrm_ratio_analysis
from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from controller.itr_controller.itr_analyzer_controller import get_itr_link_status_based_on_user, \
    initiate_itr_process, get_link_status_based_on_ref_id, get_tax_calculation, get_balance_sheet, \
    get_profit_and_loss_statement, get_ratio_analysis

itr_router = APIRouter(prefix="/v1/itr")


@itr_router.get('/link-precheck')
async def itr_data_precheck(request: Request,cust_id:Optional[str]=None)->JSONResponse:
    return await get_itr_link_status_based_on_user(request,cust_id)

@itr_router.post('/generate-link')
async def generate_itr_link(request: Request,cust_id:Optional[str]=None)->JSONResponse:
    return await initiate_itr_process(request,cust_id)

@itr_router.post('/check-link-status')
async def check_ref_status(request: Request)->JSONResponse:
    return await get_link_status_based_on_ref_id(request)


@itr_router.get('/tax-calculation')
async def tax_calculation(request: Request,cust_id:Optional[str]=None)->JSONResponse:
    return await get_tax_calculation(request,cust_id)

@itr_router.get('/r1xcrm-tax-calculation/{acc_id}')
async def r1xcrm_tax_calculation(request: Request, acc_id:int)->JSONResponse:
    return await get_r1xcrm_tax_calculation(request,acc_id)

@itr_router.get('/balance_sheet')
async def balance_sheet(request: Request,cust_id:Optional[str]=None)->JSONResponse:
    
    return await get_balance_sheet(request,cust_id)

@itr_router.get('/r1xcrm-balance_sheet/{acc_id}')
async def r1xcrm_balance_sheet(request: Request, acc_id:int)->JSONResponse:
    return await get_r1xcrm_balance_sheet(request,acc_id)

@itr_router.get('/profit-and-loss-statement')
async def profit_and_loss_statement(request: Request,cust_id:Optional[str]=None)->JSONResponse:
    return await get_profit_and_loss_statement(request,cust_id)

@itr_router.get('/r1xcrm-profit-and-loss-statement/{acc_id}')
async def r1xcrm_profit_and_loss_statement(request: Request, acc_id:int)->JSONResponse:
    return await get_r1xcrm_profit_and_loss_statement(request,acc_id)

@itr_router.get('/ratio-analysis')
async def ratio_analysis(request: Request,cust_id:Optional[str]=None)->JSONResponse:
    return await get_ratio_analysis(request,cust_id)

@itr_router.get('/r1xcrm-ratio-analysis/{acc_id}')
async def r1xcrm_ratio_analysis(request: Request, acc_id:int)->JSONResponse:
    return await get_r1xcrm_ratio_analysis(request,acc_id)