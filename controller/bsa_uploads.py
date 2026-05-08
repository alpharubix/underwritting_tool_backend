import asyncio
import copy
import uuid
from datetime import datetime, timezone, timedelta
import httpx
from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from services.scoreme_service import upload_to_scoreme,create_bsa_ref_document
from tasks.bsa_tasks import upload_files_to_gcs_and_save_metadata
import base64
import json
import google.genai as genai
import os
from utils.bsa_upload_utility import get_pdf_date_range_parser_prompt
from dotenv import (load_dotenv)
load_dotenv()
async def pdf_date_parser(files,data_params):
     #validate meta field
    try:
        required_fields = ["accountNumber", "entityType", "accountType", "bankCode"] #madatory input fields

        for field in required_fields:
            value = data_params.get(field)
            if not value or str(value).strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message":f"{field} is required"}

                )

        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message":"No files uploaded. Please upload at least one PDF file."}
            )

        if len(files) > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message":"Too many files. Maximum allowed is 12, but {len(files)} were uploaded."}
            )

        invalid_files = [f.filename for f in files if not f.filename.lower().endswith(".pdf")]
        if invalid_files:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={"message":f"Only PDF files are allowed. Invalid files: {', '.join(invalid_files)}"}
            )


        #get the date range for the uploaded list of pdf
        date_range = await upload_pdf_date_parser(files)

        #after getting the date range response from the ai agent generate the random uuid for that upload

        upload_ref_id = str(uuid.uuid4())

        #push the data and upload_ref_id to the map

        date_range['data']['files'] = files # append the files to the queue

        date_range['data']['input_data'] = data_params # append the data-params to the queue

        upload_map = UploadHashMap()

        upload_map.insert_data_to_map(upload_ref_id=upload_ref_id,data=copy.deepcopy(date_range))

        date_range['data'].pop('files')

        date_range['data'].pop('input_data')

        # append the generated upload_ref_id into the response

        date_range['data']["upload_ref_id"] = upload_ref_id

        return JSONResponse(status_code=status.HTTP_200_OK,content=date_range)

    except Exception as e:
        print("Error has been raised in bsa controller", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error please contact the admin for support."})



async def pdf_upload_consumer(user_id,input_body,mongodb_connection,background_task):
    try:

        if not input_body:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"upload_ref_id is required"})

        upload_ref_id = input_body.get("upload_ref_id")
        #if reference_id id is there check if the ref_id is there in the map or not

        upload_map = UploadHashMap()

        upload_map.peek_map()

        upload_data = upload_map.get_data_from_map(upload_ref_id=upload_ref_id)

        if not upload_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"upload_ref_id is expired","data":{"is_expired":True}})

        # if upload_ref_id found pass the file to the bsa handler

        # ── Forward to ScoreMe
        files = upload_data.get('data').get('files')
        data_params = upload_data.get('data').get('input_data')

        # scoreme_response,request_initiated_time = await upload_to_scoreme(files, data_params)
        #
        # if scoreme_response:
        #    # fetch the reference id and status from the dict
        #    reference_id = scoreme_response.get("data").get("referenceId")
        #    response_message = scoreme_response.get("responseMessage")
        #    response_code = scoreme_response.get("responseCode")
        #
        #    #create the bsa_ref document post successfull response from the scoreme server
        #    await create_bsa_ref_document(user_id=user_id,reference_id=reference_id,input_data=data_params,bsa_request_status="Submitted",bsa_request_initiated_time=request_initiated_time,bsa_request_response_message=response_message,bsa_request_response_code=response_code,mongobd_connection=mongodb_connection)
        #
        #    #create a background task to store the input bsa files to the storage object
        #    background_task.add_task(upload_files_to_gcs_and_save_metadata,files,user_id,reference_id,mongodb_connection)

        #return back the accepted message back to the clinet for every successfull uploads
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED,content={"message":"File is under processing we will let you know in the mail once the report got generated"})




    except Exception  as e:
        print("error raisers at pdf upload consumer",e)
        raise e



