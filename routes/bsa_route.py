import io
import json
import os
from copy import copy
from json import JSONDecodeError

import httpx
from fastapi import APIRouter, BackgroundTasks, File, Form, Query, Request, UploadFile
from fastapi.exceptions import HTTPException
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from starlette import status
from starlette.responses import JSONResponse, StreamingResponse

from config.config import (
    AllowedService,
    ServicePrice,
    ServiceRequestStatus,
    UpstreamStatus,
    WalletStatus,
)
from controller.backgroud_task_controller import send_report_mail_based_on_request
from controller.bank_statement_report import (
    get_available_bank_accounts,
    get_crm_bank_statement_report,
    get_report_date_range,
)
from controller.bsa_summary_drcr_monthwise import (
    bsa_summary_of_debit_credit_monthwise,
)
from controller.bsa_uploads import bank_names, pdf_upload_consumer_v2
from controller.bsa_webhook_controller import (
    fetch_and_save_bank_report,
    is_reference_id_mergable,
    merge_reference_ids,
)
from controller.cashflow_controller import (
    build_cashflow_report,
)
from controller.crm_bsa_upload_controller import handle_bsa_upload_crm
from controller.individual_bank_statement_report import (
    individual_eod_by_account,
    individual_loan_transaction_by_account,
    individual_overview_by_account,
)
from controller.overview_month_wise import (
    bank_statement_report_consolidated,
)
from controller.payments_controller.wallet_contoller import consume_reserved_balance
from controller.update_webhook_response import update_webhook_response
from services.service_request_service import get_service_request, update_service_request

ALLOWED_ROLES = ("ADMIN", "ANCHOR", "SUPER_ANCHOR")

bsa_router = APIRouter(prefix="/v1/bsa", tags=["BSA"])


@bsa_router.post("/upload")
async def upload_bsa(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(None),
    data: str = Form(None),  # This will be the JSON string of your data block
):
    # Convert string back to dictionary
    try:
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Input data is required"},
            )

        data_params = json.loads(data)

        if data_params.get("filePassword"):
            password = data_params["filePassword"]

            data_params["filePassword"] = {file.filename: password for file in files}

        response = await pdf_upload_consumer_v2(
            request=request,
            files=files,
            mongodb_connection=request.app.state.mongo_db,
            data_params=data_params,
            background_task=background_tasks,
        )
    except JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON Input"},
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise e
    return response


# @bsa_router.post("/upload_ref_id")
# async def upload_to_bsa(request:Request, background_tasks: BackgroundTasks,cust_id:Optional[str]=None):
#     try:
#           input_data = await request.json()
#
#           return await pdf_upload_consumer(request=request,input_body=input_data,mongodb_connection=request.app.state.mongo_db,background_task=background_tasks,cust_id=cust_id)
#
#     except JSONDecodeError:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail={"message":"Invalid JSON Input"}
#         )
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise e


