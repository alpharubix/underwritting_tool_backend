import datetime
from time import timezone
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi import Request, status

async def create_credit_template(request:Request):
    try:
        body = await request.json()
        user_id = request.state.user_id
        requster_role = request.state.role

        if requster_role!="BANK":
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"message":"Forbidden access !"}
            )
        template_name = body.get("parameters")
        loan_product = body.get("loan_product")
        loan_type = body.get("loan_type")
        credit_template = body.get("credit_template")

        db = request.app.state.mongo_db 

        credit_doc ={
            "template_name":template_name,
            "loan_product":loan_product,
            "loan_type":loan_type,
            "credit_template":credit_template,
            "created_by":user_id,
            "created_at":datetime.now(timezone.utc)
        }
        credit_result = await db.credit_template.insert_one(credit_doc)

        if not credit_result.acknowledged or not credit_result.inserted_id:
            return JSONResponse(
                content={"message":"Failed to create the credit template"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        raise e

async def evaluate_credit_template(request:Request,template_id:str):
    try:
        db = request.app.state.mongo_db
        user_id = request.state.user_id

        template = await db.credit_template.find_one({
            "_id":ObjectId(template_id)
        })

        if not template:
            return JSONResponse(
                content={'message':"Credit template not found"},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        else:
            credit_template = template['credit_template'].to_list(length=None)
            

            bsa_report = await db.bsa_bank_mergedstatements.find_one({"user_id": user_id})
            gst_report = await db.gst_analayzed_report.find_one({"user_id": user_id})
            itr_report = await db.itr_analyzed_report.find_one({"user_id": user_id})
            cibil_report = await db.cibil_report.find_one({"user_id": user_id})
            
            missing_reports = {
                "BSA":bsa_report,
                "ITR":itr_report,
                "GST":gst_report,
                "CIBIL":cibil_report
            }

            missing = [name for name,report in missing_reports.items() if report is None]

            if missing :
                return JSONResponse(
                    content={
                        "message":f"Failed to evaluate the credit eligibility" ,
                        "data":{
                            "user_id":user_id,
                            "requested_credit_template":credit_template,
                            "missing_reports":missing,
                        }},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            return {"message": "All required reports are available"}
            


    except Exception as e:
        raise e
    