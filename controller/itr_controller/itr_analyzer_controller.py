import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from pymongo import UpdateOne
from starlette import status
from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.requests import Request
import logging
from starlette.responses import JSONResponse
import config.config as url
from controller.backgroud_task_controller import send_itr_report_mail_based_on_request
from custom_exceptions.scoreme_exceptions import raise_itr_post_link_exception
from services.scoreme_service import update_document
from utils.auth_utility import is_email_valid
import httpx
logging.basicConfig(level=logging.INFO)

ALLOWED_ROLES = ('ANCHOR','SUPER_ANCHOR','ADMIN')

async def initiate_itr_process (request: Request)->JSONResponse:
    try:
        try:
            input_data = await request.json()
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Invalid json body","responseCode":None,"data":None})
        if not input_data :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Body should not be empty","responseCode":None,"data":None})

        if not input_data.get("email_id") :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Email_id is required","responseCode":None,"data":None})
        user_id = request.state.user_id

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

            if response.status_code == 406:
                raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,detail={"message": "Invalid input data", "responseCode": None, "data": None})

            scoreme_response_json = response.json() #it never breaks because of external server standard response across all the requests

            print("This is the scoreme response for the itr link",scoreme_response_json)

            raise_itr_post_link_exception(scoreme_response_json)

        if scoreme_response_json["responseCode"] == "SRS016":
            #create itr_reference_doc and store it on the collection
            itr_reference_doc = {
                "user_id": user_id,
                "reference_id": scoreme_response_json.get("data").get("referenceId"),
                "input_data": input_data,
                "itr_reference_id_status": "INPROGRESS",
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

            #after saving the reference document to the collection construct the itr_link state management document for managing the lifecycle of the link


            itr_link = {  #link lifecycle management for internal system
                "reference_id": scoreme_response_json.get("data").get("referenceId"),
                "user_id": user_id,
                "link_status":"PENDING",
                "link_generated_at": request_initiated_at,
                "link_expiry_time":scoreme_response_json.get("data").get("linkExpiryTime"),
                "link_response_code": "ENC220",
                "link_response_message":"The credential have not yet been submitted in the link. We are still awaiting the same",
                "link_validated_at": None,
                "last_updated_at": None,
            }

            try:
                client = database.client
                async with await client.start_session() as session:

                    async with session.start_transaction():
                        await database["itr_reference"].insert_one(
                            itr_reference_doc,
                            session=session
                        )

                        await database["itr_link_management"].insert_one(
                            itr_link,
                            session=session
                        )

            except Exception as e:
                logging.error(
                    "Transaction failed while storing ITR data",
                    exc_info=True
                )

                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": "Failed to store ITR data",
                        "responseCode": None,
                        "data": None
                    }
                )
            return  JSONResponse(status_code=status.HTTP_200_OK,content={"message":"Email triggered successfully","responseCode":"SYS_PENDING","data":{"itr_reference_id":scoreme_response_json.get("data").get("referenceId")}})
        else:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal server error","responseCode":None,"data":None})

    except HTTPException as e:
        logging.error(msg=str(e), exc_info=True)
        raise e

    except Exception as e:
        logging.error(msg=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal server error","responseCode":None,"data":None})



async def get_itr_link_status_based_on_user(request:Request,cust_id:Optional[str]) -> JSONResponse:
    try:
        requester_role = request.state.role
        user_id = request.state.user_id
        database = request.app.state.mongo_db
        itr_repo = database["itr_link_management"]
        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=400,
                    detail="Since the role is accesssing on behalf of user, hence cust_id is required"
                )
            user_id = cust_id

        existing_links: list = await itr_repo.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("link_generated_at", -1).to_list(None)

        if existing_links:
            # if any link found for this user loop through the  array of link_state doc
            #fetch the latest link that are being generated by the system
            latest_link = existing_links[0]
            print("This is the latest link",latest_link)
            link_status_data = {
                "itr_reference_id":latest_link.get("reference_id",None),
                "itr_link_response_code":latest_link.get("link_response_code"),
                "link_response_message":latest_link.get("link_response_message"),
            }
            return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"status fetched successfully","data":link_status_data})
        else:
            return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"No report found proceed","data": {
        "itr_reference_id": None,
        "itr_link_response_code": None,
        "link_response_message": None,
    }})
    except HTTPException as e:
        logging.error(msg=str(e), exc_info=True)
        print(f"Conflict might happen if we allow this user: {str(e)}")
        raise e
    except Exception as e:
        logging.error(msg=str(e),exc_info=True)
        print(f"Error while checking ITR report existence: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal Server Error","data":None})