@bsa_router.post("/webhook-response-handler")
async def webhook_response(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        db = request.app.state.mongo_db
        mongodb_connection = (
            request.app.state.mongo_db
        )  # or however your raw client is accessed
        # Step 1: Update webhook response in DB
        success = await update_webhook_response(payload, db)
        if not success["success"]:
            raise HTTPException(status_code=400, detail=success["error"])
        json_url = payload.get("data", {}).get("jsonUrl")
        reference_id = payload.get("data", {}).get("referenceId")
        user_id = success["user_id"]
        if not json_url:
            print("ScoreMe API failure — no jsonUrl in payload")
            return {"status": "failure", "message": "ScoreMe API failure"}

        if not reference_id:
            print("No referenceId in payload")
            raise HTTPException(
                status_code=400, detail="Missing referenceId in webhook payload"
            )

        # Step 2: Guard — if this reference_id is itself a merge result, store directly
        # This prevents the infinite merge loop
        ref_doc = await mongodb_connection["bsa_reference"].find_one(
            {"reference_id": reference_id}
        )
        if ref_doc and ref_doc.get("is_merge_request"):
            print(f"reference_id {reference_id} is a merge result — storing directly")
            background_tasks.add_task(
                fetch_and_save_bank_report, db, user_id, reference_id, json_url, ref_doc
            )
            background_tasks.add_task(
                send_report_mail_based_on_request,
                user_id,
                reference_id,
                request.app.state.mongo_db,
                request.app.state.postgres_conn,
            )
            # update the merge status once the merge request is successfully merged
            await mongodb_connection["bsa_reference"].update_one(
                {"reference_id": reference_id},
                {"$set": {"merge_request_status": "COMPLETED"}},
            )
            return {
                "status": "success",
                "message": "Merge result received — report ingestion started",
            }

        merge_status, existing_doc = await is_reference_id_mergable(
            user_id=user_id, json_url=json_url, mongodb_connection=mongodb_connection
        )

        if merge_status == "MERGABLE":
            existing_reference_id = existing_doc["last_merged_reference_id"]
            print(
                f"Merging [{existing_reference_id}] + [{reference_id}] for user {user_id}"
            )

            # update the service request if any service request found for this reference_id
            service_request = await get_service_request(
                database=request.app.state.mongo_db,
                filters={"reference_id": reference_id},
            )

            if service_request:
                # consume the reserved amount for the user
                amount_consumption_result = await consume_reserved_balance(
                    database=request.app.state.mongo_db,
                    service=AllowedService.BSA.value,
                    user_id=user_id,
                    reference_id=reference_id,
                    amount=ServicePrice.BSA.value,
                )
                print("Reserved prince consumption", amount_consumption_result)
                if amount_consumption_result.get("success"):
                    # if reserved price consumption is successfull then update the service request status
                    service_update = await update_service_request(
                        database=request.app.state.mongo_db,
                        reference_id=reference_id,
                        fields={
                            "wallet_status": WalletStatus.SUCCESS.value,
                            "service_status": ServiceRequestStatus.SERVICE_STATUS_SUCCESS.value,
                            "upstream_status": UpstreamStatus.UPSTREAM_STATUS_SUCCESS.value,
                        },
                    )
                    print("Service update result", service_update)

            background_tasks.add_task(
                merge_reference_ids,
                user_id,
                [existing_reference_id, reference_id],
                mongodb_connection,
            )
            return {"status": "success", "message": "Merge initiated"}

        elif merge_status == "NO_EXISTING_DOC":
            # First report for this user — store directly
            print(f"First report for user {user_id} — storing directly")
            # update the service request if any service request found for this reference_id
            service_request = await get_service_request(
                database=request.app.state.mongo_db,
                filters={"reference_id": reference_id},
            )

            if service_request:
                # consume the reserved amount for the user
                amount_consumption_result = await consume_reserved_balance(
                    database=request.app.state.mongo_db,
                    service=AllowedService.BSA.value,
                    user_id=user_id,
                    reference_id=reference_id,
                    amount=ServicePrice.BSA.value,
                )
                print("Reserved prince consumption", amount_consumption_result)
                if amount_consumption_result.get("success"):
                    # if reserved price consumption is successfull then update the service request status
                    service_update = await update_service_request(
                        database=request.app.state.mongo_db,
                        reference_id=reference_id,
                        fields={
                            "wallet_status": WalletStatus.SUCCESS.value,
                            "service_status": ServiceRequestStatus.SERVICE_STATUS_SUCCESS.value,
                            "upstream_status": UpstreamStatus.UPSTREAM_STATUS_SUCCESS.value,
                        },
                    )
                    print("Service update result", service_update)
            background_tasks.add_task(
                fetch_and_save_bank_report, db, user_id, reference_id, json_url, ref_doc
            )
            # background_tasks.add_task(
            #     send_report_mail_based_on_request, user_id, reference_id,
            #     request.app.state.mongo_db, request.app.state.postgres_conn,
            # )
            return {"status": "success", "message": "Report ingestion started"}

        else:  # ERROR
            print(f"ERROR: Could not determine merge status for user {user_id}")
            raise HTTPException(
                status_code=500, detail="Could not validate report date range"
            )
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail={"message": "Invalid Json Body"})
    except Exception as e:
        print("Error raised at webhook reciever route", e)
        raise HTTPException(
            status_code=400, detail={"message": "Internal server error"}
        )


@bsa_router.post("/month-wise-overview")
async def bsa_report(request: Request):
    db = request.app.state.mongo_db

    success_data = await bank_statement_report_consolidated(db, request)
    if success_data is None:
        raise HTTPException(
            status_code=404, detail="Bank statement not found for this user"
        )

    return {"status": "success", "data": success_data}


@bsa_router.post("/r1xcrm-month-wise-overview/{acc_id}")
async def r1xcrm_bsa_report(
    request: Request,
    acc_id: int,
):
    db = request.app.state.mongo_db
    user_collection = db["users"]

    user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user["_id"])

    request.state.user_id = user_id

    success_data = await bank_statement_report_consolidated(db, request)
    if success_data is None:
        raise HTTPException(
            status_code=404, detail="Bank statement not found for this user"
        )

    return {"status": "success", "data": success_data}


