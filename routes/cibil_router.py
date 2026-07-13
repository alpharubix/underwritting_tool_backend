from fastapi import APIRouter
from fastapi import Request
from controller.cibil_controller.cibil_bereau_controller import generate_cibil_report_otp, validate_cibil_otp, \
    resend_cibil_otp, get_list_cibil_reports, cibil_overview, account_summary,payment_history,analysis,otp_flow_id_webhook_status

cibil_router = APIRouter(prefix="/v1/cibil",tags=["cibil"])

@cibil_router.post("/generate-otp")
async def generate_otp(request: Request):
    return  await generate_cibil_report_otp(request=request)

@cibil_router.post("/validate-otp")
async def validate_otp(request: Request):
    return await validate_cibil_otp(request=request)

@cibil_router.post("/resend-otp")
async def resend_otp(request: Request):
    return await resend_cibil_otp(request=request)

@cibil_router.get("/list-reports")
async def list_reports(request: Request):
    return await get_list_cibil_reports(request=request)

@cibil_router.get("/overview/{reference_id}")
async def get_cibil_overview(request: Request, reference_id: str):
    return await cibil_overview(reference_id=reference_id,request=request)

@cibil_router.get("/account-summary/{reference_id}")
async def get_cibil_account_summary(request: Request, reference_id: str):
    return await account_summary(reference_id=reference_id,request=request)

@cibil_router.get("/payment-history/{reference_id}")
async def get_cibil_payment_history(request: Request, reference_id: str):
    return await payment_history(reference_id=reference_id,request=request)

@cibil_router.get("/analysis/{reference_id}")
async def get_cibil_analysis(request: Request, reference_id: str):
    return await analysis(reference_id=reference_id,request=request)

@cibil_router.get("/webhook-status/{otp_flow_id}")
async def get_cibil_webhook_status(request: Request, otp_flow_id: str):
    return await otp_flow_id_webhook_status(otp_flow_id=otp_flow_id,request=request)