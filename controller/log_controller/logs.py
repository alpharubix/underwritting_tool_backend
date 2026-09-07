import math

from fastapi.responses import JSONResponse
from fastapi import Request,Response
from fastapi import status as status


ALLOWED_ROLES = ('ADMIN','SUPER_ADMIN')

async def view_logs(request:Request,page:int):
    limit = 10

    requester_role = request.state.role
    if requester_role not in ALLOWED_ROLES:
        return JSONResponse(
            content={"message":"Forbidden access !"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    else:
        db = request.app.state.mongo_db
        total_logs = await db.logs.count_documents({})

        total_pages = math.ceil(total_logs / limit)
        skip = (page-1) * limit
        logs = await db.logs.find({}).sort("timestamp",-1).skip(skip).limit(limit).to_list(length=limit)

        return JSONResponse(
            content={
                "page-info":{
                    "page":page,
                    "limit":limit,
                    "total_records":total_logs,
                    "total_pages":total_pages,
                    "logs":logs
                }
            },
            status_code=status.HTTP_200_OK
        )