async def get_link_status_based_on_ref_id(request:Request) -> JSONResponse:
    try:
        try:
            input_data = await request.json()
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"message": "Invalid json body", "responseCode": None, "data": None})
        if not input_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"message": "Body should not be empty", "responseCode": None, "data": None})

        if not input_data.get("itr_reference_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"message": "itr reference id  is required", "responseCode": None, "data": None})

        database :AsyncIOMotorDatabase = request.app.state.mongo_db

        itr_link_status = await database["itr_link_management"].find_one({"reference_id":input_data.get("itr_reference_id")}, {"_id": 0})

        if not itr_link_status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"message": "Reference id is invalid", "responseCode": None, "data": None})

        response_code = itr_link_status.get("link_response_code")
        link_status = itr_link_status.get("link_status")
        link_message = itr_link_status.get("link_response_message")

        return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"status fetched successfully","data":{"itr_link_status":link_status,"itr_link_message":link_message,"itr_link_response_code":response_code}})

    except HTTPException as e:
        logging.error(msg=str(e), exc_info=True)
        raise e

    except Exception as e:
        logging.error(msg=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Internal server error","responseCode":None,"data":None})



async def poll_email_link_status(database_conn) : #this function will run every 5 sec and poll the external server for updates
    print("ITR STATUS POLLING SERVICE STARTED")
    while True:
        try:
            print("POLLING ITR STATUS")
            database : AsyncIOMotorDatabase = database_conn

            itr_link_management = database["itr_link_management"]

            itr_pending_links = await itr_link_management.find({"link_status":{"$in":["PENDING","AWAITING_CREDENTIAL_SUBMISSION","PROCESSING"]}}).to_list(length=None)

            bulk_update = [] #holds all the doc that are need to be updated

            if itr_pending_links:
                async with httpx.AsyncClient() as client:
                    for link in itr_pending_links:

                        reference_id = link.get("reference_id")

                        if not reference_id:
                            continue

                        # check if the link is expired internally or not using the generated at date
                        generated_at = link.get("link_generated_at").replace(tzinfo=timezone.utc)

                        if datetime.now(timezone.utc) - generated_at > timedelta(days=1):
                            bulk_update.append(UpdateOne(filter={"_id":link["_id"]},update={"$set":{"link_status": "INTERNAL_LINK_EXPIRED",
                                                                                     "link_response_code": "SYS_LINK_410",
                                                                                     "link_response_message": "The internal processing link is no longer active.",
                                                                    "last_updated_at":datetime.now(timezone.utc)}}))
                            print("REMOVING OLD LINKS FROM THE PIPELINE")
                            continue
                        try:
                            response = await client.get(
                                url=url.SCOREME_ITR_GET_REFERENCE_STATUS,  #define your external endpoint
                                params={"referenceId": reference_id},
                                headers={
                                    "clientId": os.getenv("CLIENT_ID"),  # Matches your .env
                                    "clientSecret": os.getenv("CLIENT_SECRET")  # Matches your .env
                                }
                                ,
                                timeout=10.0,
                            )
                            response_json: dict = response.json()
                            print(response_json)

                        except (httpx.RequestError, httpx.TimeoutException) as exc:
                            # Network/timeout error — skip this link, retry next poll
                            continue

                        status_update_dict = construct_itr_status_update(response_json)
                        bulk_update.append(
                            UpdateOne(
                                {"_id": link["_id"]},
                                {"$set": status_update_dict}
                            )
                        )
            else:
                print("No PENDING REFERENCE LINKS FOUND")

            if bulk_update:
                await itr_link_management.bulk_write(bulk_update)

            await asyncio.sleep(45)


        except httpx.HTTPError as e:
            logging.error(msg=str(e), exc_info=True)

        except Exception as e:
            logging.error(msg=str(e), exc_info=True)


def construct_itr_status_update(response_json: dict):


    response_code = response_json.get("responseCode")
    response_message = response_json.get("responseMessage")

    current_time = datetime.now(timezone.utc)

    response_code_mapping = {

        # SUCCESS
        "SRC001": "SUCCESS",

        # INVALID REQUEST / CLIENT ERRORS
        "EBF017": "INVALID_REQUEST",  # Blank Input
        "EIP018": "INVALID_REQUEST",  # Incorrect Input
        "ENR029": "INVALID_REFERENCE_ID",  # No Record Found

        # USER ACTION PENDING
        "ENC220": "AWAITING_CREDENTIAL_SUBMISSION",

        # TIMEOUT / EXPIRED
        "ECR214": "TIMEOUT",

        "RNP020":"PROCESSING"
    }

    link_status = response_code_mapping.get(response_code,"UNKNOWN_STATUS")

    update_doc = {
        "link_status": link_status,
        "link_response_code": response_code,
        "link_response_message": response_message,
        "last_updated_at": current_time,
    }

    if response_code == "SRC001":
        update_doc["link_validated_at"] = current_time

    return update_doc


async def itr_webhook_consumer(webhook_data: dict, database: AsyncIOMotorDatabase,background_task:BackgroundTasks) -> JSONResponse:
    try:
        if webhook_data.get("responseCode") != "SRC001":
            data = webhook_data.get("data") or {}
            reference_id = data.get("referenceId")
            await update_document(
                collection=database["itr_reference"],
                filter={"reference_id": reference_id},
                fields={
                    "itr_reference_id_status": "FAILED",
                    "webhook_status": "RECEIVED",
                    "webhook_received_time": datetime.now(timezone.utc),
                    "webhook_response_code": webhook_data.get("responseCode"),
                    "webhook_response_message": webhook_data.get("responseMessage"),
                    "itr_report_url": data.get("reportUrl"),
                },
            )
            return JSONResponse(status_code=200, content={"message": "Webhook acknowledged"})

        data = webhook_data.get("data") or {}
        reference_id = data.get("referenceId")
        json_url = data.get("jsonUrl")

        if not reference_id or not json_url:
            raise HTTPException(status_code=400, detail={"message": "Reference id or json url is required"})

        itr_ref_doc = await database["itr_reference"].find_one(
            {"reference_id": reference_id},
            {"_id": 0, "user_id": 1}
        )
        user_id = itr_ref_doc.get("user_id") or {}

        await update_document(
            collection=database["itr_reference"],
            filter={"reference_id": reference_id},
            fields={
                "itr_reference_id_status": "COMPLETED",
                "webhook_status": "RECEIVED",
                "webhook_received_time": datetime.now(timezone.utc),
                "webhook_response_code": webhook_data.get("responseCode"),
                "webhook_response_message": webhook_data.get("responseMessage"),
                "itr_report_url": data
            },
        )

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.get(json_url, headers={
                    "clientId": os.getenv("CLIENT_ID"),
                    "clientSecret": os.getenv("CLIENT_SECRET"),
                })
                response.raise_for_status()

            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail={"message": "Internal server error"})

        await update_document(collection=database["itr_reference"],filter={"reference_id": reference_id},fields={"is_consumed":True,"consumed_at":datetime.now(timezone.utc)})

        report_data = response.json().get("ITR") or {}


        await database["itr_analyzed_report"].insert_one({
            "user_id": user_id,
            "reference_id": reference_id,
            "report": report_data,
            "created_at": datetime.now(timezone.utc),
        })

        background_task.add_task(send_itr_report_mail_based_on_request,user_id,reference_id,database)

        return JSONResponse(status_code=200, content={"message": "ITR report successfully saved"})

    except HTTPException as e:
        logging.error("Error raised at itr webhook consumer controller", exc_info=True)
        raise e
    except httpx.HTTPError as e:
        logging.error("HTTP error in itr_webhook_consumer: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to fetch ITR report")
    except Exception:
        logging.exception("Unexpected error in itr_webhook_consumer")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_tax_calculation(request: Request,cust_id:Optional[str]=None) -> JSONResponse:
    try:
        user_id = request.state.user_id
        itr_repo = request.app.state.mongo_db["itr_analyzed_report"]
        requester_role = request.state.role

        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=400,
                    detail="Since the role is accesssing on behalf of user, hence cust_id is required"
                )
            user_id = cust_id

        document = await itr_repo.find_one(
            {"user_id": user_id},
            {
                "_id": 0,
                "report.Tax Calculation": 1,
                "report.General Information.General Information": 1,
                "report.General Information.Gross Receipt Reported for GST": 1
            }
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message":"Tax calculation report not found","data":None}
            )

        general_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("General Information", [])
        )

        gst_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("Gross Receipt Reported for GST", [])
        )

        latest_general_info = general_info[-1] if general_info else {}
        latest_gst_info = gst_info[-1] if gst_info else {}

        response_data = {
            "customer_profile": {
                "company_name": latest_general_info.get("Name"),
                "gstin": latest_gst_info.get("GSTIN"),
                "phone_number": latest_general_info.get("Contact Number"),
                "pan": latest_general_info.get("PAN")
            },
            "tax_calculation": (
                document.get("report", {})
                .get("Tax Calculation", {})
            ),
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Tax calculation fetched successfully",
                "data": response_data
            }
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def get_r1xcrm_tax_calculation(request: Request,acc_id:int)->JSONResponse:
    db = request.app.state.mongo_db
    if not acc_id:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account ID is required"
        )
    user = await db["users"].find_one({"account_id":acc_id})
    if not user:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return await get_tax_calculation(request,str(user["_id"]))

