from fastapi.responses import JSONResponse
from fastapi.requests import Request
import starlette.status as status

async def get_available_banks(
	request:Request,
	#user_id:str|None=None,
	# validating access_token
):
	collection = request.app.state.mongo_db["banks"]
	print(collection)

	query={}
	banks = await collection.find(
		query,
		{
			"_id":0,
			"bank_name": 1,
			"bank_code": 1,
	
		}
	).to_list(length=None)

	return{
		"status":True,
		"message":"Banks fetched successfully",
		"data":banks
	}

async def get_bank_parameter_controller(
	request:Request,
	bank_code:str|None=None,
	bank_name:str|None=None
):
	collection = request.app.state.mongo_db["bank_parameters"]
	
	if not bank_code and not bank_name:
		return JSONResponse(content={"message":"Missing parameters | Please provide either Bank_code or Bank_name" },status_code=status.HTTP_400_BAD_REQUEST)
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

async def get_customer_profile_controller(request:Request):
	user_id = request.state.user_id
	db = request.app.state.mongo_db

	profile = db["users"]
	query = {}
	data = await profile.find(
		{"user_id":user_id},
		{
			"_id":0,
			"email_id":1,
			"customer_name":1,
			"company_name":1
		}
	)
	print(data)

	return {
		"status":"true",
		"message":"Customer profile fetched successfully",
		"data":data
	}