async def bank_names():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://sm-bsa-sandbox.scoreme.in/bsa/external/getBankNames",
                headers={
                    "clientId": os.getenv("CLIENT_ID"),
                    "clientSecret": os.getenv("CLIENT_SECRET")
                },
            )
            if response.status_code == 200:
                data = response.json().get("data")
                return JSONResponse(content={"message": "success","data":data})

            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error please contact the admin for support."})
    except HTTPException as e:
        raise e
    except Exception as e:
        print("Error has been raised in bsa get bank names controller", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={"message": "Internal server error please contact the admin for support."})



# async def is_pdf_are_consecutive(pdf_list,from_date:datetime,to_date:datetime):
#     try:
#         MODEL_ID = os.getenv("MODEL_ID")
#         # Only run this block for Gemini Developer API
#         client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#
#         # Build content parts — one entry per PDF
#         content_parts = []
#         for pdf_bytes in pdf_list:
#             pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
#             content_parts.append({
#                 "inline_data": {
#                     "mime_type": "application/pdf",
#                     "data": pdf_base64
#                 }
#             })
#
#         ANALYSIS_PROMPT = get_pdf_analysis_prompt(current_from=from_date,current_to=to_date)
#         # Add the analysis prompt at the end
#         content_parts.append(ANALYSIS_PROMPT)
#
#         # Send all PDFs to Gemini in a single call
#         async with client.aio as aclient:
#             response = await aclient.models.generate_content(
#                 model=MODEL_ID,
#                 contents=content_parts
#             )
#
#         # Parse Gemini's JSON decision
#         raw = response.text.strip()
#         if raw.startswith("```"):
#             raw = raw.strip("`").strip()
#             if raw.startswith("json"):
#                 raw = raw[4:].strip()
#
#         result = json.loads(raw)
#         print("This is the result from gemini",result)
#         return result
#
#     except Exception as e:
#         return {
#             "error": str(e),
#             "is_consecutive": None,
#             "statement_period": None,
#             "transaction_months": [],
#             "missing_months": [],
#             "total_missing": 0
#         }

async def upload_pdf_date_parser(pdf_list):

     try:
        MODEL_ID = os.getenv("MODEL_ID")
        # Only run this block for Gemini Developer API
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        content_parts = []
        for pdf_file in pdf_list:
            if hasattr(pdf_file, "read"):
                pdf_bytes = await pdf_file.read()  # UploadFile → bytes
            else:
                pdf_bytes = pdf_file  # already bytes

            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            content_parts.append({
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": pdf_base64
                }
            })

        ANALYSIS_PROMPT = get_pdf_date_range_parser_prompt()
        # Add the analysis prompt at the end
        content_parts.append(ANALYSIS_PROMPT)

        # Send all PDFs to Gemini in a single call
        async with client.aio as aclient:
            response = await aclient.models.generate_content(
                model=MODEL_ID,
                contents=content_parts
            )

        # Parse Gemini's JSON decision
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        result = json.loads(raw)
        print("This is the result from gemini", result)
        return result
     except Exception as e:
         raise e


class UploadHashMap:

    __upload_hashmap__ = dict() #class variable for storing and retriving data the state will be same across requests


    def insert_data_to_map(self,upload_ref_id,data):
        if upload_ref_id and data:
            #append the timestamp for memory management and data tracking
            created_at = datetime.now(timezone.utc)
            data["created_at"] = created_at
            self.__upload_hashmap__[upload_ref_id] = data

    def remove_data_from_map(self,upload_ref_id):
        if upload_ref_id:
            return self.__upload_hashmap__.pop(upload_ref_id, None)
        return None

    def get_data_from_map(self,upload_ref_id):
        if upload_ref_id:
            data = self.__upload_hashmap__.get(upload_ref_id)
            return data
        return None

    def peek_map(self):
        print("This is the map", self.__upload_hashmap__)

    async def clean_expired_entries(self):
        while True:
            print('CLEANING EXPIRED ENTRIES')
            current_time = datetime.now(timezone.utc)

            # store keys to delete
            expired_keys = []

            for key, value in self.__upload_hashmap__.items():

                created_at = value.get("created_at")

                # check if entry is older than 5 minutes
                if current_time - created_at > timedelta(minutes=5):
                    expired_keys.append(key)

            for key in expired_keys:
                del self.__upload_hashmap__[key]

            await asyncio.sleep(30)