async def get_balance_sheet(request: Request,cust_id:Optional[str]=None) -> JSONResponse:
    try:

        itr_repo = request.app.state.mongo_db["itr_analyzed_report"]
        user_id=request.state.user_id
        requester_role = request.state.role
    
        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=400,
                    detail="Since the role is accesssing on behalf of user, hence cust_id is required"
                )
            user_id = cust_id

        document = await itr_repo.find_one(
            {"user_id": user_id},
            {
                "_id": 0,
                "report.Balance Sheet": 1,
                "report.General Information.General Information": 1,
                "report.General Information.Gross Receipt Reported for GST": 1
            }
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Balance sheet report not found"
            )

        general_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("General Information", [])
        )

        gst_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("Gross Receipt Reported for GST", [])
        )

        latest_general_info = general_info[-1] if general_info else {}
        latest_gst_info = gst_info[-1] if gst_info else {}

        response_data = {
            "customer_profile": {
                "company_name": latest_general_info.get("Name"),
                "gstin": latest_gst_info.get("GSTIN"),
                "phone_number": latest_general_info.get("Contact Number"),
                "pan": latest_general_info.get("PAN")
            },
            "balance_sheet": document.get("report", {}).get("Balance Sheet", {})
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Balance sheet fetched successfully",
                "data": response_data
            }
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def get_r1xcrm_balance_sheet(request:Request,acc_id:int)->JSONResponse:
    db = request.app.state.mongo_db
    if not acc_id:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account ID is required"
        )
    user = await db["users"].find_one({"account_id":acc_id})
    if not user:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return await get_balance_sheet(request,str(user["_id"]))

