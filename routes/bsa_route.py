from fastapi.exceptions import HTTPException
from fastapi  import BackgroundTasks, Query
from json import JSONDecodeError
from starlette import status
from fastapi import APIRouter, UploadFile, File, Request, Form
from controller.bsa_uploads import handle_bsa_upload,bank_names
from controller.crm_bsa_upload_controller import handle_bsa_upload_crm
from controller.update_webhook_response import update_webhook_response
from controller.bank_statement_report import bank_statement_report,get_crm_bank_statement_report
from typing import List, Optional
from controller.bsa_webhook_controller import fetch_and_save_bank_report, is_reference_id_mergable, merge_reference_ids
from controller.backgroud_task_controller import send_report_mail_based_on_request
from controller.bsa_summary_drcr_monthwise import bsa_summary_of_debit_credit_monthwise
import json
from datetime import datetime

bsa_router = APIRouter(prefix="/v1/bsa", tags=["BSA"])
@bsa_router.post("/upload")
async def upload_bsa(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(None),
    data: str = Form(None)  # This will be the JSON string of your data block
):
    # Convert string back to dictionary
    try:
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Input data is required"})

        data_params = json.loads(data)

        # Pull the account number from the metadata we just parsed
        response = await handle_bsa_upload(request.state.user_id,request.app.state.mongo_db,files,data_params,background_tasks)
    except JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message":"Invalid JSON Input"}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise e
    return response



@bsa_router.post("/webhook-response-handler")
async def webhook_response(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    db = request.app.state.mongo_db
    mongodb_connection = request.app.state.mongo_db  # or however your raw client is accessed
    user_id = request.state.user_id
    # Step 1: Update webhook response in DB
    success = await update_webhook_response(user_id, payload, db)
    if not success["success"]:
        raise HTTPException(status_code=400, detail=success["error"])
    json_url = payload.get("data", {}).get("jsonUrl")
    reference_id = payload.get("data", {}).get("referenceId")

    if not json_url:
        print("ScoreMe API failure — no jsonUrl in payload")
        return {"status": "failure", "message": "ScoreMe API failure"}

    if not reference_id:
        print("No referenceId in payload")
        raise HTTPException(status_code=400, detail="Missing referenceId in webhook payload")

    # Step 2: Guard — if this reference_id is itself a merge result, store directly
    # This prevents the infinite merge loop
    ref_doc = await mongodb_connection["bsa_reference"].find_one({"reference_id": reference_id})
    if ref_doc and ref_doc.get("is_merge_request"):
        print(f"reference_id {reference_id} is a merge result — storing directly")
        background_tasks.add_task(fetch_and_save_bank_report, db, user_id, reference_id, json_url)
        background_tasks.add_task(
            send_report_mail_based_on_request,
            user_id,
            reference_id,
            request.app.state.mongo_db,
            request.app.state.postgres_conn,
        )
        return {"status": "success", "message": "Merge result received — report ingestion started"}

    merge_status = await is_reference_id_mergable(
        user_id=user_id,
        reference_id=reference_id,
        json_url=json_url,
        mongodb_connection=mongodb_connection
    )

    if merge_status == "MERGABLE":
        existing_doc = await mongodb_connection["bsa_merged_bankstatements"].find_one(
            {"user_id": user_id, "status": "ACTIVE"},
            sort=[("created_at", -1)]
        )

        if not existing_doc:
            print(f"WARN: No existing doc found for user {user_id} — storing directly")
            background_tasks.add_task(fetch_and_save_bank_report, db, user_id, reference_id, json_url)
            background_tasks.add_task(
                send_report_mail_based_on_request, user_id, reference_id,
                request.app.state.mongo_db, request.app.state.postgres_conn,
            )
            return {"status": "success", "message": "Fallback — report ingestion started"}

        existing_reference_id = existing_doc["last_merged_reference_id"]
        print(f"Merging [{existing_reference_id}] + [{reference_id}] for user {user_id}")
        background_tasks.add_task(merge_reference_ids, user_id, [existing_reference_id, reference_id],
                                  mongodb_connection)
        return {"status": "success", "message": "Merge initiated"}

    elif merge_status == "NO_EXISTING_DOC":
        # First report for this user — store directly
        print(f"First report for user {user_id} — storing directly")
        background_tasks.add_task(fetch_and_save_bank_report, db, user_id, reference_id, json_url)
        background_tasks.add_task(
            send_report_mail_based_on_request, user_id, reference_id,
            request.app.state.mongo_db, request.app.state.postgres_conn,
        )
        return {"status": "success", "message": "Report ingestion started"}

    elif merge_status == "OVERLAP":
        # ✅ Overlapping date range — reject, don't store
        print(f"REJECTED: Overlapping date range for user {user_id}, reference_id {reference_id}")
        return {"status": "failure", "message": "Report rejected — overlapping date range with existing report"}

    else:  # ERROR
        print(f"ERROR: Could not determine merge status for user {user_id}")
        raise HTTPException(status_code=500, detail="Could not validate report date range")


@bsa_router.get("/month-wise-overview")
async def bsa_report(request:Request):
    db = request.app.state.mongo_db
    user_id = request.state.user_id
    success_data = await bank_statement_report(db, user_id)
    if success_data is None:
        raise HTTPException(status_code=404, detail="Bank statement not found for this user")
    
    return {
        "status": "success",
        "data": success_data
    }

@bsa_router.get("/summary-of-debit-and-credit_monthwise")
async def bsa_summary_of_debit_and_credit(request:Request,from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None)):
    
    print(from_date,to_date)
    db=request.app.state.mongo_db
    user_id=request.state.user_id
    if not from_date or not to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date and to_date are required query parameters"
        )
    
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d")                          # 2025-04-01 00:00:00
        to_dt   = datetime.strptime(to_date,   "%Y-%m-%d").replace(hour=23, minute=59, second=59)  # 2025-05-31 23:59:59
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if from_dt > to_dt:
        raise HTTPException(
            status_code=400,
            detail={"message": "from_date must be earlier than or equal to to_date"}
        )
    
    delta = to_dt - from_dt
    if delta.days > 730:
        raise HTTPException(
            status_code=400,
            detail={"message": "Date range cannot exceed 2 years"}
        )
    
    success_data=await bsa_summary_of_debit_credit_monthwise(db,user_id,from_dt,to_dt)
    if success_data is None:
        raise HTTPException(status_code=404, detail="Bank statement not found for this user")
    return {
        "status": "success",
        "message": "Summary of DEBIT and CREDIT monthwise",
        "data": success_data
    }


