import json
import logging
import os
import re
from typing import Optional
import uuid
import httpx
import pymongo
import pymongo.errors as pymongo_errors
from datetime import datetime, timezone
from json import JSONDecodeError
from bson import ObjectId
from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorCollection,AsyncIOMotorDatabase
from starlette.requests import Request
from starlette.responses import JSONResponse
from httpx import AsyncClient
from httpx import HTTPError
from config import config
from config.config import AllowedService, ServicePrice, WalletStatus, ServiceRequestStatus, UpstreamStatus
from custom_exceptions.scoreme_exceptions import raise_gst_basic_info_expectation, raise_gst_otp_expectation, \
    raise_gst_validate_otp_exception, raise_gst_post_gstin_exception
from services.scoreme_service import update_document
from services.service_request_service import create_service_request, get_service_request, update_service_request
from controller.backgroud_task_controller import send_gst_report_mail_based_on_request
from controller.payments_controller.wallet_contoller import consume_reserved_balance, release_reserved_balance, reserve_service_balance
logger = logging.getLogger(__name__)
from fastapi import status as status

ALLOWED_ROLES=('ANCHOR','SUPER_ANCHOR','ADMIN')

def _is_gstin_valid_for_new_registration(primary_gst,upcoming_gst):
        primary_pan = primary_gst[3:12]
        upcoming_pan = upcoming_gst[3:12]

        if primary_pan != upcoming_pan:
            return False
        else:
            return True

async def get_gstin(request: Request,cust_id :Optional[str]=None)->JSONResponse:
    try:
        user_id = request.state.user_id
        user_coll : AsyncIOMotorCollection = request.app.state.mongo_db["users"]
        requester_role = request.state.role
        user = None
        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=400,
                    detail="cust_id is required"
                )
            user_id = cust_id

        print(user_id)
        user = await user_coll.find_one({"_id":ObjectId(user_id)},{"_id":1,"gst_number":1,"secondary_gst_list":1})

        if not user:
            raise HTTPException(status_code=404, detail={"message":"user not found"})

        if user.get("gst_number"):

            gstin_list = [user["gst_number"]]

            if user.get("secondary_gst_list"):
                gstin_list.extend(user["secondary_gst_list"])

            return JSONResponse(
                status_code=200,
                content={
                    "message": "GST number found",
                    "gst_number": gstin_list,
                    "is_found": True
                }
            )
        return JSONResponse(
                status_code=200,
                content={
                    "message": "GST number not found",
                    "gst_number": None,
                    "is_found": False
                }
            )

    except HTTPException as e:
        logger.error("Error raised at get_gstin controller",e)
        raise e

    except Exception as e:
        logger.error("Error raised at get_gstin controller",e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error contact the administrator",
            }
        )

async def add_new_gst(request,cust_id:Optional[str]=None):
    try:
        #step1-> validate the upcoming gstin number
        body = await request.json()
        if not body:
            raise HTTPException(status_code=400, detail={"message": "Body cannot be empty"})

        gstin :str= body.get("gstin")

        if not gstin:
            raise HTTPException(status_code=400, detail={"message": "GSTIN is required"})

        gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        if not re.match(gstin_pattern, gstin.upper()):
            raise HTTPException(status_code=400, detail={"message": "Invalid GSTIN format"})

        #step2-> Get the primary gst number of this user

        user_collection = request.app.state.mongo_db["users"]

        user_id = request.state.user_id
        requester_role = request.state.role

        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer ID is required"
                )
            user_id = cust_id
        primary_gst_info = await user_collection.find_one({"_id": ObjectId(user_id)},{"_id":0,"gst_number":1,"secondary_gst_list":1})

        primary_gst = primary_gst_info["gst_number"]

        #edge case covering
        if primary_gst==gstin.strip():
            raise HTTPException(status_code=400, detail={"message": "GSTIN already Added"})

        if _is_gstin_valid_for_new_registration(primary_gst,gstin):

            #add this new gst to the users db as secondary gst numbers
            existing_secondary_gst = primary_gst_info.get("secondary_gst_list")

            if existing_secondary_gst:
                #update the existing_gst list with the new gst
                result = await user_collection.update_one( {"_id": ObjectId(user_id)},{"$addToSet": {"secondary_gst_list": gstin}}) #edge case covering
                if result.modified_count == 0:
                    raise HTTPException(
                        status_code=400,
                        detail={"message": "GSTIN already Added to GST list"})

            else:
                # Create the secondary_gst list with the first GSTIN
                await user_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$set": {
                            "secondary_gst_list": [gstin]
                        }
                    }
                )


            return JSONResponse(
                status_code=200,
                content={"message": "GSTIN Added Successfully", "data": {"gstin": gstin.upper()},"is_completed":True})
        else:
            raise HTTPException(status_code=400, detail={"message": "Pan number miss match found"})
    except JSONDecodeError :
        raise HTTPException(status_code=400, detail={"message": "Invalid Json"})
    except HTTPException as e:
        print(e)
        raise e
    except Exception as e:
        print(e)
        raise  HTTPException(status_code=500, detail={"message": "Internal server error contact the administrator"})