async def get_profit_and_loss_statement(request: Request,cust_id:str) -> JSONResponse:
    try:
        user_id = request.state.user_id
        itr_repo = request.app.state.mongo_db["itr_analyzed_report"]
        requester_role = request.state.role
        
        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=400,
                    detail="Since the role is accesssing on behalf of user, hence cust_id is required"
                )
            user_id = cust_id
        document = await itr_repo.find_one(
            {"user_id": user_id},
            {
                "_id": 0,
                "report.Profit And Loss Statement": 1,
                "report.General Information.General Information": 1,
                "report.General Information.Gross Receipt Reported for GST": 1
            }
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profit and Loss statement not found"
            )

        general_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("General Information", [])
        )

        gst_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("Gross Receipt Reported for GST", [])
        )

        latest_general_info = general_info[-1] if general_info else {}
        latest_gst_info = gst_info[-1] if gst_info else {}

        response_data = {
            "customer_profile": {
                "company_name": latest_general_info.get("Name"),
                "gstin": latest_gst_info.get("GSTIN"),
                "phone_number": latest_general_info.get("Contact Number"),
                "pan": latest_general_info.get("PAN")
            },
            "profit_and_loss_statement": (
                document.get("report", {})
                .get("Profit And Loss Statement", {})
            )
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Profit and Loss statement fetched successfully",
                "data": response_data
            }
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def get_r1xcrm_profit_and_loss_statement(request:Request,acc_id:int)->JSONResponse:
    db = request.app.state.mongo_db
    if not acc_id:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account ID is required"
        )
    user = await db["users"].find_one({"account_id":acc_id})
    if not user:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return await get_profit_and_loss_statement(request,str(user["_id"]))

async def get_ratio_analysis(request: Request,cust_id:str) -> JSONResponse:
    try:

        itr_repo = request.app.state.mongo_db["itr_analyzed_report"]
        user_id = request.state.user_id

        requester_role = request.state.role

        if requester_role in ALLOWED_ROLES:
            if not cust_id:
                raise HTTPException(
                    status_code=400,
                    detail="Since the role is accesssing on behalf of user, hence cust_id is required"
                )
            user_id = cust_id

        document = await itr_repo.find_one(
            {"user_id": user_id},
            {
                "_id": 0,
                "report.Ratio Analysis": 1,
                "report.General Information.General Information": 1,
                "report.General Information.Gross Receipt Reported for GST": 1
            }
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ratio analysis report not found"
            )

        general_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("General Information", [])
        )

        gst_info = (
            document.get("report", {})
            .get("General Information", {})
            .get("Gross Receipt Reported for GST", [])
        )

        latest_general_info = general_info[-1] if general_info else {}
        latest_gst_info = gst_info[-1] if gst_info else {}

        response_data = {
            "customer_profile": {
                "company_name": latest_general_info.get("Name"),
                "gstin": latest_gst_info.get("GSTIN"),
                "phone_number": latest_general_info.get("Contact Number"),
                "pan": latest_general_info.get("PAN")
            },
            "ratio_analysis": (
                document.get("report", {})
                .get("Ratio Analysis", {})
            )
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Ratio analysis fetched successfully",
                "data": response_data
            }
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def get_r1xcrm_ratio_analysis(request:Request,acc_id:int)->JSONResponse:
    db = request.app.state.mongo_db
    if not acc_id:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account ID is required"
        )
    user = await db["users"].find_one({"account_id":acc_id})
    if not user:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return await get_ratio_analysis(request,str(user["_id"]))