@bsa_router.post("/crm/upload")
async def upload_bsa_crm(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(None),
    data: str = Form(None),
):
    try:
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Input data is required"}
            )

        data_params = json.loads(data)

        # account_id is the CRM identity bridge — mandatory for this route
        account_id = data_params.pop("account_id", None)
        crm_user_id = data_params.pop("crm_user_id", None)

        if not account_id or str(account_id).strip() == "" or not crm_user_id or str(crm_user_id).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "account_id and crm_user_id is required for CRM uploads"}
            )

        response = await handle_bsa_upload_crm(
            account_id=account_id,
            mongodb_connection=request.app.state.mongo_db,
            pg_db = request.app.state.postgres_conn,
            files=files,
            data_params=data_params,
            BackgroundTask=background_tasks,
            crm_user_id=crm_user_id
        )

    except JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON Input"}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise e

    return response

@bsa_router.get("/crm-bsa-statement-report/{acc_id}")
async def crm_bsa_statement_report(request:Request,acc_id:str):
    try:
        acc_id = acc_id.strip()
        return await get_crm_bank_statement_report(db=request.app.state.mongo_db,acc_id=int(acc_id))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message":"Internal server error please contact the admin for support."}
        )

@bsa_router.get("/get-bank-names")
async def bsa_get_bank_names():
    try:
        return await bank_names()
    except HTTPException as e:
        raise e
    except Exception as e:
        print("Error happened at get bank name route",e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Internal server error please contact the admin for support."}
        )