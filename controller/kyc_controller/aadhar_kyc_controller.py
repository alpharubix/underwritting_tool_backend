import os
from datetime import datetime, timezone, timedelta
from json import JSONDecodeError
from uuid import uuid4

import httpx
from pymongo.errors import PyMongoError
from fastapi import HTTPException
from starlette import status
from httpx import AsyncClient, HTTPError, HTTPStatusError, RequestError
from starlette.responses import JSONResponse
import config.config as config
from config.config import KYC_FLOW_STATUS
from custom_exceptions.scoreme_exceptions import raise_aadhaar_verification_exception, raise_aadhaar_otp_exception, \
    raise_digilocker_url_exception, raise_digilocker_document_list_exception
import logging

from utils.error_codes_utility import AADHAAR_OTP_ERROR_MAP, DIGILOCKER_SESSION_STATUS_ERROR_MAP

logging.basicConfig(level=logging.INFO)


async def generate_aadhaar_otp(request):
    try:
        input = await request.json()

        if not input:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message":"Body cannot be empty"})
        if not input["aadhaar_number"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message":"Aadhaar number cannot be empty"})

    #validate the aadhaar number before sending it to the third party api

        aadhaar_number = input["aadhaar_number"]

        if len(aadhaar_number) != 12 or not aadhaar_number.isdigit():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message":"Invalid aadhaar number"})

    #proceed with third party api call

        async with AsyncClient() as client:
            try:
                response = await client.post(url=config.SCOREME_AADHAAR_VERIFICATION_URL,json={"aadhaar_number":aadhaar_number},headers={
                                "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                                "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                            },timeout=30.0)
            except HTTPError as err:
                logging.error(msg=str(err))
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error"})

        logging.info(msg=f"status of the scoreme api call {response.status_code}")
        data = response.json()

        raise_aadhaar_verification_exception(data)

        if data.get("responseCode") == "SOS174": #success immediate fall back
            aadhar_otp_coll = request.app.state.mongo_db["aadhaar_otp_manager"]
            user_id = request.state.user_id
            aadhar_otp_session_doc = {
                "user_id" : user_id,
                "aadhaar_number" : aadhaar_number,
                "reference_id":data.get("referenceId"),
                "otp_status":"PENDING",
                "response_message":data.get("responseMessage"),
                "created_at":datetime.now(timezone.utc),
                "last_updated_at":None,
            }
            await aadhar_otp_coll.insert_one(aadhar_otp_session_doc)
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message":"OTP successfully sent to mobile number","data":{"aadhaar_number":aadhaar_number,"reference_id":data.get("referenceId")}})

    except JSONDecodeError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message":"Invalid json"})
    except HTTPException as e:
        raise e
    except Exception as err:
        logging.exception(err)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error"}
        )


