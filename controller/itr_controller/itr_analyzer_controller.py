import json
import os
from datetime import datetime, timezone
from typing import Optional
from starlette import status
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.requests import Request
import logging
from starlette.responses import JSONResponse
import config.config as url
from custom_exceptions.scoreme_exceptions import raise_itr_post_link_exception
from utils.auth_utility import is_email_valid
import httpx
logging.basicConfig(level=logging.INFO)


async def send_itr_to_scoreme (request: Request):
    try:
        try:
            input_data = await request.json()
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Invalid json body","responseCode":None,"data":None})
        if not input_data :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Body should not be empty","responseCode":None,"data":None})

        if not input.get("email_id") :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Email_id is required","responseCode":None,"data":None})
        user_id = request.app.state.user_id

        database: AsyncIOMotorDatabase = request.app.state.mongo_db

        email_id = input_data.get("email_id")

        if not is_email_valid(email_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"message": "Invalid email id", "responseCode": None, "data": None})

        async with httpx.AsyncClient() as client:
            try:
                request_initiated_at = datetime.now(timezone.utc)
                response = await client.post(url=url.SCOREME_FILE_ITR_LINK,headers={
                            "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                            "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                        },
                        json={"email":email_id},
                        timeout=60.0)
            except httpx.HTTPError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message": "Internal server error", "responseCode": None, "data": None})

            scoreme_response_json = response.json() #it never breaks because of external server standard response across all the requests

            raise_itr_post_link_exception(scoreme_response_json)

        if scoreme_response_json["responseCode"] == "SRS016":
            #create a itr_reference_doc and store it on the collection
            itr_reference_doc = {
                "user_id": user_id,
                "reference_id": scoreme_response_json.get("data").get("referenceId"),
                "input_data": input_data,
                "itr_reference_id_status": "INPROGRESS",
                "link_validation_status": "SENT",
                "itr_request_status": scoreme_response_json.get("responseMessage"),
                "itr_request_response_code": scoreme_response_json.get("responseCode"),
                "itr_request_initiated_time": request_initiated_at,
                "webhook_status": "PENDING",
                "webhook_received_time": None,
                "webhook_response_code": None,
                "itr_report_url": None,
                "is_consumed": False,
                "consumed_at": None,
            }
            await database['itr_reference'].insert_one(itr_reference_doc)

            return  JSONResponse(status_code=status.HTTP_200_OK,content={"message":"Email triggered successfully","responseCode":scoreme_response_json.get("responseCode"),"data":{"itr_reference_id":scoreme_response_json.get("data").get("referenceId")}})
        else:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal server error","responseCode":None,"data":None})

    except HTTPException as e:
        logging.error(msg=str(e), exc_info=True)
        raise e

    except Exception as e:
        logging.error(msg=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal server error","responseCode":None,"data":None})



async def is_itr_report_already_there(request:Request) -> JSONResponse:
    try:
        user_id = request.state.user_id
        database = request.app.state.mongo_db
        itr_repo = database["itr_analyzed_report"]

        existing_report: Optional[dict] = await itr_repo.find_one(
            {"user_id": user_id},
            {"_id": 1}
        )

        if existing_report:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                          detail={"message": "Report already exists!", "data":{"is_proceed":False}})
        else:
            return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"No report found proceed","data":{"is_proceed":True}})
    except HTTPException as e:
        logging.error(msg=str(e), exc_info=True)
        print(f"Conflict might happen if we allow this user: {str(e)}")
        raise e
    except Exception as e:
        logging.error(msg=str(e),exc_info=True)
        print(f"Error while checking ITR report existence: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal Server Error","data":None})
