from fastapi import APIRouter, UploadFile, File, Request, Form
from database.db import get_mongo_db
from controllers.bsa_uploads import handle_bsa_upload
from typing import List
from tasks.bsa_tasks import process_reconciliation
import json

router = APIRouter()
@router.post("/upload")
async def upload_bsa(
    files: List[UploadFile] = File(...),
    metadata: str = Form(...)  # This will be the JSON string of your data block
):
    db = get_mongo_db()
    
    # Convert string back to dictionary
    try:
        data_params = json.loads(metadata)
        # Pull the account number from the metadata we just parsed
        acc_no = data_params.get("accountNumber")
    except Exception as e:
        return {"status": "error", "message": f"Invalid JSON: {str(e)}"}
    response = await handle_bsa_upload(db, files, data_params)
    return response

@router.post("/scoreme-callback")
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