async def validate_aadhaar_otp(request):
    try:
        input = await request.json()

        if not input:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": "Body cannot be empty"})
        if not input.get("aadhaar_number") or not input.get("otp") or not input.get("reference_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"message": "Aadhaar number and Otp and referenceId is required"})

        aadhaar_number = input["aadhaar_number"]
        otp = input["otp"]
        reference_id = input["reference_id"]

        async with AsyncClient() as client:
            try:
                response = await client.post(url=config.SCOREME_AADHAAR_OTP_VERIFICATION,json={"otp":otp,"aadhaar_number":aadhaar_number,"consent":"Y"},headers={
                                "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                                "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                            })
                print(response.text)
                response.raise_for_status()

            except HTTPStatusError as err:
                print("ScoreMe returned HTTP error")
                print(f"Status Code: {err.response.status_code}")
                print(f"Response Text: {err.response.text}")
                print(f"Full Error: {err}")  # Add this for more details

            except RequestError as err:
                print("Network error occurred")
                print(f"Error Type: {type(err).__name__}")
                print(f"Error Message: {str(err)}")  # Convert exception to string
                print(f"Full Error: {err}")

            except Exception as err:
                print(f"Unexpected error: {type(err).__name__}")
                print(f"Details: {str(err)}")

        logging.info(msg=f"status of the scoreme api call {response.status_code} || response {response.text}")
        result = response.json()
        result_copy = result.copy()


        if result.get("responseCode") == "SRC001": #immediate success fall back


            aadhaar_details_coll = request.app.state.mongo_db["aadhaar_details"]
            aadhar_otp_doc =  request.app.state.mongo_db["aadhaar_otp_manager"]
            result["user_id"] = request.state.user_id
            result['created_at'] = datetime.now(timezone.utc)
            result['last_updated_at'] = datetime.now(timezone.utc)

            result.pop("created_at")
            result.pop("last_updated_at")


            await aadhaar_details_coll.insert_one(result)
            await aadhar_otp_doc.update_one({"reference_id":reference_id},{"$set":{"otp_status":"COMPLETED","last_updated_at":datetime.now(timezone.utc)}})



            return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"Otp validation success","data":result_copy})

        response_code = result.get("responseCode")

        if response_code in AADHAAR_OTP_ERROR_MAP:
            aadhar_otp_doc = request.app.state.mongo_db["aadhaar_otp_manager"]
            print("updated")
            update_doc = {
                "$set": {
                    "otp_status": AADHAAR_OTP_ERROR_MAP[response_code].get("message"),
                    "last_updated_at": datetime.now(timezone.utc)
                }
            }

            if response_code == "ETP011":
                update_doc["$inc"] = {"otp_attempts": 1}

            await aadhar_otp_doc.update_one(
                {"reference_id": reference_id},
                update_doc
            )
            raise_aadhaar_otp_exception(result)
    except PyMongoError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={"message": "Internal server error"})
    except HTTPException as err:
        logging.error(msg=str(err))
        print(err)
        raise err

async def fetch_user_aadhaar_details(request):
    try:
        user_id  = request.state.user_id
        aadhaar_details_coll = request.app.state.mongo_db["aadhaar_details"]

        aadhar_details = await aadhaar_details_coll.find_one({"user_id":user_id},{"data.photoBase64":0,"data.xmlBase64":0})

        if not aadhar_details:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail={"message": "aadhaar details not found for this user","data":None,"responseCode":"SYS_NOT_FOUND"})

        else:
            return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"aadhaar details fetched successfully","data":aadhar_details.get("data"),"responseCode":"SYS_OK"})


    except PyMongoError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={"message": "Internal server error"})
    except HTTPException as err:
        logging.error(msg=str(err))
        raise err

async def generate_digilocker_url(request):
    try:
        user_id = request.state.user_id

        try:
            async with AsyncClient() as session:
                response = await session.post(url=config.SCOREME_GENERATE_DIGI_URL,json={},headers={
                                "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                                "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                            },timeout=30)
        except HTTPError as err:
            logging.error(msg=str(err))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message": "Internal server error","data":None,"responseCode":"SYS_INT_ERR"})

        api_call_result = response.json()

        raise_digilocker_url_exception(api_call_result)

        if api_call_result.get("responseCode") == "SRC001":
            digilocker_session_coll = request.app.state.mongo_db["digilocker_session_manager"]
            kyc_flow_id = str(uuid4())
            data = {
                 "user_id": user_id,
                 "kyc_flow_id": kyc_flow_id,
                 "session_id": api_call_result.get("data").get("sessionId"),
                 "digilocker_url": api_call_result.get("data").get("digilockerUrl"),
                 "reference_id": api_call_result.get("referenceId"),
                 "responseCode": api_call_result.get("responseCode"),
                "responseMessage": api_call_result.get("responseMessage"),
                "session_status": KYC_FLOW_STATUS.CONSENT_PENDING.value,
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
             }

            await digilocker_session_coll.insert_one(data)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message":"Digilocker link generated successfully",
                    "data":{
                        "kyc_flow_id": kyc_flow_id,
                        "digilocker_url": api_call_result.get("data").get("digilockerUrl")
                    },
                    "responseCode":"SYS_OKAY"
                }
            )

        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail={"message": "Internal server error", "data": None, "responseCode": "SYS_INT_ERR"})
    except PyMongoError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={"message": "Internal server error", "data": None, "responseCode": "SYS_INT_ERR"})
    except HTTPException as err:
        logging.error(msg=str(err))
        raise err


