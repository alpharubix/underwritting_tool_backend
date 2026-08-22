from fastapi import APIRouter,Request,Query
from controller.admin_controller.admin import update_admin,delete_admin,get_users,get_admins_list,get_anchors

admin_router = APIRouter(prefix="/v1/admin")

@admin_router.patch("/update-admin/{login_id}") # THIS ROUTE CAN HANDLE SINGLE UPDATE
async def update_admin_route(request:Request,login_id:str):
    return await update_admin(request,login_id)


@admin_router.get("/admins-list") 
async def get_admins_list_route(request:Request,page:int=Query(1,ge=1)):
    return await get_admins_list(request,page)

@admin_router.get('/users-list')
async def get_users_route(request:Request,page: int = 1):
    #regex using 
    return await get_users(request,page)

@admin_router.get('/anchors/anchor-list')
async def get_anchors_route(request:Request,page:int=1):
    return await get_anchors(request,page)