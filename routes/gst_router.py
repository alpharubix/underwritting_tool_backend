from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from controller.gst_contoller.gst_analyser_controller import get_gstin, update_gstin, get_gstin_basic_info, get_gst_otp, \
    validate_gst_otp_info, send_gstin_to_score_me, gst_ref_id_status,get_all_user_ref_ids

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

@gst_router.post("/gstin-basic-info")
async def gstin_basic_info(request: Request):
    try:
        return await get_gstin_basic_info(request)
    except HTTPException as e:
        raise e

@gst_router.post("/generate-otp")
async def gst_otp(request: Request):
    try:
        return await get_gst_otp(request)
    except HTTPException as e:
        raise e

@gst_router.post("/validate-otp")
async def validate_otp(request: Request):
    try:
        return await validate_gst_otp_info(request)
    except HTTPException as e:
        raise e

@gst_router.post("/post-gstin")
async def post_gstin(request: Request):
    try:
        return await send_gstin_to_score_me(request)
    except HTTPException as e:
        raise e


@gst_router.post("/get-gst-ref-status")
async def get_gst_ref_status(request: Request):
    try:
        return await gst_ref_id_status(request)
    except HTTPException as e:
        raise e

@gst_router.get("/users-ref-ids")
async def get_user_ref_id(request: Request):
    try:
        return await get_all_user_ref_ids(request)
    except HTTPException as e:
        raise e