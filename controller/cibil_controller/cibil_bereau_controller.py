import json
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette import status

from config.config import (
    SCOREME_GENERATE_CIBIL_OTP_URL,
    SCOREME_RESEND_CIBIL_OTP_URL,
    SCOREME_VALIDATE_CIBIL_OTP_URL,
    CibilOTPStatus,
    CibilWebhookStatus,
)
from custom_exceptions.scoreme_exceptions import (
    raise_cibil_otp_exception,
    raise_cibil_resend_otp_exception,
    raise_cibil_validate_otp_exception,
)

load_dotenv()
logger = logging.getLogger(__name__)

async def generate_cibil_report_otp(request)-> JSONResponse:
    try:
        try: #payload data validation
            input = await request.json()
        except json.decoder.JSONDecodeError:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"message":"Invalid JSON","data":None,"responsecode":"SYS_INPUT_ERR"})

        if not input:
         return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"message": "Payload is empty", "data": None, "responsecode": "SYS_INPUT_ERR"})

        default_input_parameter = ["first_name", "last_name", "middle_name","date_of_birth", "gender", "mobile_number", "address", "state", "pincode", "identity"]

        for parameter in default_input_parameter:
            if parameter not in input:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"message": f'{parameter} is required', "data": None, "responsecode": "SYS_INPUT_ERR"})
            elif input[parameter] is None:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"message": f'{parameter} value is empty', "data": None, "responsecode": "SYS_INPUT_ERR"})

        normalized_payload = {
            "bureauName": [
                "equifax"
            ],"firstName": input["first_name"],
             "middleName": input["middle_name"],
              "lastName": input["last_name"],
                "addressList": [
                {
                  "address":input["address"],
                  "state": input["state"],
                  "pinCode": input["pincode"],
                }
                  ],
                  "mobileList": [
                    input["mobile_number"],
                  ],
                  "identityList": [
                   input["identity"],
                  ],
                  "dateOfBirth": input["date_of_birth"],
                  "gender": input["gender"],
                  "referenceIdFlag": "0",
                  "vendorResponseFlag": "0"
        }
        #third party api calling for generating otp
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url=SCOREME_GENERATE_CIBIL_OTP_URL,headers={
                                "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                                "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                            },json=normalized_payload,timeout=20.0)

        except httpx.TimeoutException:
            return JSONResponse(status_code=status.HTTP_504_GATEWAY_TIMEOUT,content={"message": "Gateway Error", "data": None, "responsecode": "SYS_INT_ERR"})
        print(response.text)
        if response.status_code != 200:
            return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                content={"message": "Service Unavailable", "data": None, "responsecode": "SYS_INT_ERR"})


        api_response = response.json()


        if api_response["responseCode"] == "SOS174": #success fall back

            otp_flow_id = str(uuid.uuid6())

            construct_cibil_otp_manager = { #constructing otp management object
                "user_id":request.state.user_id,
                "otp_flow_id":otp_flow_id,
                "vendor":"equifax",
                "reference_id":api_response.get("data").get("referenceId"),
                "otp_status":CibilOTPStatus.OTP_SENT.value,
                "otp_generated_at":datetime.now(timezone.utc),
                "verification_attempts": 0,
                "resend_attempts": 0,
                "webhook_message":None,
                "webhook_status":CibilWebhookStatus.PENDING.value,
                "created_at":datetime.now(timezone.utc),
                "updated_at":datetime.now(timezone.utc)

            }

            coll = await request.app.state.mongo_db["cibil_otp_manager"].insert_one(construct_cibil_otp_manager)
            return JSONResponse(status_code=status.HTTP_200_OK,content={"message":api_response.get("responseMessage"),"data":{"otp_flow_id":otp_flow_id},"responseCode":api_response.get("responseCode")})

        return raise_cibil_otp_exception(api_response) #failure fall back

    except Exception as e:
        print("This is the error",e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,content={"message":"Internal server error","data":None,"responsecode":"SYS_INT_ERR"})

