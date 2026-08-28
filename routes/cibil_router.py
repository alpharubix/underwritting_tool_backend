from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from controller.cibil_controller.cibil_bereau_controller import (
    account_summary,
    analysis,
    cibil_overview,
    generate_cibil_report_otp,
    get_list_cibil_reports,
    get_list_r1xcrm_reports,
    otp_flow_id_webhook_status,
    payment_history,
    resend_cibil_otp,
    validate_cibil_otp,
)

ALLOWED_ROLES = ('ADMIN','ANCHOR','SUPER_ANCHOR')

cibil_router = APIRouter(prefix="/v1/cibil",tags=["cibil"])

@cibil_router.post("/generate-otp")
async def generate_otp(request: Request,cust_id:Optional[str]=None):
    return  await generate_cibil_report_otp(request=request,cust_id=cust_id)

@cibil_router.post("/validate-otp")
async def validate_otp(request: Request,cust_id:Optional[str]=None):
    return await validate_cibil_otp(request=request,cust_id=cust_id)

@cibil_router.post("/resend-otp")
async def resend_otp(request: Request,cust_id:Optional[str]=None):
    return await resend_cibil_otp(request=request,cust_id=cust_id)

@cibil_router.get("/list-reports")
async def list_reports(request: Request,cust_id:Optional[str]=None): 
    return await get_list_cibil_reports(request=request,cust_id=cust_id)

@cibil_router.get("/r1xcrm-list-reports/{acc_id}")
async def list_r1xcrm_reports(request: Request,acc_id:int):
    return await get_list_r1xcrm_reports(request=request,acc_id=acc_id)

@cibil_router.get("/overview/{reference_id}")
async def get_cibil_overview(request: Request, reference_id: str):
    return await cibil_overview(reference_id=reference_id,request=request)

@cibil_router.get("/r1xcrm-overview/{reference_id}")
async def get_r1xcrm_cibil_overview(request: Request, reference_id: str):
    return await cibil_overview(reference_id=reference_id,request=request)

@cibil_router.get("/account-summary/{reference_id}")
async def get_cibil_account_summary(request: Request, reference_id: str):
    return await account_summary(reference_id=reference_id,request=request)
    
@cibil_router.get("/r1xcrm-account-summary/{reference_id}")
async def get_r1xcrm_cibil_account_summary(request: Request, reference_id: str):
    return await account_summary(reference_id=reference_id,request=request)

@cibil_router.get("/payment-history/{reference_id}")
async def get_cibil_payment_history(request: Request, reference_id: str):
    return await payment_history(reference_id=reference_id,request=request)

@cibil_router.get("/r1xcrm-payment-history/{reference_id}")
async def get_r1xcrm_cibil_payment_history(request: Request, reference_id: str):
    return await payment_history(reference_id=reference_id,request=request)

@cibil_router.get("/analysis/{reference_id}")
async def get_cibil_analysis(request: Request, reference_id: str):
    return await analysis(reference_id=reference_id,request=request)

@cibil_router.get("/r1xcrm-analysis/{reference_id}")
async def get_r1xcrm_cibil_analysis(request: Request, reference_id: str):
    return await analysis(reference_id=reference_id,request=request)

@cibil_router.get("/webhook-status/{otp_flow_id}")
async def get_cibil_webhook_status(request: Request, otp_flow_id: str):
    return await otp_flow_id_webhook_status(otp_flow_id=otp_flow_id,request=request)