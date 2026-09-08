from typing import Optional

from fastapi import APIRouter, Query, Request

from controller.export_controller import export_bsa_report
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