async def get_kyc_flow_id_status(request):
    kyc_flow_id = None
    session_manager_coll = None
    user_id = request.state.user_id

    try:
        body = await request.json()

        if not body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Request body cannot be empty"
                }
            )

        kyc_flow_id = body.get("kyc_flow_id")

        if not kyc_flow_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "kyc_flow_id is required"
                }
            )

        session_manager_coll = request.app.state.mongo_db["digilocker_session_manager"]

        session_doc = await session_manager_coll.find_one(
            {"kyc_flow_id": kyc_flow_id, "user_id": user_id}
        )

        if not session_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Invalid kyc_flow_id","data":None,"responseCode":"SYS_INPUT_ERR"
                }
            )

        session_id = session_doc.get("session_id")
        expires_at = session_doc.get("expires_at")

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) >= expires_at:

            if session_doc.get("session_status") != KYC_FLOW_STATUS.EXPIRED: #guard for updating the same status gain and again for the same kyc_flow_id
                await session_manager_coll.update_one(
                    {"kyc_flow_id": kyc_flow_id, "user_id": user_id},
                    {
                        "$set": {
                            "session_status": KYC_FLOW_STATUS.EXPIRED.value,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Session expired","data": {"kyc_flow_id": kyc_flow_id,"session_status": KYC_FLOW_STATUS.EXPIRED}, "responseCode": "SYS_INPUT_ERR"}
            )

        async with AsyncClient(timeout=60) as client:
            response = await client.post(
                url=config.SCOREME_DIGILOCKER_SESSION_STATUS_URL,
                json={"sessionId":session_id},
                headers={
                                "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                                "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                            },timeout=30.0
            )

        result = response.json()

        response_code = result.get("responseCode")
        print("responsecode",response_code)

        if response_code == "RNP020" :
            session_status = KYC_FLOW_STATUS.INPROGRESS.value
        elif response_code =="RNP030" :
            session_status = KYC_FLOW_STATUS.CONSENT_REJECTED.value
        elif response_code == "ERT788" :
            session_status = KYC_FLOW_STATUS.TIMEOUT.value
        elif response_code == "SRC001" :
            session_status = KYC_FLOW_STATUS.CONSENT_APPROVED.value
        else:
            session_status = KYC_FLOW_STATUS.ERROR.value

        await session_manager_coll.update_one(
            {"kyc_flow_id": kyc_flow_id, "user_id": user_id},
            {
                "$set": {
                    "session_status": session_status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,content={
                "message": "Kyc flow status fetched successfully",
                "data": {"kyc_flow_id": kyc_flow_id,"kyc_url":session_doc.get("digilocker_url"),"session_status": session_status},
                "responseCode": "SYS_OK"
            }
        )
    except httpx.TimeoutException:

        logging.exception(
            f"Timeout while checking DigiLocker status for kyc_flow_id={kyc_flow_id}"
        )

        if kyc_flow_id and session_manager_coll is not None:
            await session_manager_coll.update_one(
                {"kyc_flow_id": kyc_flow_id,"user_id": user_id},
                {
                    "$set": {
                        "session_status": KYC_FLOW_STATUS.TIMEOUT.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,detail={"message": "Gateway timeout error", "data": None, "responseCode": "SYS_INT_ERR"})


    except JSONDecodeError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message": "Invalid JSON", "data": None, "responseCode": "SYS_INPUT_ERROR"})

    except HTTPException as err:
        logging.error(msg=str(err))
        raise err

    except Exception as err:

        logging.exception(str(err))

        if kyc_flow_id and session_manager_coll is not None:
            await session_manager_coll.update_one(
                {"kyc_flow_id": kyc_flow_id,"user_id":user_id},
                {
                    "$set": {
                        "session_status": KYC_FLOW_STATUS.ERROR.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message": "Internal server error", "data": None, "responseCode": "SYS_INT_ERR"})

# async def update_session_status(request):
#     try:
#         body = await request.json()
#         if not body:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail={
#                     "message": "Request body cannot be empty"
#                 }
#             )
#
#         session_id = body.get("session_id")
#         session_status = body.get("session_status")
#
#         if not session_id or not session_status:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail={
#                     "message": "both session_id and session_status are required"
#                 }
#             )
#         session_manager_coll = request.app.state.mongo_db["digilocker_session_manager"]
#
#         session_doc = await session_manager_coll.find_one(
#             {"session_id": session_id},{"_id":0,"created_at":0,"updated_at":0}
#         )
#
#         if not session_doc:
#             raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,detail = {
#         "message": "Invalid session_id"})
#
#         else:
#             await session_manager_coll.update_one(
#                 {"session_id": session_id},
#             {"$set": {"session_status": session_status}})
#
#             return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"Session status updated successfully","data":session_doc,"responseCode":"SYS_OKAY"})
#
#     except HTTPException as err:
#         logging.error(msg=str(err))
#         raise err
#
#     except JSONDecodeError as err:
#         logging.error(msg=str(err))
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message": "Invalid JSON", "data": None, "responseCode": "SYS_INPUT_ERROR"})

async def update_session_status(request):
    try:
        body = await request.json()
        if not body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Request body cannot be empty"
                }
            )

        session_id = body.get("session_id")
        session_status = body.get("session_status")

        if not session_id or not session_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "both session_id and session_status are required"
                }
            )
        session_manager_coll = request.app.state.mongo_db["digilocker_session_manager"]

        session_doc = await session_manager_coll.find_one(
            {"session_id": session_id}, {"_id": 0, "created_at": 0, "updated_at": 0}
        )

        if not session_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
                "message": "Invalid session_id"})


        await session_manager_coll.update_one(
            {"session_id": session_id},
            {"$set": {"session_status": session_status}}
        )

        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "message": "Session status updated successfully",
            "data": session_doc,
            "responseCode": "SYS_OKAY"
        })

    except HTTPException as err:
        logging.error(msg=str(err))
        raise err

    except JSONDecodeError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "message": "Invalid JSON",
            "data": None,
            "responseCode": "SYS_INPUT_ERROR"
        })

