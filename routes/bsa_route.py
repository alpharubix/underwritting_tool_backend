from fastapi.exceptions import HTTPException
from fastapi  import BackgroundTasks
from json import JSONDecodeError
from starlette import status
from fastapi import APIRouter, UploadFile, File, Request, Form
from controller.bsa_uploads import handle_bsa_upload
from controller.crm_bsa_upload_controller import handle_bsa_upload_crm
from controller.update_webhook_response import update_webhook_response
from controller.bank_statement_report import bank_statement_report
from typing import List
from controller.fetch_and_save_bank_report import fetch_and_save_bank_report
from controller.backgroud_task_controller import send_report_mail_based_on_request
import json

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
        account_id = data_params.get("account_id")
        if not account_id or str(account_id).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "account_id is required for CRM uploads"}
            )

        response = await handle_bsa_upload_crm(
            account_id=account_id,
            mongodb_connection=request.app.state.mongo_db,
            pg_db = request.app.state.postgres_conn,
            files=files,
            data_params=data_params,
            BackgroundTask=background_tasks
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