async def update_gstin(request: Request,cust_id:Optional[str]=None)->JSONResponse:

    try:
        user_id = request.state.user_id
        user_coll: AsyncIOMotorCollection = request.app.state.mongo_db["users"]
        requester_role = request.state.role
        if requester_role in ALLOWED_ROLES:
                    if not cust_id:
                        raise HTTPException(
                            status_code=400,
                            detail="cust_id is required"
                        )
                    user_id = cust_id
        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid JSON format in request body"}
            )

        if not body:
            raise HTTPException(status_code=400, detail={"message": "Body cannot be empty"})

        gstin = body.get("gstin")

        if not gstin:
            raise HTTPException(status_code=400, detail={"message": "GSTIN is required"})

        gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        if not re.match(gstin_pattern, gstin.upper()):
            raise HTTPException(status_code=422, detail={"message": "Invalid GSTIN format"})

        user = await user_coll.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(status_code=404, detail={"message": "User not found"})

        result = await user_coll.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"gst_number": gstin.upper(), "updated_at": datetime.now(timezone.utc)}},
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail={"message": "Failed to update GSTIN"})

        return JSONResponse(
            status_code=200,
            content={"message": "GSTIN updated successfully","data":{"gstin": gstin.upper()}}
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        logger.error("Error raised at update_gstin controller",e)
        raise HTTPException(status_code=500, detail={"message": f"Internal server error: {str(e)}"})

async def get_gstin_basic_info(request: Request,cust_id:Optional[str]=None) -> JSONResponse:
    try:
        user_id = request.state.user_id
        requester_role = request.state.role
        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=400,
                    detail="cust_id is required"
                )
            user_id = cust_id
        gstin_info_coll: AsyncIOMotorCollection = request.app.state.mongo_db["gstin_basic_info"]

        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid JSON format in request body"},
            )

        if not body:
            raise HTTPException(
                status_code=400,
                detail={"message": "Body cannot be empty"},
            )

        gst_list = body.get("gstin")

        if not gst_list:
            raise HTTPException(
                status_code=400,
                detail={"message": "GSTIN list is required"},
            )

        gst_list = [gst.strip().upper() for gst in gst_list]

        response_data = []
        missing_gstins = []

        # Check which GSTINs are already present
        for gstin in gst_list:
            gst_info = await gstin_info_coll.find_one({"gstin": gstin})

            if gst_info:
                response_data.append(
                    {
                        "gstin": gst_info.get("gstin"),
                        "legalNameOfBusiness": gst_info.get("legalNameOfBusiness"),
                        "tradeName": gst_info.get("tradeName"),
                        "gstinStatus": gst_info.get("gstinStatus"),
                        "taxpayerType": gst_info.get("taxpayerType"),
                        "constitutionOfBusiness": gst_info.get(
                            "constitutionOfBusiness"
                        ),
                        "natureOfBusiness": gst_info.get("natureOfBusiness"),
                        "dateOfRegistration": gst_info.get("dateOfRegistration"),
                    }
                )
            else:
                missing_gstins.append(gstin)

        # Fetch missing GSTINs from ScoreMe
        if missing_gstins:
            for gstin in missing_gstins:
                async with AsyncClient() as client:
                    try:
                        response = await client.post(
                            config.SCOREME_GST_INFO_URL,
                            headers={
                                "clientId": os.getenv("CLIENT_ID"),
                                "clientSecret": os.getenv("CLIENT_SECRET"),
                            },
                            json={"gstin": gstin},
                            timeout=60.0,
                        )

                        scoreme_response_json = response.json()

                    except HTTPError as e:
                        raise e

                raise_gst_basic_info_expectation(scoreme_response_json)

                gst_data = scoreme_response_json.get("data", [])

                gst_data["user_id"] = user_id


                await gstin_info_coll.insert_one(gst_data)

                response_data.append(
                    {
                        "gstin": gst_data.get("gstin"),
                        "legalNameOfBusiness": gst_data.get("legalNameOfBusiness"),
                        "tradeName": gst_data.get("tradeName"),
                        "gstinStatus": gst_data.get("gstinStatus"),
                        "taxpayerType": gst_data.get("taxpayerType"),
                        "constitutionOfBusiness": gst_data.get(
                            "constitutionOfBusiness"
                        ),
                        "natureOfBusiness": gst_data.get("natureOfBusiness"),
                        "dateOfRegistration": gst_data.get("dateOfRegistration"),
                    }
                )

        return JSONResponse(
            status_code=200,
            content={
                "message": "GST information fetched successfully",
                "data": response_data,
            },
        )

    except HTTPException as e:
        raise e

    except HTTPError as e:
        logger.error("Error raised at get_gstin_basic_info controller", str(e))
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error"},
        )

    except Exception as e:
        logger.error("Error raised at get_gstin_basic_info controller", str(e))
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error"},
        )



