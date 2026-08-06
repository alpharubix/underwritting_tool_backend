from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from controller.gst_contoller.gst_analyser_controller import get_gstin, update_gstin, get_gstin_basic_info, get_gst_otp, \
    validate_gst_otp_info, send_gstin_to_score_me, gst_ref_id_status, get_all_user_ref_ids, \
    get_overview_and_account_details, get_top_suppliers_and_customers,get_monthly_sales_and_purchase_summary, \
    get_r1xcrm_gst_ref_id_status, get_r1xcrm_overview, get_r1xcrm_top_suppliers_and_customers, get_r1xcrm_monthly_sales_purchase_summary,add_new_gst

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

@gst_router.post("/gstin/add-new")
async def gstin_add(request: Request):
    try:
        return await add_new_gst(request)
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
        user_id = request.state.user_id
        return await get_all_user_ref_ids(request,user_id)
    except HTTPException as e:
        raise e

@gst_router.get("/r1xcrm-gst-ref-status/{acc_id}")
async def r1xcrm_get_gst_ref_status(request: Request,acc_id:int):
    try:
        return await get_r1xcrm_gst_ref_id_status(request,acc_id)
    except HTTPException as e:
        raise e

@gst_router.post("/overview")
async def overview(request: Request):
    try:
        return await get_overview_and_account_details(request)
    except HTTPException as e:
        raise e

@gst_router.post("/r1xcrm-overview")
async def r1xcrm_overview(request: Request):
    try:
        return await get_r1xcrm_overview(request)
    except HTTPException as e:
        raise e

@gst_router.post("/top-suppliers-and-customers")
async def top_suppliers_and_customers(request: Request):
    try:
        return await get_top_suppliers_and_customers(request)
    except HTTPException as e:
        raise e

@gst_router.post("/r1xcrm-top-suppliers-and-customers")
async def r1xcrm_top_suppliers_and_customers(request: Request):
    try:
        return await get_r1xcrm_top_suppliers_and_customers(request)
    except HTTPException as e:
        raise e

@gst_router.post("/monthly-sales-purchase-summary")
async def monthly_sales_purchase_summary(request: Request):
    try:
        return await get_monthly_sales_and_purchase_summary(request)
    except HTTPException as e:
        raise e


@gst_router.post("/r1xcrm-monthly-sales-purchase-summary")
async def r1xcrm_monthly_sales_purchase_summary(request: Request):
    try:
        return await get_r1xcrm_monthly_sales_purchase_summary(request)
    except HTTPException as e:
        raise e