from fastapi import Request,APIRouter
from controller.anchor_controller.anchor import get_anchors,update_anchor,delete_anchor
anchor_router = APIRouter(prefix="/v1/anchor")

# @anchor_router.get("/dashboard")
# async def anchor_dashboard_route(request: Request,actor_module: str,page: int = 1,limit: int = 10):
#     return await anchor_dashboard(
#         request,
#         actor_module,
#         page,
#         limit
#     )

# @anchor_router.get("/get-anchors")
# async def get_anchors_route(request:Request):
#     """
#     anchors only if he is super-anchor
#     """
#     return await get_anchors(request)

@anchor_router.get("/get-anchors")
async def get_anchors_route(request: Request):
    """
    Filter anchors based on query parameters.
    Only accessible by SUPER_ANCHOR.
    """

    return await get_anchors(request)

@anchor_router.patch("/update/{login_id}")
async def update_anchor_route(request:Request,login_id:str):
    return await update_anchor(request,login_id)

@anchor_router.delete("/delete/{login_id}")
async def delete_anchor_route(request:Request,login_id:str):
    return await delete_anchor(request,login_id)