async def get_gst_otp(request: Request)->JSONResponse:
    try:
        try:
            input_data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail={"message": "Invalid JSON format in request body"})

        if not input_data:
            raise HTTPException(status_code=400, detail={"message": "Body cannot be empty"})

        gstin = input_data.get("gstin")
        user_name = input_data.get("user_name")

        if not gstin or not user_name:
            raise HTTPException(status_code=400, detail={"message": "Both gstin and user_name is required"})


        async with AsyncClient() as client:
            try:
                response = await client.post(url=config.SCORME_GST_USER_NAME_OTP,headers={
                            "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                            "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                        },
                        json={"gstin":[gstin.upper()],"username":[user_name]},
                        timeout=60.0)
            except HTTPError as e:
                raise e


        scoreme_response_json = response.json()

        raise_gst_otp_expectation(scoreme_response_json)

        if scoreme_response_json.get("responseCode") == "SRO037":

            otp_reference_id = str(uuid.uuid4())

            database : AsyncIOMotorDatabase = request.app.state.mongo_db

            gst_otp_manager_coll : AsyncIOMotorCollection = database["gst_otp_manager"]

            otp_management_dict = {
                "gstin": scoreme_response_json.get("data").get("gstin"),
                "otp_reference_id": otp_reference_id,
                "is_authenticated":False,
                "is_expired":False,
                "otp_generated_at":datetime.now(timezone.utc),
            }

            await gst_otp_manager_coll.insert_one(otp_management_dict)

            return JSONResponse(
                status_code=200,
                content={"message":"OTP Generated Successfully","data":{"gstin":scoreme_response_json.get("data").get("gstin"),"otp_reference_id":otp_reference_id}}
            )


        else: #this case will only run if any unexpected error code that is not covered in the api doc is thrown rare but guard is there
            raise HTTPException(status_code=500, detail={"message": "Internal server error contact admin for support"})



    except HTTPException as e:
        logger.error("Error raised at get_gst_otp_info controller", exc_info=True)
        raise e
    except HTTPError as e:
        logger.error("Error raised at get_gst_otp_info controller",exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})
    except Exception as e:
        logger.error("Error raised at get_gst_otp_info controller",exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})