async def validate_cibil_otp(request):
    try:
        # Parse JSON
        try:
            payload = await request.json()
        except json.decoder.JSONDecodeError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid JSON",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        if not payload:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Payload is empty",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        # Required fields
        required_fields = ["otp_flow_id", "otp"]

        for field in required_fields:
            value = payload.get(field)

            if value is None or (isinstance(value, str) and not value.strip()):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "message": f"{field} is required",
                        "data": None,
                        "responseCode": "SYS_INPUT_ERR",
                    },
                )

        coll = request.app.state.mongo_db["cibil_otp_manager"]

        otp_document = await coll.find_one(
            {
                "otp_flow_id": payload["otp_flow_id"],
                "user_id": request.state.user_id,
            }
        )

        if otp_document is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "OTP flow not found.",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        if otp_document["otp_status"] == CibilOTPStatus.OTP_VERIFIED.value: #verification check to eliminate duplicate api call
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "OTP has already been verified.",
                    "data": None,
                    "responseCode": "ERU061",
                },
            )
        # if datetime.now(timezone.utc) > expires_at: #expiry check
        #     await coll.update_one(
        #         {"_id": otp_document["_id"]},
        #         {
        #             "$set": {
        #                 "otp_status": CibilOTPStatus.OTP_EXPIRED.value,
        #                 "updated_at": datetime.now(timezone.utc),
        #             }
        #         },
        #     )
        #
        #     return JSONResponse(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         content={
        #             "message": "OTP has expired.",
        #             "data": None,
        #             "responseCode": "SYS_OTP_EXPIRED",
        #         },
        #     )

        if otp_document["verification_attempts"] >= 3: #total attempts check
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Maximum OTP verification attempts exceeded.",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        await coll.update_one( #update the total number of attempts
            {"_id": otp_document["_id"]},
            {
                "$inc": {"verification_attempts": otp_document["verification_attempts"] + 1},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

        normalized_payload = {
            "referenceId": otp_document["reference_id"],
            "otp": payload["otp"],
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=SCOREME_VALIDATE_CIBIL_OTP_URL,
                    headers={
                        "clientId": os.getenv("CLIENT_ID"),
                        "clientSecret": os.getenv("CLIENT_SECRET"),
                    },
                    json=normalized_payload,
                    timeout=20,
                )
                print("Reached after API call")
                print("Status:", response.status_code)
                print("Body:", repr(response.text))

        except httpx.TimeoutException:
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "message": "Gateway timeout.",
                    "data": None,
                    "responseCode": "SYS_INT_ERR",
                },
            )
        api_response = response.json()

        if api_response["responseCode"] == "SRS016":

            await coll.update_one(
                {"_id": otp_document["_id"]},
                {
                    "$set": {
                        "otp_status": CibilOTPStatus.OTP_VERIFIED.value,
                        "verified_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": api_response["responseMessage"],
                    "data": {
                        "otp_flow_id": payload["otp_flow_id"]
                    },
                    "responseCode": api_response["responseCode"],
                },
            )
        if api_response["responseCode"] == "ERR541": #update the tp status to expired
            await coll.update_one(
                {"_id": otp_document["_id"]},
                {
                    "$set": {
                        "otp_status": CibilOTPStatus.OTP_EXPIRED.value,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        return raise_cibil_validate_otp_exception(api_response)

    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Unknown error. Contact administrator.",
                "data": None,
                "responseCode": "SYS_INT_ERR",
            },
        )

async def resend_cibil_otp(request):
    try:
        # Parse JSON
        try:
            payload = await request.json()
        except json.decoder.JSONDecodeError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid JSON",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        if not payload:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Payload is empty",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        otp_flow_id = payload.get("otp_flow_id")

        if not otp_flow_id or not otp_flow_id.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "otp_flow_id is required",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        coll = request.app.state.mongo_db["cibil_otp_manager"]

        otp_document = await coll.find_one(
            {
                "otp_flow_id": otp_flow_id,
                "user_id": request.state.user_id,
            }
        )

        if otp_document is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "OTP flow not found.",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        # Already verified
        if otp_document["otp_status"] == CibilOTPStatus.OTP_VERIFIED.value:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "OTP has already been verified.",
                    "data": None,
                    "responseCode": "ERU061",
                },
            )

        # Maximum resend limit
        if otp_document["resend_attempts"] >= 3:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "message": "Maximum OTP resend attempts exceeded.",
                    "data": None,
                    "responseCode": "ERU063",
                },
            )

        normalized_payload = {
            "referenceId": otp_document["reference_id"]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=SCOREME_RESEND_CIBIL_OTP_URL,
                    headers={
                        "clientId": os.getenv("CLIENT_ID"),
                        "clientSecret": os.getenv("CLIENT_SECRET"),
                    },
                    json=normalized_payload,
                    timeout=20,
                )

            print("Reached after API call")
            print("Status:", response.status_code)
            print("Body:", response.text)

        except httpx.TimeoutException:
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "message": "Gateway timeout.",
                    "data": None,
                    "responseCode": "SYS_INT_ERR",
                },
            )

        api_response = response.json()

        # Successful resend
        if api_response["responseCode"] == "SOS174":
            current_time = datetime.now(timezone.utc)

            await coll.update_one(
                {"_id": otp_document["_id"]},
                {
                    "$inc": {
                        "resend_attempts": 1,
                    },
                    "$set": {
                        "otp_status": CibilOTPStatus.OTP_RESENT.value,
                        "verification_attempts": 0,
                        "otp_generated_at": current_time,
                        "updated_at": current_time,
                    },
                },
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": api_response["responseMessage"],
                    "data": {
                        "otp_flow_id": otp_flow_id,
                    },
                    "responseCode": api_response["responseCode"],
                },
            )

        return raise_cibil_resend_otp_exception(api_response)

    except Exception as e:
        print("Error raised here", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Unknown error. Contact administrator.",
                "data": None,
                "responseCode": "SYS_INT_ERR",
            },
        )


