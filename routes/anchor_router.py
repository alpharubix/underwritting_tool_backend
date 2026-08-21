from fastapi import Request,APIRouter
from controller.anchor_controller.anchor import get_anchors
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