async def validate_gst_otp_info(request: Request) -> JSONResponse:
    try:
        try:
            input_data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid JSON format in request body"}
            )

        if not input_data:
            raise HTTPException(
                status_code=400,
                detail={"message": "Body cannot be empty"}
            )

        gstin            = input_data.get("gstin")
        otp              = input_data.get("otp")
        otp_reference_id = input_data.get("otp_reference_id")

        if not gstin or not otp or not otp_reference_id:
            raise HTTPException(
                status_code=400,
                detail={"message": "gstin, otp and otp_reference_id are required"}
            )

        #pre database check for otp validity
        database: AsyncIOMotorDatabase             = request.app.state.mongo_db
        gst_otp_manager_coll: AsyncIOMotorCollection = database["gst_otp_manager"]

        otp_doc = await gst_otp_manager_coll.find_one(
            {"otp_reference_id": otp_reference_id}
        )

        if not otp_doc:
            raise HTTPException(
                status_code=404,
                detail={"message": "Invalid otp_reference_id. No OTP request found."}
            )

        if otp_doc.get("is_authenticated"):
            raise HTTPException(
                status_code=400,
                detail={"message": "OTP already authenticated for this reference ID."}
            )

        if otp_doc.get("is_expired"):
            raise HTTPException(
                status_code=400,
                detail={"message": "OTP has expired. Please regenerate OTP."}
            )


        async with AsyncClient() as client:
            try:
                response = await client.post(
                    url=config.SCOREME_GST_OTP_AUTHENTICATION,
                    headers={
                        "clientId":     os.getenv("CLIENT_ID"),
                        "clientSecret": os.getenv("CLIENT_SECRET")
                    },
                    json={
                        "gstin": [gstin.upper()],
                        "otp":   [otp]
                    },
                    timeout=60.0
                )
            except HTTPError as e:
                raise e

        scoreme_response_json = response.json()

        # Raises HTTPException for any known error code
        raise_gst_validate_otp_exception(scoreme_response_json)

        #Success: SAC041 — update state flags ───────────────────────────
        if scoreme_response_json.get("responseCode") == "SAC041":

            await gst_otp_manager_coll.update_one(
                {"otp_reference_id": otp_reference_id},
                {"$set": {
                    "is_authenticated": True,
                    "is_expired":       True,        # consumed — block reuse
                    "authenticated_at": datetime.now(timezone.utc)
                }}
            )

            return JSONResponse(
                status_code=200,
                content={
                    "message": "OTP Validated Successfully",
                    "data": {
                        "gstin":scoreme_response_json.get("data").get("gstin"),
                        "is_otp_validated":True,
                    }
                }
            )

        else:
            raise HTTPException(
                status_code=500,
                detail={"message": "Internal server error, contact admin for support"}
            )

    except HTTPException as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise e
    except HTTPError as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})
    except Exception as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})


async def send_gstin_to_score_me(request: Request,cust_id:str)->JSONResponse:
    try:
        try:
            user_id = request.state.user_id
            requester_role = request.state.role
            if requester_role in ALLOWED_ROLES:
                if not cust_id:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Cust ID not found !")
                user_id = cust_id

            input_data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail={"message": "Invalid JSON format in request body"})
        if not input_data:
            raise HTTPException(status_code=400, detail={"message": "Body cannot be empty"})

        gstin = input_data.get("gstin",None)
        from_month = input_data.get("from_month", None)
        to_month = input_data.get("to_month", None)

        if not gstin or not from_month or not to_month:
           raise HTTPException(status_code=400, detail={"message": "gstin and from_month and to_month are required"})


        async with AsyncClient() as client:
           try:
                request_initiated_at = datetime.now(timezone.utc)
                response = await client.post(url=config.SCOREME_GST_POST_GSTIN,headers={
                        "clientId":     os.getenv("CLIENT_ID"),
                        "clientSecret": os.getenv("CLIENT_SECRET")
                    },json={"gstin":[gstin.upper()],"from":[from_month],"to":[to_month]},timeout=60.0)

           except HTTPError as e:
               raise e

        print(response.text)
        scoreme_response_json = response.json()

        raise_gst_post_gstin_exception(scoreme_response_json)

        if response.status_code == 404: #guard for 404 status code
            raise HTTPException(status_code=404, detail={"message": "Gst data not found for this months"})

        if scoreme_response_json.get("responseCode") == "SRS016":

            database:AsyncIOMotorDatabase = request.app.state.mongo_db
            gst_reference_coll:AsyncIOMotorCollection = database["gst_reference"]
            reference_id = scoreme_response_json.get("data").get("referenceId")

            # if this blocks works that means the result is successfully

            gst_reference_doc = {
                "gstin": [gstin.upper()],
                "user_id":user_id,
                "reference_id":reference_id,
                "input_data": input_data,
                "from_month": from_month,
                "to_month": to_month,
                "gst_reference_id_status": "INPROGRESS",
                "gst_request_status":scoreme_response_json.get("responseMessage"),
                "gst_request_response_code":scoreme_response_json.get("responseCode"),
                "gst_request_initiated_time":request_initiated_at,
                "webhook_status":"PENDING",
                "webhook_received_time":None,
                "webhook_response_code":None,
                "gst_report_url":None,
                "is_consumed":False,
                "consumed_at":None,
            }

            await gst_reference_coll.insert_one(gst_reference_doc)

            if requester_role in ALLOWED_ROLES:
                reserve_result = await reserve_service_balance(
                    request=request,
                    user_id=user_id,
                    service=AllowedService.GST.value,
                    amount=ServicePrice.GST.value,
                    reference_id=reference_id,
                )

                if not reserve_result.get("success"):
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail={"message": reserve_result.get("message")},
                    )

                await create_service_request(
                    database=database,
                    user_id=user_id,
                    requested_by=request.state.user_id,
                    service=AllowedService.GST.value,
                    amount=ServicePrice.GST.value,
                    reference_id=reference_id,
                )
                print("Reserved amount for Gst",reserve_result)


            return JSONResponse(status_code=202,content={"message": "gstin sent successfully","data":{"gstin":gstin,"gst_reference_id":reference_id}})

        else:
            raise HTTPException(status_code=500, detail={"message": "unknown error from external server contact admin for support"})



    except HTTPException as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise e
    except HTTPError as e:
        logger.error("Error raised at score me api call in validate_gst_otp_info controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})

    except Exception as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})


