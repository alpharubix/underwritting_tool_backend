from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import status

ADMIN_ROLES = ('ADMIN','SUPER_ADMIN')

async def get_total_super_anchors(request:Request):
    try:
        requester_role = request.state.role
        if requester_role not in ADMIN_ROLES:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"message":"Forbidden access"}
            )
        db = request.app.state.mongo_db

        total_super_anchors = await db.anchors.find(
            {"role":"SUPER_ANCHOR"},
            {
                "anchor_name":1,
                "anchor_code":1
            }
        )

        no_of_total_super_anchor = len(total_super_anchors)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message":"Super anchors fetched successfully",
                "data":{
                    "no_of_super_anchors":no_of_total_super_anchor
                }
            }
        )


    except Exception as e:
        raise e
    
    