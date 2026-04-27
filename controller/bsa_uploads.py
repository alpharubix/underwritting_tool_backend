import os
import httpx
from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from services.scoreme_service import upload_to_scoreme,create_bsa_ref_document
from tasks.bsa_tasks import upload_files_to_gcs_and_save_metadata
from dotenv import load_dotenv
load_dotenv()
async def handle_bsa_upload(user_id,mongodb_connection:AsyncIOMotorDatabase, files,data_params,BackgroundTask:BackgroundTasks):
     #validate meta field
    try:
        required_fields = ["accountNumber", "entityType", "accountType", "bankCode"] #madatory input fields

        for field in required_fields:
            value = data_params.get(field)
            if not value or str(value).strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message":f"{field} is required"}

                )

        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message":"No files uploaded. Please upload at least one PDF file."}
            )

        if len(files) > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message":"Too many files. Maximum allowed is 12, but {len(files)} were uploaded."}
            )

        invalid_files = [f.filename for f in files if not f.filename.lower().endswith(".pdf")]
        if invalid_files:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={"message":f"Only PDF files are allowed. Invalid files: {', '.join(invalid_files)}"}
            )

        #__append user_id to the request for request tracking
        data_params['userapplicationid'] = user_id

        # ── Forward to ScoreMe

        scoreme_response,request_initiated_time = await upload_to_scoreme(files, data_params)

        if scoreme_response:
           # fetch the reference id and status from the dict
           reference_id = scoreme_response.get("data").get("referenceId")
           response_message = scoreme_response.get("responseMessage")
           response_code = scoreme_response.get("responseCode")

           #create the bsa_ref document post successfull response from the scoreme server
           await create_bsa_ref_document(user_id=user_id,reference_id=reference_id,input_data=data_params,bsa_request_status="Submitted",bsa_request_initiated_time=request_initiated_time,bsa_request_response_message=response_message,bsa_request_response_code=response_code,mongobd_connection=mongodb_connection)

           #create a background task to store the input bsa files to the storage object
           BackgroundTask.add_task(upload_files_to_gcs_and_save_metadata,files,user_id,reference_id,mongodb_connection)

        #return back the accepted message back to the clinet for every successfull uploads
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED,content={"message":"File is under processing we will let you know in the mail once the report got"
                                                                                    " generated"})

    except HTTPException as e: #caught the http exceptions raised at upload_to_scoreme
        raise e
    except Exception as e:
        print("Error has been raised in bsa controller", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error please contact the admin for support."})



async def bank_names():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://sm-bsa-sandbox.scoreme.in/bsa/external/getBankNames",
                headers={
                    "clientId": os.getenv("CLIENT_ID"),
                    "clientSecret": os.getenv("CLIENT_SECRET")
                },
            )
            if response.status_code == 200:
                data = response.json().get("data")
                return JSONResponse(content={"message": "success","data":data})

            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error please contact the admin for support."})
    except HTTPException as e:
        raise e
    except Exception as e:
        print("Error has been raised in bsa get bank names controller", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={"message": "Internal server error please contact the admin for support."})