async def gst_ref_id_status(request: Request)->JSONResponse:
    try:
        try:
            input_data = await request.json()
        except json.decoder.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail={"message": "Invalid JSON format in request body"})

        if not input_data:
            raise HTTPException(status_code=400, detail={"message": "Body cannot be empty"})

        gst_ref_id = input_data.get("gst_ref_id", None)

        if not gst_ref_id :
            raise HTTPException(status_code=400, detail={"message": "At least one gst reference id is required"})

        gst_reference_id_status = [] #stores the retrived  status from the db
        gst_reference_coll : AsyncIOMotorCollection = request.app.state.mongo_db["gst_reference"]

        for ref_id in gst_ref_id:
            doc = await gst_reference_coll.find_one({"reference_id":ref_id},{"_id":0,"gst_reference_id_status":1})
            if doc:
                gst_reference_id_status.append({"gst_reference_id_status":doc["gst_reference_id_status"],"gst_reference_id":ref_id})

        return JSONResponse(status_code=200,content={"message":"status fetch successfully","data":{"gst_reference_id_status":gst_reference_id_status}})

    except HTTPException as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise e

    except Exception as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})


async def get_all_user_ref_ids(request: Request,cust_id:str,is_crm:bool = False)->JSONResponse:
    try:
        if is_crm:
            user_id = cust_id
        else:
            user_id = request.state.user_id
            requester_role = request.state.role
            if requester_role in ALLOWED_ROLES:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Forbidden access !")

        gst_ref_coll: AsyncIOMotorCollection = request.app.state.mongo_db["gst_reference"]
        docs = await gst_ref_coll.find({"user_id":user_id},{"_id":0,"gst_reference_id_status":1,"from_month":1,"to_month":1,"reference_id":1,"gstin":1}).to_list(None)

        if not docs:
            raise HTTPException(status_code=404, detail={"message": "No reference id found for this user"})
        #serialize response data
        for doc in docs:
            doc['gstin'] = doc['gstin'][0]
        return JSONResponse(status_code=200,content={"message":"Gst reference id list fetch success","data":docs})

    except HTTPException as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise e
    except Exception as e:
        logger.error("Error raised at validate_gst_otp_info controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})


async def get_r1xcrm_gst_ref_id_status(request: Request,acc_id:int)->JSONResponse:
    try:
        db = request.app.state.mongo_db

        user = await db["users"].find_one({"account_id":acc_id})

        if not user:
            raise HTTPException(status_code=404, detail={"message": "No user found for this account id"})

        return await get_all_user_ref_ids(request,cust_id=str(user["_id"]),is_crm=True)
    except HTTPException as e:
        logger.error("Error raised at get_r1xcrm_gst_ref_id_status controller", exc_info=True)
        raise e
    except Exception as e:
        logger.error("Error raised at get_r1xcrm_gst_ref_id_status controller", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})



