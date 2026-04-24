from fastapi.exceptions import HTTPException
from fastapi  import BackgroundTasks, Query
from json import JSONDecodeError
from starlette import status
from fastapi import APIRouter, UploadFile, File, Request, Form
from controller.bsa_uploads import handle_bsa_upload
from controller.crm_bsa_upload_controller import handle_bsa_upload_crm
from controller.update_webhook_response import update_webhook_response
from controller.bank_statement_report import bank_statement_report,get_crm_bank_statement_report
from typing import List, Optional
from controller.fetch_and_save_bank_report import fetch_and_save_bank_report
from controller.backgroud_task_controller import send_report_mail_based_on_request
from controller.bsa_summary_drcr_monthwise import bsa_summary_of_debit_credit_monthwise
from controller.cashflow_controller import build_cashflow_report
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
async def webhook_response(request:Request,background_tasks: BackgroundTasks):
    payload = await request.json()
    db = request.app.state.mongo_db
    user_id = request.state.user_id
    success=await update_webhook_response(user_id,payload,db)
    if not success["success"]:
        raise HTTPException(status_code=400, detail=success["error"])
    
    json_url = payload.get("data", {}).get("jsonUrl")
    reference_id=payload.get("data", {}).get("referenceId")
    if json_url:
        # Pass db, user_id, and json_url to the consumer
        background_tasks.add_task(
            fetch_and_save_bank_report, 
            db, 
            user_id, 
            reference_id,
            json_url
        )

        background_tasks.add_task(
            send_report_mail_based_on_request,
            user_id,
            reference_id,
            request.app.state.mongo_db,
            request.app.state.postgres_conn,
        )
    return {"status": "success", "message": "Reference updated and report ingestion started"}
    


@bsa_router.get("/calculated-bank-statement-report")
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


@bsa_router.get("/cashflow")
async def cashflow_report(
    request:    Request,
    from_month: str = Query(..., description="Start month in YYYY-MM format, e.g. 2024-01"),
    to_month:   str = Query(..., description="End month in YYYY-MM format, e.g. 2024-12"),
):
    db=request.app.state.mongo_db
    user_id=request.state.user_id
    result = await build_cashflow_report(db, user_id, from_month, to_month)
 
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result)
 
    return result

