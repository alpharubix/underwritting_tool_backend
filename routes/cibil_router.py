from fastapi import APIRouter
from fastapi import Request
from controller.cibil_controller.cibil_bereau_controller import generate_cibil_report_otp,validate_cibil_otp,resend_cibil_otp

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
