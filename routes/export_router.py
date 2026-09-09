from typing import Optional

from fastapi import APIRouter, Query, Request

from controller.export_controller import export_bsa_report
from controller.export_generic_controller import (
    export_cibil_report_generic,
    export_gst_report_generic,
    export_itr_report_generic,
)
export_router = APIRouter(prefix="/v1/export")

@export_router.get("/bsa")
async def export_bsa_route(
    request: Request,
    from_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    to_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    cust_id: Optional[str] = None,
):
    user_id = request.state.user_id
    requester_role = request.state.role

    return await export_bsa_report(
        db=request.app.state.mongo_db,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        requester_role=requester_role,
        cust_id=cust_id,
    )


@export_router.get("/gst")
async def export_gst_route(
    request: Request,
    reference_id: str | None = None,
    cust_id: str | None = None,
):
    user_id = cust_id or request.state.user_id
    return await export_gst_report_generic(
        db=request.app.state.mongo_db,
        user_id=user_id,
        reference_id=reference_id,
    )


@export_router.get("/itr")
async def export_itr_route(
    request: Request,
    cust_id: str | None = None,
):
    user_id = cust_id or request.state.user_id
    return await export_itr_report_generic(
        db=request.app.state.mongo_db,
        user_id=user_id,
    )


@export_router.get("/cibil")
async def export_cibil_route(
    request: Request,
    reference_id: str = Query(...),
    cust_id: str | None = None,
):
    return await export_cibil_report_generic(
        db=request.app.state.mongo_db,
        reference_id=reference_id,
        user_id=cust_id or request.state.user_id,
    )