@bsa_router.post("/summary-of-debit-and-credit_monthwise")
async def bsa_summary_of_debit_and_credit(request: Request):

    db = request.app.state.mongo_db
    success_data = await bsa_summary_of_debit_credit_monthwise(db, request)
    if success_data is None:
        raise HTTPException(
            status_code=404, detail="Bank statement not found for this user"
        )
    return {
        "status": "success",
        "message": "Summary of DEBIT and CREDIT monthwise",
        "data": success_data,
    }


@bsa_router.post("/r1xcrm-summary-of-debit-and-credit_monthwise/{acc_id}")
async def r1xcrm_summary_of_debit_and_credit_monthwise(
    request: Request,
    acc_id: int,
):
    try:
        db = request.app.state.mongo_db

        user_collection = db["users"]

        user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user["_id"])

        request.state.user_id = user_id

        return await bsa_summary_of_debit_credit_monthwise(
            request=request, db=request.app.state.mongo_db
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error please contact the admin for support."
            },
        )


@bsa_router.post("/crm/upload")
async def upload_bsa_crm(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(None),
    data: str = Form(None),
):
    try:
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Input data is required"},
            )

        data_params = json.loads(data)

        # account_id is the CRM identity bridge — mandatory for this route
        account_id = data_params.pop("account_id", None)
        crm_user_id = data_params.pop("crm_user_id", None)

        if (
            not account_id
            or str(account_id).strip() == ""
            or not crm_user_id
            or str(crm_user_id).strip() == ""
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "account_id and crm_user_id is required for CRM uploads"
                },
            )

        response = await handle_bsa_upload_crm(
            account_id=account_id,
            mongodb_connection=request.app.state.mongo_db,
            pg_db=request.app.state.postgres_conn,
            files=files,
            data_params=data_params,
            BackgroundTask=background_tasks,
            crm_user_id=crm_user_id,
        )

    except JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON Input"},
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise e

    return response


@bsa_router.get("/crm-bsa-statement-report/{acc_id}")
async def crm_bsa_statement_report(request: Request, acc_id: str):
    try:
        acc_id = acc_id.strip()
        return await get_crm_bank_statement_report(
            db=request.app.state.mongo_db, acc_id=int(acc_id)
        )
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error please contact the admin for support."
            },
        )


@bsa_router.post("/cashflow")
async def cashflow_report(
    request: Request,
):
    db = request.app.state.mongo_db

    result = await build_cashflow_report(db, request)

    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result)

    return result


@bsa_router.post("/r1xcrm-cashflow/{acc_id}")
async def r1x_cashflow_report(
    request: Request,
    acc_id: int,
):
    db = request.app.state.mongo_db
    user_collection = db["users"]

    user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user["_id"])

    request.state.user_id = user_id

    result = await build_cashflow_report(db, request)

    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result)

    return result


@bsa_router.post("/individual/overview")
async def individual_overview_report(
    request: Request,
):
    return await individual_overview_by_account(
        db=request.app.state.mongo_db, request=request
    )


@bsa_router.post("/individual/r1x-overview/{acc_id}")
async def r1x_individual_overview_report(
    request: Request,
    acc_id: int,
):
    try:
        db = request.app.state.mongo_db

        user_collection = db["users"]

        user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user["_id"])

        request.state.user_id = user_id

        return await individual_overview_by_account(
            db=request.app.state.mongo_db, request=request
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error please contact the admin for support."
            },
        )


@bsa_router.post("/individual/eod-analysis")
async def individual_eod_analysis_report(
    request: Request,
):
    return await individual_eod_by_account(
        db=request.app.state.mongo_db, request=request
    )


@bsa_router.post("/individual/r1x-eod-analysis/{acc_id}")
async def r1x_individual_eod_analysis_report(
    request: Request,
    acc_id: int,
):
    try:
        db = request.app.state.mongo_db

        user_collection = db["users"]

        user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user["_id"])

        request.state.user_id = user_id

        return await individual_eod_by_account(
            db=request.app.state.mongo_db, request=request
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error please contact the admin for support."
            },
        )


@bsa_router.post("/individual/loan-transactions")
async def individual_loan_transactions_report(
    request: Request,
):
    return await individual_loan_transaction_by_account(
        request=request, db=request.app.state.mongo_db
    )