async def gst_webhook_consumer(webhook_data:dict,database:AsyncIOMotorDatabase,background_task:BackgroundTasks)->JSONResponse:
    try:
        if webhook_data.get("responseCode") != "SRC001": #guard for releasing the reserved amount if the webhook response is failed
            data = webhook_data.get("data") or {}
            reference_id = data.get("referenceId")
            gst_ref_doc = await database["gst_reference"].find_one(
                {"reference_id": reference_id},
                {"_id": 0, "user_id": 1}
            )
            user_id = gst_ref_doc.get("user_id") if gst_ref_doc else None

            await update_document(
                collection=database["gst_reference"],
                filter={"reference_id": reference_id},
                fields={
                    "gst_reference_id_status": "FAILED",
                    "webhook_status": "RECEIVED",
                    "webhook_received_time": datetime.now(timezone.utc),
                    "webhook_response_code": webhook_data.get("responseCode"),
                    "webhook_response_message": webhook_data.get("responseMessage"),
                    "gst_report_url": data.get("reportUrl"),
                },
            )

            service_request = await get_service_request(
                database=database,
                filters={
                    "reference_id": reference_id,
                    "service_status": ServiceRequestStatus.SERVICE_STATUS_PROCESSING.value,
                },
            )

            if service_request and user_id:
                release_result = await release_reserved_balance(
                    database=database,
                    service=AllowedService.GST.value,
                    user_id=user_id,
                    reference_id=reference_id,
                    amount=ServicePrice.GST.value,
                )

                if release_result.get("success"):
                    await update_service_request(
                        database=database,
                        reference_id=reference_id,
                        fields={
                            "wallet_status": WalletStatus.RELEASED.value,
                            "service_status": ServiceRequestStatus.SERVICE_STATUS_FAILED.value,
                            "upstream_status": UpstreamStatus.UPSTREAM_STATUS_FAILED.value,
                        },
                    )

            return JSONResponse(status_code=200, content={"message": "Webhook acknowledged"})

        data = webhook_data.get("data") or {}
        reference_id = data.get("referenceId")
        json_url = data.get("jsonUrl")

        if not reference_id or not json_url:
            raise HTTPException(status_code=400, detail={"message": "Reference id or json url is required"})

        gst_ref_doc = await database["gst_reference"].find_one({"reference_id":reference_id},{"_id":0,"user_id":1})
        user_id = gst_ref_doc.get("user_id") or {}

        await update_document(
            collection=database["gst_reference"],
            filter={"reference_id": reference_id},
            fields={
                "gst_reference_id_status": "COMPLETED",
                "webhook_status": "RECEIVED",
                "webhook_received_time": datetime.now(timezone.utc),
                "webhook_response_code": webhook_data.get("responseCode"),
                "webhook_response_message": webhook_data.get("responseMessage"),
                "gst_report_url": data,
            },
        )

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.get(json_url, headers={
                    "clientId": os.getenv("CLIENT_ID"),
                    "clientSecret": os.getenv("CLIENT_SECRET"),
                })
                response.raise_for_status()

            except HTTPError as e:
                raise HTTPException(status_code=500, detail={"message": "Internal server error"})

            await update_document(collection=database["gst_reference"], filter={"reference_id": reference_id},
                                  fields={"is_consumed": True, "consumed_at": datetime.now(timezone.utc)})

        service_request = await get_service_request(
            database=database,
            filters={
                "reference_id": reference_id,
                "service_status": ServiceRequestStatus.SERVICE_STATUS_PROCESSING.value,
            },
        )

        if service_request:
            consume_result = await consume_reserved_balance(
                database=database,
                service=AllowedService.GST.value,
                user_id=user_id,
                reference_id=reference_id,
                amount=ServicePrice.GST.value,
            )

            if consume_result.get("success"):
                await update_service_request(
                    database=database,
                    reference_id=reference_id,
                    fields={
                        "wallet_status": WalletStatus.SUCCESS.value,
                        "service_status": ServiceRequestStatus.SERVICE_STATUS_SUCCESS.value,
                        "upstream_status": UpstreamStatus.UPSTREAM_STATUS_SUCCESS.value,
                    },
                )

        report_data = response.json().get("data") or {}

        await database["gst_analyzed_report"].insert_one({
            "user_id": user_id,
            "reference_id": reference_id,
            "report": report_data,
            "created_at": datetime.now(timezone.utc),
        })

        background_task.add_task(send_gst_report_mail_based_on_request,user_id,reference_id,database)

        return JSONResponse(status_code=200, content={"message": "GST report successfully saved"})

    except HTTPException as e:
        logger.error("Error raised at webhook consumer controller", exc_info=True)
        raise e
    except HTTPError as e:
        logger.error("HTTP error in gst_webhook_consumer: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to fetch GST report")
    except Exception:
        logger.exception("Unexpected error in gst_webhook_consumer")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_overview_and_account_details(request:Request)->JSONResponse:
    try:
        #pass reference id from body
        input_data = await request.json()
    except JSONDecodeError as e:
        raise HTTPException(status_code=400, detail={"message": "Invalid json format in body"})

    if not input_data:
        raise HTTPException(status_code=400, detail={"message": "Body cannot be empty"})

    if not input_data.get('gst_reference_id'):
        raise HTTPException(status_code=400, detail={"message": "Gst reference id cannot be empty"})


    gst_report_coll:AsyncIOMotorCollection = request.app.state.mongo_db["gst_analyzed_report"]

    projection = {
        "_id": 0,
        "reference_id": 1,
        "report.Account Details":1,
        "report.Overview":1,
        "report.Snapshot.Averages":1
        }

    doc = await gst_report_coll.find_one(
        {"reference_id": input_data.get('gst_reference_id')},
        projection
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"message": "No data found"}
        )

    overview = []

    for i in range(0,len(doc['report'])):
        if len(doc.get("report")[i])==0:
            continue

        if doc.get("report")[i].get("Snapshot"):
            snapshot = doc["report"][i]["Snapshot"]
            doc["report"][i]["Snapshot"] = [item for item in snapshot if item]

        overview.append(doc.get("report")[i])


    return JSONResponse(
        status_code=200,
        content={
            "message": "overview and averages fetched successfully",
            "data": overview,
        }
    )

