from fastapi import APIRouter
from starlette.requests import Request
from controller.kyc_controller.aadhar_kyc_controller import generate_aadhaar_otp,validate_aadhaar_otp,fetch_user_aadhaar_details,get_kyc_flow_id_status,get_documents_list,fetch_documents_url,generate_digilocker_url,get_current_session,is_document_already_exists
kyc_router = APIRouter(prefix="/v1/kyc", tags=["KYC"])


@kyc_router.post("/aadhaar/generate-otp", tags=["KYC"])
async def generate_otp(request: Request):
    return await generate_aadhaar_otp(request)

@kyc_router.post("/aadhaar/validate-otp", tags=["KYC"])
async def validate_otp(request: Request):
    return await validate_aadhaar_otp(request)

@kyc_router.get("/aadhaar/details",tags=["KYC"])
async def aadhaar_details(request: Request):
    return await fetch_user_aadhaar_details(request)

@kyc_router.get("/digilocker/generate-url",tags=["KYC"])
async def digilocker_url(request: Request):
    return await generate_digilocker_url(request)

# @kyc_router.patch("/digilocker/session-status",tags=["KYC"])
# async def session_status_update(request: Request):
#     return await update_session_status(request)


@kyc_router.post("/digilocker/session-status",tags=["KYC"])
async def session_status(request: Request):
    return await get_kyc_flow_id_status(request)


@kyc_router.post("/digilocker/list-documents",tags=["KYC"])
async def list_documents(request: Request):
    return await get_documents_list(request)

@kyc_router.post("/digilocker/document-url",tags=["KYC"])
async def document_url(request: Request):
    return await fetch_documents_url(request)

@kyc_router.get("/digilocker/document-precheck",tags=["KYC"])
async def document_precheck(request: Request):
    return await is_document_already_exists(request)

@kyc_router.get("/digilocker/current-status",tags=["KYC"])
async def current_status(request: Request):
    return await get_current_session(request)




