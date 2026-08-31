from fastapi import Query, Request,APIRouter
from controller.anchor_controller.anchor import get_associated_anchors, get_users_reports,update_anchor,delete_anchor,get_users
anchor_router = APIRouter(prefix="/v1/anchor")



@anchor_router.get("/associated-anchors")
async def get_anchors_route(request:Request,page:int=1):
    """
    Filter anchors based on query parameters.
    Only accessible by SUPER_ANCHOR.
    """
    return await get_associated_anchors(request)

@anchor_router.get('/users')
async def get_users_route(request:Request,page:int=Query(1,ge=1)):
    return await get_users(request,page)

@anchor_router.patch("/update/{login_id}")
async def update_anchor_route(request:Request,login_id:str):
    return await update_anchor(request,login_id)

@anchor_router.delete("/delete/{login_id}")
async def delete_anchor_route(request:Request,login_id:str):
    return await delete_anchor(request,login_id)

@anchor_router.get('/get-user-reports/{module}')
async def get_user_reports_route(request:Request,module:str,cust_id:str,page:int=1):
    return await get_users_reports(request,module,cust_id,page)