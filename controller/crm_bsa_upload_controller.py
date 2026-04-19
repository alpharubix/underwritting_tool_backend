from fastapi import BackgroundTasks, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from asyncpg import connection
from services.scoreme_service import upload_to_scoreme, create_bsa_ref_document
from tasks.bsa_tasks import upload_files_to_gcs_and_save_metadata
from services.auth_service import get_crm_user

async def handle_bsa_upload_crm(
    account_id: str,
    mongodb_connection: AsyncIOMotorDatabase,
    pg_db:connection,
    files,
    data_params: dict,
    BackgroundTask: BackgroundTasks,
    crm_user_id:str
):
    #check if the request has crm_user_id or not because it is crucial for security reasons

    crm_user = await get_crm_user(int(crm_user_id),pg_db)


    # ── Step 1: Resolve internal user from CRM account_id
    user = await mongodb_connection["users"].find_one({"account_id": int(account_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": (
                    "No matching user found for the provided account ID. "
                    "Please sync your CRM with 5PointCredit — "
                    "the user must be created in the application before proceeding."
                )
            }
        )

    user_id = str(user["_id"])  # internal user identity from this point on

    # ── Step 2: Validate mandatory fields
    required_fields = ["accountNumber", "entityType", "accountType", "bankCode"]

    for field in required_fields:
        value = data_params.get(field)
        if not value or str(value).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": f"{field} is required"}
            )

    # ── Step 3: File validations
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "No files uploaded. Please upload at least one PDF file."}
        )

    if len(files) > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Too many files. Maximum allowed is 12, but {len(files)} were uploaded."
            }
        )

    invalid_files = [f.filename for f in files if not f.filename.lower().endswith(".pdf")]
    if invalid_files:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "message": f"Only PDF files are allowed. Invalid files: {', '.join(invalid_files)}"
            }
        )

    # ── Step 4: Append internal identifiers to the request payload
    data_params["userapplicationid"] = user_id

    crm_user_id = data_params.get("crm_user_id")  # optional but saved if present

    # ── Step 5: Forward to ScoreMe
    scoreme_response, request_initiated_time = await upload_to_scoreme(files, data_params)

    if scoreme_response:
        reference_id = scoreme_response.get("data", {}).get("referenceId")
        response_message = scoreme_response.get("responseMessage")
        response_code = scoreme_response.get("responseCode")

        # ── Step 6: Persist BSA reference — include crm_user_id if provided
        await create_bsa_ref_document(
            user_id=user_id,
            reference_id=reference_id,
            input_data=data_params,
            bsa_request_status="Submitted",
            bsa_request_initiated_time=request_initiated_time,
            bsa_request_response_message=response_message,
            bsa_request_response_code=response_code,
            mongobd_connection=mongodb_connection,
            is_request_from_crm=True,
            crm_user_info=crm_user  # conditionally attach
        )

        # ── Step 7: Background task to push files to GCS
        BackgroundTask.add_task(
            upload_files_to_gcs_and_save_metadata,
            files,
            user_id,
            reference_id,
            mongodb_connection
        )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "File is under processing. We will notify you via email once the report is generated."
        }
    )