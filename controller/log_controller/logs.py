import math
import re

from fastapi import Request, status
from starlette.responses import JSONResponse



ALLOWED_ROLES = ('ADMIN','SUPER_ADMIN')

async def view_logs(
    request: Request,
    page: int = 1,
    status_filter: str | None = None,
    service: str | None = None,
    method: str | None = None,
    path: str | None = None,
    user_id: str | None = None,
    role: str | None = None,
    status_code: int | None = None,
):
    limit = 10
    # Validate page
    if page < 1:
        return JSONResponse(
            content={
                "message": "Page must be greater than or equal to 1"
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    requester_role = getattr(
        request.state,
        "role",
        None,
    )

    # Only allowed roles can view logs
    if requester_role not in ALLOWED_ROLES:
        return JSONResponse(
            content={
                "message": "Forbidden access!"
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    db = request.app.state.mongo_db

    # MongoDB filter
    query = {}

    if status_filter:
        query["status"] = status_filter.upper()

    if service:
        query["service.service_name"] = service

    if method:
        query["request.method"] = method.upper()

    if path:
        query["request.path"] = {
            "$regex": re.escape(path.strip()),
            "$options": "i"
        }
    if user_id:
        query["user.user_id"] = user_id

    if role:
        query["user.role"] = role

    if status_code:
        query["response.status_code"] = status_code

    # Pagination
    skip = (page - 1) * limit

    # Total matching logs
    total_logs = await db.logs.count_documents(query)

    # Fetch logs
    logs = await db.logs.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
    

    total_pages = math.ceil(total_logs / limit)

    return JSONResponse(
        content={
            "page": page,
            "limit": limit,
            "total_logs": total_logs,
            "total_pages": total_pages,
            "logs": logs,
        },
        status_code=status.HTTP_200_OK,
    )
