from typing import Any

from fastapi import APIRouter, Body,Request,Query
from controller.admin_controller.admin import update_admin,delete_admin,get_users,get_admins_list,get_anchors,get_payments,get_service_requests_payments

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

@admin_router.delete('/admins/{login_id}')
async def delete_admin_route(request:Request,login_id:str):
    return await delete_admin(request,login_id)

@admin_router.get('/anchors/anchor-list')
async def get_anchors_route(request:Request,page:int=1):
    return await get_anchors(request,page)

@admin_router.get('/payments')
async def get_payments_route(request:Request,page:int=1,limit=10):
    return await get_payments(request,page,limit)

@admin_router.get('/service-request-user')
async def get_service_requests_payments_route(request:Request):
    return await get_service_requests_payments(request)