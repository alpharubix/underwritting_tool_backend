from fastapi.responses import JSONResponse
from fastapi.requests import Request
import starlette.status as status

async def get_available_banks(
	request:Request,
	#user_id:str|None=None,
	# validating access_token
):
	collection = request.app.state.mongo_db["bank_parameters"]
	print(collection)

	query={}
	banks = await collection.find(
		query,
		{
			"_id":0,
			"bank_name": 1,
			"bank_id": 1,
	
		}
	).to_list(length=None)

	return{
		"status":True,
		"message":"Banks fetched successfully",
		"data":banks
	}

async def get_bank_parameter_controller(
	request:Request,
	bank_id:str|None=None,
	bank_name:str|None=None
):
	collection = request.app.state.mongo_db["bank_parameters"]
	
	if not bank_id and not bank_name:
		return JSONResponse(content={"message":"Missing parameters | Please provide either Bank_id or Bank_name" },status_code=status.HTTP_400_BAD_REQUEST)
	query = {}

	if bank_id:
		query["bank_id"] = bank_id
	if bank_name:
		query["bank_name"] = bank_name

	bank_parameters = await collection.find_one(
		query,
		{
			"_id":0,
			"bank_name":1,
			"modules":1
		}

	)

	return {
		"status":"true",
		"message":"Bank parameters fetched successfully",
		"data":bank_parameters
	}


async def analyse_date_range_controller(
		request:Request
):
	user_id = request.state.user_id

	collections = request.app.state.mongo_db["bsa_merged_bankstatements"]

	query = {}
	data = await collections.find(
		{"user_id"==user_id},
		{
			"_id":0,
			"from_date":1,
			"to_date":1
		}
	)

	return {
		"status": "true", 
		"message": "Date range fetched successfully", 
		"data":data
	}
