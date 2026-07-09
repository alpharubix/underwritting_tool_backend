from asyncio.log import logger

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
		{"user_id": user_id},
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
		{"user_id": user_id},
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

from datetime import datetime
from pymongo import UpdateOne
#ADDING MIGRATION SCRIPT FOR PARSED MONTH DATE TO THE OVERVIEW OBJECT 
async def add_parsed_month_date(db):
    print("Starting migration for parsedMonthDate...")
    """
    One-time migration script.

    Adds `parsedMonthDate` to every object inside

    analysis_metadata.Data.OverView

    if it does not already exist.

    Safe to execute multiple times.
    """

    collection = db.bsa_merged_bankstatements

    cursor = collection.find(
        {
            "analysis_metadata.Data.Cash Flow": {
                "$exists": True
            }
        },
        {
            "_id": 1,
            "analysis_metadata.Data.Cash Flow": 1
        }
    )

    bulk_updates = []

    total_documents = 0
    updated_documents = 0
    skipped_documents = 0

    async for doc in cursor:

        total_documents += 1

        cashFlow = (
            doc.get("analysis_metadata", {})
               .get("Data", {})
               .get("Cash Flow", [])
        )

        modified = False

        for row in cashFlow:
            print("Processing row:", row)
            # Skip if already migrated
            if "parsedMonthDate" in row:
                continue

            month = row.get("MonthYear")

            if not month:
                continue

            try:

                row["parsedMonthDate"] = datetime.strptime(
                    month,
                    "%b %Y"
                ).replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                modified = True

            except Exception as e:

                logger.warning(
                    "Unable to parse month '%s' in document %s",
                    month,
                    doc["_id"]
                )

        if modified:

            updated_documents += 1

            bulk_updates.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "analysis_metadata.Data.Cash Flow": cashFlow
                        }
                    }
                )
            )

        else:
            skipped_documents += 1

        # Execute every 500 updates
        if len(bulk_updates) >= 500:

            await collection.bulk_write(bulk_updates)

            logger.info(
                "Updated %d documents...",
                updated_documents
            )

            bulk_updates = []

    if bulk_updates:

        await collection.bulk_write(bulk_updates)

    logger.info(
        """
Migration Completed

Total Documents   : %d
Updated Documents : %d
Skipped Documents : %d
""",
        total_documents,
        updated_documents,
        skipped_documents,
    )