async def cibil_webhook_consumer(request):
    try:
        input_data = await request.json()

        if not input_data:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Webhook data is empty",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        response_code = input_data.get("responseCode")
        message = input_data.get("message")
        data = input_data.get("data", {})
        reference_id = data.get("referenceId")

        if not reference_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Reference ID is missing",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        mongo_db = request.app.state.mongo_db
        otp_manager = mongo_db["cibil_otp_manager"]

        # Common function to update webhook message
        async def update_webhook_message(webhook_status=CibilWebhookStatus.PENDING.value):
            await otp_manager.update_one(
                {"reference_id": reference_id},
                {"$set": {"webhook_message": message,"webhook_status":webhook_status}},
            )

        if response_code == "EOV841":
            await update_webhook_message(webhook_status=CibilWebhookStatus.FAILED.value)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Webhook data successfully saved",
                    "data": None,
                    "responseCode": "SYS_OK",
                },
            )

        if response_code != "SRC001":
            await update_webhook_message(webhook_status=CibilWebhookStatus.FAILED.value)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Webhook ignored",
                    "data": None,
                    "responseCode": "SYS_OK",
                },
            )

        cibil_otp_doc = await otp_manager.find_one({"reference_id": reference_id})

        if not cibil_otp_doc:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "Reference ID not found",
                    "data": None,
                    "responseCode": "SYS_NOT_FOUND",
                },
            )

        json_url = data.get("jsonUrl")
        if not json_url:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "jsonUrl missing",
                    "data": None,
                    "responseCode": "SYS_INPUT_ERR",
                },
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                json_url,
                headers={
                    "clientId": os.getenv("CLIENT_ID"),
                    "clientSecret": os.getenv("CLIENT_SECRET"),
                },
            )

        if response.status_code != 200:
            return JSONResponse(
                status_code=response.status_code,
                content={
                    "message": "Failed to fetch CIBIL report",
                    "data": None,
                    "responseCode": "SYS_INT_ERR",
                },
            )

        cibil_report = {
            "user_id": cibil_otp_doc["user_id"],
            "reference_id": reference_id,
            "cibil_report":response.json(),
            "cibil_pulled_date": datetime.now(timezone.utc),
            "source_urls":data,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        }

        await mongo_db["cibil_report"].insert_one(cibil_report)

        await update_webhook_message(webhook_status=CibilWebhookStatus.SUCCESS.value)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Webhook data successfully saved",
                "data": None,
                "responseCode": "SYS_OK",
            },
        )
    except json.decoder.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": "Invalid JSON",
                "data": None,
                "responseCode": "SYS_INPUT_ERR",
            },
        )

async def get_list_cibil_reports(request,user_id) :
    try:
        mongo_db = request.app.state.mongo_db        

        cibil_report_collection = mongo_db["cibil_report"]

        cursor = cibil_report_collection.find(
            {"user_id": user_id},
            {"_id": 0, "reference_id": 1, "cibil_pulled_date": 1}
        )

        list_cibil_reports = await cursor.to_list(length=None)

        for cibil_report in list_cibil_reports:
            cibil_report["cibil_pulled_date"] = cibil_report["cibil_pulled_date"].isoformat()

        print(list_cibil_reports)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Cibil report list fetched successfully",
                "data": list_cibil_reports,
                "responseCode": "SYS_OK",
            },
        )
    except Exception as err:
        print("Error in get_list_cibil_reports",err)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,content={"message":"Internal server error contact the admin for support","data":None,"responseCode":"SYS_INT_ERR"})


