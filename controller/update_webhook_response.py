from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status
from starlette.responses import JSONResponse
from datetime import datetime, timezone



async def update_webhook_response(user_id,payload,db):
    try:
        datablock=payload.get("data",{})
        ref_Id=datablock.get("referenceId")
        if not ref_Id:
            return {"success": False, "error": "No referenceId in payload"}

        existing_doc=await db["bsa_reference"].find_one({"reference_id":ref_Id})

        if not existing_doc:
            print(f"Alert: referenceId {ref_Id} not found in database.")
            return {"success": False, "error": "Reference ID not found"}
        
        sample_payload_received=datetime.now(timezone.utc)
        print(sample_payload_received)
        update_query = {
            "$set": {
                "report_urls.json": datablock.get("jsonUrl"),
                "report_urls.excel": datablock.get("excelUrl"),
                "webhook_response_status": "Completed",
                "webhook_response_code": payload.get("responseCode"),
                "webhook_response_message": payload.get("responseMessage"),
                "webhook_received_at": sample_payload_received,  # Now it has a value!
                "updated_at": datetime.now(timezone.utc)
            }
        }
        await db["bsa_reference"].update_one({"reference_id": ref_Id}, update_query)
        # print(update_query)
        return {"success": True, "message": "Record updated successfully"}
    
    except Exception as e:
        print("Error has been raised in update_webhook_response controller", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":"Internal server error please contact the admin for support."})


        
