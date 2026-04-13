from fastapi.exceptions import HTTPException
from json import JSONDecodeError
from starlette import status
from fastapi import APIRouter, UploadFile, File, Request, Form
from controller.bsa_uploads import handle_bsa_upload
from typing import List
from tasks.bsa_tasks import process_reconciliation
import json

bsa_router = APIRouter(prefix="/v1/bsa", tags=["BSA"])
@bsa_router.post("/upload")
async def upload_bsa(
    request: Request,
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
        response = await handle_bsa_upload(request.state.user_id,request.app.state.mongo_db,files,data_params)
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

@bsa_router.post("/scoreme-callback")
async def scoreme_webhook(request: Request):
    full_body = await request.json()
    
    # Extract from the 'data' key based on the ScoreMe response you shared
    inner_data = full_body.get("data", {})
    
    ref_id = inner_data.get("referenceId")
    json_url = inner_data.get("jsonUrl")
    
    print(f"Webhook received! Ref: {ref_id}, URL: {json_url}")

    if ref_id and json_url:
        process_reconciliation.delay(ref_id, json_url)
        return {"status": "accepted"}
    
    return {"status": "error", "message": "Missing ref_id or json_url"}








