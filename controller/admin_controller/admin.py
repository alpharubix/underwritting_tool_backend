import math
from typing import Any

from fastapi import Header,Request,status
from bson import ObjectId
from starlette.requests import Request
from starlette.responses import JSONResponse
from datetime import datetime, timedelta,timezone

from config import config

""" DOCUMENTATION - 
admins should see - 
super admin ->admin, users , anchors(other controller),super anchors(other controller)
admin -> users
"""


ALLOWED_ROLES = {"SUPER_ADMIN","ADMIN"}

# async def admin_dashboard(request:Request,module:str):
#     """
#         role -> superadmin 
#         module -> admin,user

#     """
#     db = request.app.state.mongo_db
#     requester_role = request.state.role
#     ALLOWED_MODULES = {"ADMIN","USERS"}

#     module=module.lower() 
#     if requester_role=="SUPER_ADMIN":
#         #fetch the collection of module dynamically
#         if module not in ALLOWED_MODULES:
#             return JSONResponse(
#                 content={"message":f"Invalid module : {module}"},
#                 status_code=status.HTTP_400_BAD_REQUEST
#             )
#         #fetch the modules 
#         else:
#             data = await db.module.find({},{"_id":0})

#     else:
#         #HE IS ADMIN
#         pass    



async def update_admin(request:Request,incoming_login_id:str):
    #ONLY SUPER ADMIN PREVILEGE
    requested_role = request.state.role

    body = await request.json()
    keys = body.keys() #ATTRIBUTE checking

    if not incoming_login_id:
        return JSONResponse(
            content={"message": "Please provide the login ID"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if requested_role!="SUPER_ADMIN":
        return JSONResponse(
            content={"message":"Forbidden access !"},
            status_code=status.HTTP_403_FORBIDDEN
        )

    ALLOWED_ATTR = {"admin_status","role","login_id"}
    CLOSEST_ATTR = {}

    db = request.app.state.mongo_db

    invalid_keys = set(keys) - ALLOWED_ATTR

    if invalid_keys:
        CLOSEST_ATTR = {
            key: actual
            for key in invalid_keys
            for actual in ALLOWED_ATTR
            if actual in key or key in actual
        }
        return JSONResponse(
            content={"message":f"Invalid keys found : {list(invalid_keys)}","Closest keys":CLOSEST_ATTR},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    now = datetime.now(timezone.utc)

    target_admin = await db.admins.find_one({
        "login_id":incoming_login_id

    })

    if not target_admin :
        return JSONResponse(
            content={"message":"Admin not found | Please recheck the login-id"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    old_data = {
        key:target_admin.get(key)
        for key in keys
    }
    redundant_data = {
        key:value
        for key,value in body.items()
        if old_data.get(key) == value
    }

    update_data = {
        key: value
        for key, value in body.items()
        if key not in redundant_data
    }
    update_data["updated_at"]=now.isoformat()
    print("Redundant data : ",redundant_data)
    print("Update data : ",update_data)
    admin_result = await db.admins.update_one(
        {"_id": target_admin["_id"]},
        {"$set":update_data}
    )

    if admin_result.matched_count==0:
        return JSONResponse(
            content={"message":"Failed to update - "},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    final_updated_data = {
        "login_id":incoming_login_id,
        f"old data":old_data,
        f"updated data":update_data
    }
    print(admin_result)

    return JSONResponse(
        content={"message":f"Admin with the login-id : {incoming_login_id} has been updated successfully",**final_updated_data},
        status_code=status.HTTP_200_OK
    )
async def delete_admin(request:Request,login_id:str):
    requester_role = request.state.role

    if requester_role !="SUPER_ADMIN" :
        return JSONResponse(
            content={"Cant delete ! Forbidden access"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    db = request.app.state.mongo_db
    target_admin = await db.admins.find_one({"login_id":login_id})

    if target_admin is None: 
        return JSONResponse(
            content={"message":"Admin not found for the deletion"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    else:
        admin_delete = await db.admins.delete_one({
            "login_id":login_id,
            "role":"ADMIN"
        })

        auth_delete = await db.auth.delete_one({
            "_id":ObjectId(target_admin["_id"])
        })

        if admin_delete.deleted_count == 0 or auth_delete.deleted_count==0:
            return JSONResponse(
                content={"message":"Couldnt delete | Internal Server Error"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return JSONResponse(
            content={"message":"Admin deleted successfully !"},
            status_code=status.HTTP_410_GONE
            )


# async def dashboard_admins(request:Request):
#     db = request.app.state.mongo_db
#     requester_role = request.state.role
#     # if super-admin - admins and super-anchors and anchors
#     # if admin - super-anchors , anchors and users
#     # if super-anchors - anchors , users
#     # if anchors - users
#     print("Requester Role : ",requester_role)

#     ALLOWED_ROLES = {"SUPER_ADMIN","ADMIN","SUPER_ANCHOR","ANCHOR"}

#     if requester_role not in ALLOWED_ROLES:
#         print("Inside not allowed roles")
#         return JSONResponse(
#             content={"message":"Forbidden access !"},
#             status_code=status.HTTP_403_FORBIDDEN
#         )
    
#     user_id = request.state.user_id
#     users =  await db.users.find({"anchor_id":user_id},{"_id":0}).to_list(length=None)

#     if requester_role == "SUPER_ADMIN":
#         # admins, super_anchors, anchors,users
#         admins = await db.admins.find({"role":"ADMIN"},{"_id":0}).to_list(length=None)
#         super_anchors = await db.anchors.find({"role":"SUPER_ANCHOR"},{"_id":0}).to_list(length=None)
#         anchors = await db.anchors.find({"role":"ANCHOR"},{"_id":0}).to_list(length=None)
#         data = {"role":requester_role,"super_anchors":super_anchors,"admins":admins,"anchors":anchors,"users":users}
#         return data

#     elif requester_role == "ADMIN":
#         #super_anchors, anchors,users
#         super_anchors = await db.anchors.find({"role":"SUPER_ANCHOR"},{"_id":0}).to_list(length=None)
#         anchors = await db.anchors.find({"role":"ANCHOR"},{"_id":0}).to_list(length=None)
#         data = {"role":requester_role,"super_anchors":super_anchors,"anchors":anchors,"users":users}
#         return data

#     elif requester_role == "SUPER_ANCHOR":
#         # anchors, users
#         anchors = await db.anchors.find({"role":"ANCHOR"},{"_id":0}).to_list(length=None)
#         data = {"role":requester_role,"anchors":anchors,"users":users}
#         return data

#     else:
#         #anchor
#         #view USERS info, he is admin
#         data={"role":requester_role,"users":users}
#         return data

# async def get_userss(request:Request,page:int):
    
#     limit=10
#     db = request.app.state.mongo_db
#     requester_role = request.state.role
#     skip = (page-1)*limit
#     print(requester_role)
#     if requester_role not in ALLOWED_ROLES:
#         return JSONResponse(
#             content={
#                 "message": "You are not authorized to access users"
#             },
#             status_code=status.HTTP_403_FORBIDDEN
#         )   

#     total_users = await db.users.count_documents({})

#     projection = {
#         "_id":0,
#         "created_at":0,
#         "updated_at":0,
#         "anchor_id":0
#     }
    

#     users = await db.users.find({},projection).skip(skip).limit(limit).to_list(length=limit)
#     current_range = f"{((page-1)*limit)+1}-{(page)*limit}"

#     return JSONResponse(
#         content={
#                     "message":"Users fetched successfully",
#                     "data":users,
#                     "pagination": {
#                         "page": page,
#                         "current_range":current_range,
#                         "total": total_users,
#                         "remaining_records":total_users-(page*limit),
#                         "total_pages":total_users//limit
#                     }
#                 },
#         status_code=status.HTTP_200_OK
#     )

async def get_users(request: Request,page:int):
    limit = 10
    
    EXPECTED_FILTERS = {
        "account_id": int,
        "customer_name": str,
        "company_name": str,
        "email_id":str,
        "phone": str,
        "gst_number": str,
        "status": str,
        "created_at": datetime,
        "updated_at": datetime,
        "anchor_id": ObjectId
    }

    #ROLE Validation 
    requester_role = request.state.role
    if requester_role not in ALLOWED_ROLES:
        return JSONResponse(
            content={"message": "Forbidden access"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    #Empty filters validation - may not be used much as frontend is directly sending the correct filters only
    filters = dict(request.query_params)
    # if not filters:
    #     return JSONResponse(
    #         content={"message": "Filters are needed | Got empty filters"},
    #         status_code=status.HTTP_400_BAD_REQUEST
    #     )

    #Filters checking
    wrong_filters = set(filters.keys()) - set(EXPECTED_FILTERS.keys())
    for wrong_filter in wrong_filters:
        filters.pop(wrong_filter)

    query = {}
    for filter, filter_val in filters.items():

        filter_type = EXPECTED_FILTERS[filter]

        if filter_type == datetime:
            try:
                start_date = datetime.fromisoformat(filter_val)
                end_date = start_date + timedelta(days=1)
            except ValueError:
                return JSONResponse(
                    content={"message": f"Invalid datetime value : {filter_val}"},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            query[filter] = {
                "$gte": start_date,
                "$lt": end_date
            }

            continue

        try:
            filter_val = filter_type(filter_val)
        except (ValueError, TypeError):
            return JSONResponse(
                content={
                    "message": f"Invalid value for {filter} : {filter_val}"
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if filter_type == str:
            query[filter] = {
                "$regex": f"^{filter_val}",
                "$options": "i"
            }
        else:
            query[filter] = filter_val                  
    db = request.app.state.mongo_db

    skip = (page - 1) * limit
    users = await db.users.aggregate([
        {
            "$match": query
        },
        {
            "$project": {
                "is_deleted": 0
            }
        },
        {
            "$skip": skip
        },
        {
            "$limit": limit
        }
    ]).to_list(length=limit)

    total_users = await db.users.count_documents({})

    total_pages=math.ceil(total_users / limit)


    for user in users:
        user["_id"] = str(user["_id"])

        if "anchor_id" in user:
            user["anchor_id"] = str(user["anchor_id"])

        if "created_at" in user:
            user["created_at"] = user["created_at"].isoformat()

        if "updated_at" in user:
            user["updated_at"] = user["updated_at"].isoformat()


    response_status = True
    if page>total_pages or len(users)<1:
        # print("Less than 1" if len(users)<1 or "0")
        print("Condition hit")
        response_status=False

    return JSONResponse(
    content={
        "message": "Users fetched successfully" if response_status else "No users fetched",
        "data": users,
        "page_info":{"page": page,
        "limit": limit,
        "total_pages":total_pages,
        "total_data": total_users,
    }},
    status_code=status.HTTP_200_OK
)

async def get_admins_list(
    request: Request,
    page: int
):
    requested_role = request.state.role
    limit =10
    if requested_role!=config.AdminRole.SUPER_ADMIN.value:
        return JSONResponse(
            content={"message": "Forbidden access!"},
            status_code=status.HTTP_403_FORBIDDEN
        )

    db = request.app.state.mongo_db

    filters = dict(request.query_params)
    # Remove pagination parameters
    filters.pop("page", None)
    

    query = {}

    # Build filters here
    for filter, filter_val in filters.items():

        query[filter] = {
            "$regex": f"^{filter_val}",
            "$options": "i"
        }

    skip = (page - 1) * limit

    admins = await (
        db.admins
        .find(
            query,
            {
                "_id": 0,
            }
        )
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total_pages = math.ceil(len(admins) / limit)
    return {
        "data": admins,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records":  len(admins),
            "total_pages":total_pages
        }
    }


async def get_anchors(request: Request,page:int=1):

    limit=10
    requester_role = request.state.role

    if requester_role not in ('ADMIN','SUPER_ADMIN'):
        return JSONResponse(
            content={
                "message": "Forbidden access !",
                "role": requester_role
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    db = request.app.state.mongo_db

    filters = dict(request.query_params)

    query:dict[str, Any] = {
        # "role": "ANCHOR"
    }

    ALLOWED_FILTERS = {
        "anchor_name",
        "anchor_code",
        "login_id",
        "is_active"
    }

    for filter_field, filter_value in filters.items():

        if filter_field not in ALLOWED_FILTERS:
            continue

        if filter_field == "is_active":
            query[filter_field] = filter_value.lower() == "true"

        else:
            query[filter_field] = {
                "$regex": f"^{filter_value}",
                "$options": "i"
            }

    projection = {
        "$project": {
            "_id": 0,
            "anchor_name": 1,
            "anchor_code": 1,
            "login_id": 1,
            "is_active": 1,
            "role": 1,
            "created_at": {"$toString": "$created_at"},
            "updated_at": {"$toString": "$updated_at"},
            "created_by": {"$toString": "$created_by"},
            "updated_by": {"$toString": "$updated_by"}
        }
    }


    anchor_docs = await (
        db.anchors
        .aggregate([
            {"$match": query},
            projection
        ])
        .to_list(length=None)
    )
    print("Total number of docs",len(anchor_docs))
    total_pages = math.ceil(len(anchor_docs) / limit)

    response_status = True
    if page>total_pages or len(anchor_docs)<1:
        # print("Less than 1" if len(users)<1 or "0")
        print("Condition hit")
        response_status=False

    return JSONResponse(
        content={
            "message": "Anchors fetched successfully" if response_status else "No anchors fetched",
            "data": anchor_docs,
            "page_info":{
            "page":page,
            "limit":limit,
            "total_pages":total_pages,
            "total_records":len(anchor_docs),
           }
        },
        status_code=status.HTTP_200_OK
    )