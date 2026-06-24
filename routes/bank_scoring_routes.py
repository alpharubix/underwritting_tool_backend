from fastapi import FastAPI,APIRouter,Request
from controller.banking_score_controller import get_available_banks,get_bank_parameter_controller,analyse_date_range_controller
from controller.bank_statement_report import get_report_date_range
bank_scoring_router = APIRouter(prefix="/v1/bank-scoring",tags=["Bank scoring"])


#API 1 - TO RETURN ALL THE BANKS
@bank_scoring_router.get("/available-banks")
async def get_banks(
	request:Request
):
	return await get_available_banks(request)


#API 2 - TO  GET THE BANK PARAMETERS 
@bank_scoring_router.get("/bank-parameters")
async def get_bank_parameters(
	request:Request,
	bank_id:str | None=None,
	bank_name:str|None=None
):
	return await get_bank_parameter_controller(request,bank_id,bank_name)

#API 3 - TO GET THE DATE RANGE 
@bank_scoring_router.get("/analysis-date-range")
async def analyse_date_range(
		request:Request
):
	return await get_report_date_range(request.app.state.mongo_db,request.state.user_id)