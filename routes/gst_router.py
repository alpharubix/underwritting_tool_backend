from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from controller.gst_contoller.gst_analyser_controller import get_gstin,update_gstin,get_gstin_basic_info,get_gst_otp,validate_gst_otp_info,send_gstin_to_score_me
gst_router = APIRouter(prefix="/v1/gst", tags=["gst"])


@gst_router.get("/gstin")
async def gstin(request: Request):
    try:
        return await get_gstin(request)
    except HTTPException as e:
        raise e


@gst_router.patch("/gstin")
async def gstin(request: Request):
    try:
       return await update_gstin(request)
    except HTTPException as e:
        raise e

@gst_router.post("/gstin_basic_info")
async def gstin_basic_info(request: Request):
    try:
        return await get_gstin_basic_info(request)
    except HTTPException as e:
        raise e

@gst_router.post("/generate_otp")
async def gst_otp(request: Request):
    try:
        return await get_gst_otp(request)
    except HTTPException as e:
        raise e

@gst_router.post("/validate_otp")
async def validate_otp(request: Request):
    try:
        return await validate_gst_otp_info(request)
    except HTTPException as e:
        raise e

@gst_router.post("/post_gstin")
async def post_gstin(request: Request):
    try:
        return await send_gstin_to_score_me(request)
    except HTTPException as e:
        raise e