async def get_r1xcrm_overview(request:Request)->JSONResponse:
    try:
        return await get_overview_and_account_details(request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})

async def get_top_suppliers_and_customers(request:Request)->JSONResponse:
    try:
        input_data = await request.json()
    except JSONDecodeError as e:
        raise HTTPException(status_code=400, detail={"message": "Invalid json format in body"})

    if not input_data:
        raise HTTPException(status_code=400, detail={"message": "Body cannot be empty"})

    if not input_data.get('gst_reference_id'):
        raise HTTPException(status_code=400, detail={"message": "Gst reference id cannot be empty"})

    projection = {
        "_id": 0,
        "report.Account Details":1,
        "report.Major Suppliers & Customers ":1
    }

    gst_analyzed_coll:AsyncIOMotorCollection = request.app.state.mongo_db["gst_analyzed_report"]

    doc = await gst_analyzed_coll.find_one({"reference_id": input_data.get('gst_reference_id')},projection)

    if not doc:
        raise HTTPException(status_code=404, detail={"message": "No Analyzed Data Found"})

    suppliers_and_customers = []

    for i in range (0,len(doc['report'])):
        if not doc['report'][i]:
            continue
        suppliers_and_customers.append(doc['report'][i])

    return JSONResponse(status_code=200, content={"message":"Top 10 suppliers and customers fetched successfully","data": suppliers_and_customers})

async def get_r1xcrm_top_suppliers_and_customers(request:Request)->JSONResponse:
    try:
        return await get_top_suppliers_and_customers(request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})

async def get_monthly_sales_and_purchase_summary(request: Request) -> JSONResponse:
    try:
        input_data = await request.json()
    except JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid json format in body"}
        )

    if not input_data:
        raise HTTPException(
            status_code=400,
            detail={"message": "Body cannot be empty"}
        )

    if not input_data.get("gst_reference_id"):
        raise HTTPException(
            status_code=400,
            detail={"message": "Gst reference id cannot be empty"}
        )

    projection = {
        "_id": 0,
        "report.Account Details": 1,
        "report.Monthly Sales&Purchase": 1,
    }

    gst_analyzed_coll: AsyncIOMotorCollection = request.app.state.mongo_db[
        "gst_analyzed_report"
    ]

    doc = await gst_analyzed_coll.find_one(
        {"reference_id": input_data.get("gst_reference_id")},
        projection
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"message": "No Analyzed Data Found"}
        )

    monthly_sales_and_purchase_summary = []

    for i in range(0, len(doc["report"])):

        if not doc["report"][i]:
            continue
        monthly_sales_and_purchase_summary.append(
                doc["report"][i]
            )



    return JSONResponse(
        status_code=200,
        content={
            "message": "Monthly sales and purchase summary fetched successfully",
            "data": {
                "monthly_sales_and_purchase_summary": monthly_sales_and_purchase_summary,
            }
        }
    )


async def get_r1xcrm_monthly_sales_purchase_summary(request:Request) -> JSONResponse:
    try:
        return await get_monthly_sales_and_purchase_summary(request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": "Internal server error"})























