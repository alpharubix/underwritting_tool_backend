from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from controller.itr_controller.itr_analyzer_controller import is_itr_report_already_there, \
    initiate_itr_process, get_link_status_based_on_ref_id, get_tax_calculation, get_balance_sheet, \
    get_profit_and_loss_statement, get_ratio_analysis

itr_router = APIRouter(prefix="/v1/itr")


@itr_router.get('/data-precheck')
async def itr_data_precheck(request: Request)->JSONResponse:
    return await is_itr_report_already_there(request)

@itr_router.post('/generate-link')
async def generate_itr_link(request: Request)->JSONResponse:
    return await initiate_itr_process(request)

@itr_router.post('/check-link-status')
async def check_ref_status(request: Request)->JSONResponse:
    return await get_link_status_based_on_ref_id(request)


@itr_router.get('/tax-calculation')
async def tax_calculation(request: Request)->JSONResponse:
    return await get_tax_calculation(request)

@itr_router.get('/balance_sheet')
async def balance_sheet(request: Request)->JSONResponse:
    return await get_balance_sheet(request)

@itr_router.get('/profit-and-loss-statement')
async def profit_and_loss_statement(request: Request)->JSONResponse:
    return await get_profit_and_loss_statement(request)

@itr_router.get('/ratio-analysis')
async def ratio_analysis(request: Request)->JSONResponse:
    return await get_ratio_analysis(request)