async def get_documents_list(request):
    try:
        body = await request.json()
        if not body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Request body cannot be empty"
                }
            )

        kyc_flow_id = body.get("kyc_flow_id")

        if not kyc_flow_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "kyc_flow_id is required"
                }
            )

        session_manager_coll = request.app.state.mongo_db["digilocker_session_manager"]

        session_doc = await session_manager_coll.find_one(
            {"kyc_flow_id": kyc_flow_id}
        )


        if not session_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "message": "Invalid kyc_flow_id"})

        session_id = session_doc.get("session_id")

        async with AsyncClient() as client:
            try:
                response = await client.post(url=config.SCOEME_DIGILOCKER_DOCUMENT_LIST_URL,json={"sessionId":session_id},headers={
                                "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                                "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                            },timeout=30.0)
            except HTTPError as err:
                logging.error(msg=str(err))
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error"})

        api_call_result = response.json()

        raise_digilocker_document_list_exception(api_call_result)

        if api_call_result.get("responseCode") == "SRC001":
            user_id = request.state.user_id
            user_kyc_coll = request.app.state.mongo_db["user_kyc_documents"]

            doc = {
                "user_id":user_id,
                "document_list":api_call_result.get("data").get("documents"),
                "kyc_flow_id": kyc_flow_id,
                "session_id": session_id,
                "updated_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc)
            }

            await user_kyc_coll.insert_one(doc)

            #after insertion removing unwanted meta data
            doc.pop("updated_at")
            doc.pop("created_at")
            doc.pop("_id")
            doc.pop("session_id")

            return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"message": "Documents list fetched successfully","data":doc,"responseCode": "SYS_OKAY"})
    except HTTPException as err:
        logging.error(msg=str(err))
        raise err

    except JSONDecodeError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"message": "Invalid JSON", "data": None, "responseCode": "SYS_INPUT_ERROR"})

     