@bsa_router.post("/individual/r1x-loan-transactions/{acc_id}")
async def r1x_individual_loan_transactions_report(
    request: Request,
    acc_id: int,
):
    try:
        db = request.app.state.mongo_db

        user_collection = db["users"]

        user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user["_id"])

        request.state.user_id = user_id

        return await individual_loan_transaction_by_account(
            request=request, db=request.app.state.mongo_db
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error please contact the admin for support."
            },
        )


@bsa_router.get("/get-bank-names")
async def bsa_get_bank_names():
    try:
        return await bank_names()
    except HTTPException as e:
        raise e
    except Exception as e:
        print("Error happened at get bank name route", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error please contact the admin for support."
            },
        )


@bsa_router.post("/report-date-range")
async def report_date_range(request: Request):
    try:
        return await get_report_date_range(
            request=request, db=request.app.state.mongo_db
        )
    except HTTPException as e:
        raise e


# expose bank statement data to r1xcrm


@bsa_router.post("/r1xcrm-report-date-range/{acc_id}")
async def r1xcrm_report_date_range(request: Request, acc_id: int):
    try:
        db = request.app.state.mongo_db

        user_collection = db["users"]

        user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user["_id"])

        request.state.user_id = user_id

        return await get_report_date_range(
            request=request, db=request.app.state.mongo_db
        )
    except HTTPException as e:
        raise e


@bsa_router.get("/bank-accounts")
async def bank_report(request: Request, cust_id: str | None = Query(None)):
    return await get_available_bank_accounts(request, cust_id)


@bsa_router.get("/r1x-bank-accounts/{acc_id}")
async def r1x_bank_report(request: Request, acc_id: int):
    try:
        db = request.app.state.mongo_db

        user_collection = db["users"]

        user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user["_id"])
        request.state.user_id = user_id

        return await get_available_bank_accounts(request=request, cust_id=user_id)
    except HTTPException as e:
        raise e


@bsa_router.post("/account-details")
async def account_details(request: Request):
    try:
        db = request.app.state.mongo_db

        input_body = await request.json()
        account_number = input_body.get("account_number")

        if not account_number:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Account number is required"},
            )

        doc = await db.bsa_merged_bankstatements.find_one(
            {"account_details.Account Number": account_number},
            {"_id": 0, "account_details": 1},
        )

        if not doc:
            raise HTTPException(
                status_code=404, detail={"message": "Account not found for this user"}
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Account details fetched successfully", "data": doc},
        )
    except JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": "Invalid JSON"}
        )

    except Exception:
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error"}
        )


@bsa_router.post("/r1x-account-details/{acc_id}")
async def r1x_account_details(request: Request, acc_id: int):
    try:
        db = request.app.state.mongo_db

        user_collection = db["users"]

        user = await user_collection.find_one({"account_id": acc_id}, {"_id": 1})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user["_id"])
        request.state.user_id = user_id

        return await account_details(request=request)
    except HTTPException as e:
        raise e


@bsa_router.post("/export-report")
async def export_bsa_report(request: Request):
    try:
        db = request.app.state.mongo_db
        input_body = await request.json()

        if not input_body.get("account_number"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "account number is required"},
            )

        url_doc: str = await db.bsa_merged_bankstatements.find_one(
            {"account_details.Account Number": input_body.get("account_number")},
            {"_id": 0, "source_url": 1},
        )

        # find and replace json with xlsx

        url = url_doc.get("source_url")

        excel_url = url.replace("json", "xlsx")

        # make  a api call to the upstream service to get the excel file as bytes

        async with httpx.AsyncClient() as client:
            excel_response = await client.get(
                excel_url,
                headers={
                    "clientId": os.getenv("CLIENT_ID"),
                    "clientSecret": os.getenv("CLIENT_SECRET"),
                },
            )

        if excel_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"message": "Bad Gateway try again later"},
            )

        excel_bytes = excel_response.content

        wb = load_workbook(io.BytesIO(excel_bytes))

        PIXELS_TO_EMU = 9525

        for ws in wb.worksheets:
            if not ws._images:
                continue

            old_image = ws._images[0]

            # Preserve the original position only
            anchor = copy(old_image.anchor)

            # Load your logo at its natural/original dimensions
            new_image = XLImage("assets/crisp_logo.png")

            # Don't set width/height again
            new_image.anchor = copy(old_image.anchor)

            ws._images.clear()
            ws.add_image(new_image)

        output = io.BytesIO()

        wb.save(output)

        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="Bsa_analysis_report.xlsx"'
            },
        )

    except JSONDecodeError as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": "Invalid JSON"}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error"}
        )