async def get_list_r1xcrm_reports(request,acc_id:int):
    try:
        db = request.app.state.mongo_db

        user = await db["users"].find_one({"account_id": acc_id})

        if not user:
            raise HTTPException(status_code=404, detail={"message": "No user found for this account id"})

        return await get_list_cibil_reports(request,user_id=str(user["_id"]))
    
    except HTTPException as e:
        logger.error("Error raised at get_r1xcrm_gst_ref_id_status controller", exc_info=True)
        raise e
    except Exception:
        logger.error("Error raised at get_r1xcrm_gst_ref_id_status controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})


async def cibil_overview(reference_id: str, request):
    try:
        mongo_db = request.app.state.mongo_db

        cibil_report = await mongo_db["cibil_report"].find_one(
            {
                "reference_id": reference_id,
            },
            {
                "_id": 0,
                "reference_id": 1,
                "cibil_pulled_date": 1,
                "cibil_report.EquifaxRetail.BureauAnalysis": 1,
                "cibil_report.EquifaxRetail.generalInfo": 1,
            },
        )


        if cibil_report is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "CIBIL report not found",
                    "data": None,
                    "responseCode": "SYS_NOT_FOUND",
                },
            )

        cibil_report["cibil_pulled_date"] = cibil_report["cibil_pulled_date"].isoformat()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Overview fetched successfully",
                "data": cibil_report,
                "responseCode": "SYS_OK",
            },
        )

    except Exception as e:
        print("Error in get_cibil_overview:", e)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error contact the admin for support",
                "data": None,
                "responseCode": "SYS_INT_ERR",
            },
        )

async def account_summary(reference_id: str, request ):
    try:
        mongo_db = request.app.state.mongo_db

        cibil_report = await mongo_db["cibil_report"].find_one(
            {
                "reference_id": reference_id,
            },
            {
                "_id": 0,
                "reference_id": 1,
                "cibil_report.EquifaxRetail.accountSummary": 1,
            },
        )

        if cibil_report is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "CIBIL report not found",
                    "data": None,
                    "responseCode": "CBL_NOT_FOUND",
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Account summary fetched successfully",
                "data": cibil_report,
                "responseCode": "SYS_OK",
            },
        )

    except Exception as e:
        print("Error in get_cibil_account_summary:", e)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error contact the admin for support",
                "data": None,
                "responseCode": "SYS_INT_ERR",
            },
        )

async def payment_history(reference_id: str, request):
    try:
        mongo_db = request.app.state.mongo_db

        cibil_report = await mongo_db["cibil_report"].find_one(
            {
                "reference_id": reference_id,
            },
            {
                "_id": 0,
                "reference_id": 1,
                "cibil_report.EquifaxRetail.activeAccountRepaymentTrack": 1,
                "cibil_report.EquifaxRetail.closedAccountRepaymentTrack": 1,
            },
        )

        if cibil_report is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "CIBIL report not found",
                    "data": None,
                    "responseCode": "CBL_NOT_FOUND",
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Payment history fetched successfully",
                "data": cibil_report,
                "responseCode": "SYS_OK",
            },
        )

    except Exception as e:
        print("Error in get_cibil_payment_history:", e)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error contact the admin for support",
                "data": None,
                "responseCode": "SYS_INT_ERR",
            },
        )


async def analysis(reference_id: str, request):
    try:
        mongo_db = request.app.state.mongo_db

        cibil_report = await mongo_db["cibil_report"].find_one(
            {
                "reference_id": reference_id,
            },
            {
                "_id": 0,
                "reference_id": 1,
                "cibil_report.EquifaxRetail.ScoremeAnalysis": 1,
            },
        )

        if cibil_report is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "CIBIL report not found",
                    "data": None,
                    "responseCode": "CBL_NOT_FOUND",
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Analysis fetched successfully",
                "data": cibil_report,
                "responseCode": "SYS_OK",
            },
        )

    except Exception as e:
        print("Error in get_cibil_analysis:", e)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error contact the admin for support",
                "data": None,
                "responseCode": "SYS_INT_ERR",
            },
        )

async def otp_flow_id_webhook_status(otp_flow_id,request):
    try:
        mongo_db = request.app.state.mongo_db
        user_id = request.state.user_id
        report_status = CibilWebhookStatus.IN_PROGRESS

        webhook_status = await mongo_db["cibil_otp_manager"].find_one({"user_id": user_id,"otp_flow_id":otp_flow_id},{"webhook_status":1})

        if webhook_status :
            if webhook_status["webhook_status"] == CibilWebhookStatus.PENDING.value:
                report_status = CibilWebhookStatus.IN_PROGRESS.value
            elif webhook_status["webhook_status"] == CibilWebhookStatus.SUCCESS.value:
                report_status = CibilWebhookStatus.SUCCESS.value
            elif webhook_status["webhook_status"] == CibilWebhookStatus.FAILED.value:
                report_status = CibilWebhookStatus.FAILED.value

        else:

            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,content={"message":"Invalid otp_flow_id","data":None,"responseCode":"SYS_INPUT_ERR"},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,content={"message":"Otp webhook status fetched successdfully","data":{"webhook_status":report_status},"responseCode":"SYS_OK"},
        )
    except Exception as e:
        print("Error in get_cibil_analysis:", e)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error contact the admin for support",
                "data": None,
                "responseCode": "SYS_INT_ERR",
            },
        )

























































