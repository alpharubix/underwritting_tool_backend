import os
import json
from datetime import datetime, timezone
import httpx
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.results import UpdateResult
from starlette.exceptions import HTTPException
from starlette import status

from config.config import SCOREME_UPLOAD_URL
from custom_exceptions.scoreme_exceptions import raise_bsa_exception

async def upload_to_scoreme(files, data_params):
    payload = {"data": json.dumps(data_params)}
    files_to_send = []
    for f in files:
        await f.seek(0)
        content = await f.read()
        files_to_send.append(("file", (f.filename, content, f.content_type)))

    async with httpx.AsyncClient() as client:
        try:
            request_initiated_time = datetime.now(timezone.utc)
            response = await client.post(
                SCOREME_UPLOAD_URL,
                headers={
                    "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                    "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                },
                data=payload,
                files=files_to_send,
                timeout=60.0
            )
            print("Response from ScoreMe API:",response.text)
            result = response.json() #this never breaks because of scoreme proper json formated response for all the errors

            print("scoreme result",result)

            raise_bsa_exception(result)  #Http exception will be raised here if any error code matches

            if response.status_code == 200:
                return result,request_initiated_time
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"message": "Unexpected response from ScoreMe."}
                )
            return result
        except HTTPException as e: #caught the http exception raised by the bsa_exception function and re raise the error
            raise e
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                                detail={"message": "ScoreMe request timed out."})
        except Exception as e: #caught the non http execption error and re-rasie it as httpexception
            print(f"ScoreMe API Exception raised at upload_to_scoreme function: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error please contact the admin for support."})


async def create_bsa_ref_document(user_id, reference_id, input_data, bsa_request_status,
                                    bsa_request_initiated_time,bsa_request_response_message,bsa_request_response_code,mongobd_connection: AsyncIOMotorClient,is_request_from_crm=False,crm_user_info=None,is_merge_request=False,merge_request_status=None):
    try:
        document = {
            "user_id": user_id,
            "reference_id": reference_id,
            "input_data": input_data,
            "bsa_request_status": bsa_request_status,
            "bsa_request_initiated_at": bsa_request_initiated_time,
            "bsa_request_response_message": bsa_request_response_message,
            "bsa_request_response_code":bsa_request_response_code,

            # Webhook fields — populated later
            "webhook_response_status": "pending",
            "webhook_response_code": None,
            "webhook_response_message": None,
            "webhook_received_at": None,

            # Report URLs — populated after webhook
            "report_urls": {
                "json": None,
                "excel": None
            },

            # Pipeline flag
            "is_consumed": False,
            "consumed_at": None,

            #crm_user_info
            "is_request_from_crm": is_request_from_crm,
            "crm_user_info": crm_user_info,

            # Timestamps
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),

            #request differentiator flags for webhook handler
            "is_merge_request": is_merge_request,
            "merge_request_status": merge_request_status,
        }

        result = await mongobd_connection['bsa_reference'].insert_one(document)
        return str(result.inserted_id)
    except Exception as e:
        print("Error occurred while creating a bsa reference document in create_bsa_ref_document.",e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal server error please contact the admin for support."})

async def update_document(
    collection: AsyncIOMotorCollection,
    filter: dict,
    fields: dict,
) -> UpdateResult:
    return await collection.update_one(filter, {"$set": fields})