async def fetch_documents_url(request):
    try:
        body = await request.json()
        if not body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Request body cannot be empty"
                }
            )

        kyc_flow_id = body.get("kyc_flow_id")
        document_format = body.get("document_format")
        document_uri = body.get("document_uri")
        document_type = body.get("document_type")

        if not kyc_flow_id or not document_format or not document_uri or not document_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "kyc_flow_id,document_format,document_uri,document_type are required"
                }
            )
        session_manager_coll = request.app.state.mongo_db["user_kyc_documents"]

        session_doc = await session_manager_coll.find_one({"kyc_flow_id": kyc_flow_id})
        if not session_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
                "message": "Invalid kyc_flow_id"})

        session_id = session_doc.get("session_id")
        async with AsyncClient() as client:
            try:
                response = await client.post(url=config.SCOREME_DICILOCKER_DOCUMENT_DOWNLOAD_URL,json={"sessionId":session_id,"documentFormat":document_format,"documentUri":document_uri},headers={
                                "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                                "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                            },timeout=30.0)
                print(response.text)
            except HTTPError as err:
                logging.error(msg=str(err))
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail={"message": "Internal server error"})

        api_call_result = response.json()

        raise_digilocker_document_list_exception(api_call_result)

        if api_call_result.get("responseCode") == "SRC001":


            user_kyc_coll = request.app.state.mongo_db["user_kyc_documents"]

            result = await user_kyc_coll.update_one(
                {
                    "session_id": session_id,
                    "document_list.documentType": document_type
                },
                {
                    "$set": {
                        "document_list.$.documentUrl": api_call_result.get("data").get("documentUrl"),
                        "document_list.$.document_url_fetched_at": datetime.now(timezone.utc)
                    }
                }
            )

            print("matched:", result.matched_count)
            print("modified:", result.modified_count)

        return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"message": "Document url fetched successfully", "data": api_call_result.get("data"),
                                 "responseCode": "SYS_OKAY"})

    except HTTPException as err:
        logging.error(msg=str(err))
        raise err

    except JSONDecodeError as err:
        logging.error(msg=str(err))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"message": "Invalid JSON", "data": None, "responseCode": "SYS_INPUT_ERROR"})


async def is_document_already_exists(request):
    try:
        user_id = request.state.user_id

        user_kyc_coll = request.app.state.mongo_db["user_kyc_documents"]

        documents = await user_kyc_coll.find_one(
            {"user_id": user_id},
            {
                "_id": 0,
                "created_at": 0,
                "updated_at": 0
            }
        )



        if not documents:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "No Kyc Documents found for this user","data":{},"responseCode": "SYS_NOT_FOUND"})

        else:
            for document in documents.get("document_list"): #serialize documents list for response
                if document.get("document_url_fetched_at"):
                    document.pop("document_url_fetched_at") #pop datetime meta field

            return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"Kyc documents found","data":documents,"responseCode": "SYS_OKAY"})
    except HTTPException as err:
        logging.error(msg=str(err))
        raise err

async def get_current_session(request):

    try:
        user_id = request.state.user_id

        session_manager_coll = request.app.state.mongo_db["digilocker_session_manager"]

        latest_session = await session_manager_coll.find_one({"user_id":user_id},sort=[("created_at", -1)])

        if not latest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No Kyc Session found", "data": None, "responseCode": "SYS_NOT_FOUND"
                }
            )
        else:
            kyc_flow_id = latest_session.get("kyc_flow_id")
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={
                    "message": "Kyc session found",
                    "data": {"kyc_flow_id": kyc_flow_id},
                    "responseCode": "SYS_OK"
                }
            )
    except HTTPException as err:
        raise err
    except Exception as err:
        logging.error(msg=str(err))
        print(err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Internal server error", "data": None, "responseCode": "SYS_INT_ERR"})


































