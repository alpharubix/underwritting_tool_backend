from datetime import datetime, timedelta
import math
from typing import Any

from bson import ObjectId
from fastapi import Request,Header
from starlette.responses import JSONResponse
from starlette import status as status



ALLOWED_ROLES={"SUPER_ANCHOR","ANCHOR"}

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
        "is_active",
        "created_"
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


    total_anchors = await db.anchors.count_documents(query)
    skip = (page-1)*limit
    anchor_docs = await (
        db.anchors
        .aggregate([
            {"$match": query},
            projection,
            {"$skip": skip},
            {"$limit": limit}
        ])
        .to_list(length=None)
    )

    if not anchor_docs:
        return JSONResponse(
            content={"message": "No anchors found !"},
            status_code=status.HTTP_404_NOT_FOUND
        )

    total_pages=math.ceil(total_anchors / limit)

    response_status = True
    if page>total_pages or len(anchor_docs)<1:
        # print("Less than 1" if len(users)<1 or "0")
        print("Condition hit")
        response_status=False

    return JSONResponse(
        content={
            "message": "Anchors fetched successfully" if response_status else "No anchors fetched",
            "page":page,
            "limit":limit,
            "total_pages":total_pages,
            "total_records":total_anchors,
            "role": requester_role,
            "data": anchor_docs
        },
        status_code=status.HTTP_200_OK
    )

async def update_anchor(request:Request,login_id:str):
    requester_role=request.state.role

    #who can update - super admins and admins
    if requester_role not in {"SUPER_ADMIN","ADMIN"}:
        return JSONResponse(
            content={"message":"Forbidden access !"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    else:
        db = request.app.state.mongo_db
        body = await request.json()

        target_anchor = await db.anchors.find_one({"login_id":login_id})
        if target_anchor is None:
            return JSONResponse(
                content={"message":"Anchor not found"},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        body.pop("created_at", None)
        body.pop("created_by", None)
        body.pop("_id", None)

        body["modified_at"] = datetime.isoformat(datetime.now())
        body["modified_by"] = request.state.user_id

        old_data = {
            key: (
                target_anchor.get(key).isoformat()
                if isinstance(target_anchor.get(key), datetime)
                else target_anchor.get(key)
            )
            for key in body.keys()
        }

        new_data = {
            key: (
                value.isoformat()
                if isinstance(value, datetime)
                else value
            )
            for key, value in body.items()
        }

        anchor_result = await db.anchors.update_one(
            {"_id":target_anchor["_id"]},
            {"$set":new_data}
            )
        if anchor_result.modified_count==0:
            return JSONResponse(
                content={"message":"Failed to update"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        final_updated_data = {
                "login_id":login_id,
                f"old data":old_data,
                f"updated data":new_data
            }
        return JSONResponse(
                content={"message":f"Admin with the login-id : {login_id} has been updated successfully",**final_updated_data},
                status_code=status.HTTP_200_OK
            )

async def delete_anchor(request:Request,login_id:str):
    requester_role = request.state.role

    if requester_role not in {"ADMIN","SUPER_ADMIN","SUPER_ANCHOR"} :
        return JSONResponse(
            content={"Cant delete ! Forbidden access"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    db = request.app.state.mongo_db
    target_anchor = await db.anchors.find_one({"login_id":login_id})

    if target_anchor is None:
        return JSONResponse(
            content={"message":"Anchor not found for the deletion"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    else:
        anchor_delete = await db.anchors.delete_one({
            "login_id":login_id,
            "role":"ANCHOR"
        })
        if anchor_delete.deleted_count == 0:
            return JSONResponse(
                content={"message":"Couldnt delete | Internal Server Error"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return JSONResponse(
            content={"message":"Anchor deleted successfully !"},
            status_code=status.HTTP_410_GONE
            )


async def get_users(request:Request,page:int=1):
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
    print(requester_role)
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

async def get_users_per_anchor(request:Request,page:int):
    requester_role = request.state.role
    """IF SUPER-ADMIN IS LOGGING, THERE IS SEPERATE ENDPOINT - since this is endpoint grouping users under one anchor 
        super-admin endpoint is : /users
    """
    if requester_role not in ALLOWED_ROLES:
        return JSONResponse(
            content={"message":"Forbidden access !"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    else:
        """
        in the users docs , you have anchor id, as object id - > 
        You have object id of the anchor in the request , so target_anchor can hold that values
        """
        target_anchor=ObjectId(request.state.user_id)
        db = request.app.state.mongo_db
        limit = 10
        skip = (page - 1) * limit
        projection ={
            "_id":0,
            "anchor_id":0
        }

        users = await db.users.find({"anchor_id":target_anchor},projection).skip(skip).limit(limit).to_list(length=limit)

        for user in users: #For converting "datetime" fields
            if user.get("created_at"):
                user["created_at"]=user["created_at"].isoformat()

            if user.get("updated_at"):
                user['updated_at']=user["updated_at"].isoformat()
            else:
                #future expansion (for other fields which are not str)
                continue

        if not users:
            return JSONResponse(
                content={"message":"No users found for this anchor"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        total_records = await db.users.count_documents({
            "anchor_id": target_anchor
        })
        total_pages = math.ceil(len(total_records) / limit)

        return JSONResponse(
            content={
                "message":"Users fetched successfully for the anchor",
                "data":users,
                "page_info":{
                            "page":page,
                            "limit":limit,
                            "total_pages":total_pages,
                            "total_records":len(users),
                }
            },
            status_code=status.HTTP_200_OK
        )




# async def anchor_dashboard(
#     request: Request,
#     actor_module: str,
#     page: int = 1,
#     limit: int = 10
# ):
#     requester_role = request.state.role
#     db = request.app.state.mongo_db

#     # PAGINATION VALIDATION
#     if page < 1:
#         return JSONResponse(
#             content={"message": "Page must be greater than 0"},
#             status_code=status.HTTP_400_BAD_REQUEST
#         )

#     if limit < 1 or limit > 100:
#         return JSONResponse(
#             content={"message": "Limit must be between 1 and 100"},
#             status_code=status.HTTP_400_BAD_REQUEST
#         )

#     actor_module = actor_module.lower()
#     print("Actor module received : ",actor_module)

#     # ROLE + MODULE AUTHORIZATION
#     if requester_role == "SUPER_ANCHOR" or requester_role=="SUPER_ADMIN":
#         # Super Anchor can view both anchors and users
#         if actor_module not in {"anchors", "users"}:
#             return JSONResponse(
#                 content={
#                     "message": "Invalid actor module",
#                     "allowed_modules": ["anchors", "users"]
#                 },
#                 status_code=status.HTTP_400_BAD_REQUEST
#             )
#     elif requester_role == "ANCHOR":
#         # Anchor can view users only
#         if actor_module != "users":
#             return JSONResponse(
#                 content={
#                     "message": "Anchors are only allowed to view users !"
#                 },
#                 status_code=status.HTTP_403_FORBIDDEN
#             )

#     else:
#         return JSONResponse(
#             content={
#                 "message": "You are not authorized to access this dashboard !"
#             },
#             status_code=status.HTTP_403_FORBIDDEN
#         )

#     skip = (page - 1) * limit

#     # VIEW ANCHORS
#     if actor_module == "anchors":

#         total_documents = await db.anchors.count_documents({})
#         print("Total docuents: ",total_documents)
#         anchor_docs = await (
#             db.anchors.aggregate([
#                 {
#                     "$set": {
#                         "created_by": {"$toString": "$created_by"},
#                         "modified_by": {"$toString": "$modified_by"}
#                     }
#                 },
#                 {
#                     "$sort": {
#                         "_id": 1
#                     }
#                 },
#                 {
#                     "$skip": skip
#                 },
#                 {
#                     "$limit": limit
#                 },
#                 {
#                     "$unset": [
#                         "_id",
#                         "created_at",
#                         "modified_at"
#                     ]
#                 }
#             ])
#         ).to_list(length=limit)

#         total_pages = (
#             (total_documents + limit - 1) // limit
#             if total_documents > 0
#             else 0
#         )

#         return JSONResponse(
#             content={
#                 "message": "Anchors fetched successfully",
#                 "pagination": {
#                     "page": page,
#                     "limit": limit,
#                     "total_documents": total_documents,
#                     "total_pages": total_pages,
#                     "has_next": page < total_pages,
#                     "has_previous": page > 1
#                 },
#                 "data": anchor_docs
#             },
#             status_code=status.HTTP_200_OK
#         )

#     # VIEW USERS
#     elif actor_module == "users":

#         total_documents = await db.users.count_documents({})

#         user_docs = await (
#             db.users
#             .find({},{"_id":0,"anchor_id":0,"created_at":0,"updated_at":0})
#             .sort("_id", 1)
#             .skip(skip)
#             .limit(limit)
#             .to_list(length=limit)
#         )

#         total_pages = (
#             (total_documents + limit - 1) // limit
#             if total_documents > 0
#             else 0
#         )

#         return JSONResponse(
#             content={
#                 "message": "Users fetched successfully",
#                 "pagination": {
#                     "page": page,
#                     "limit": limit,
#                     "total_documents": total_documents,
#                     "total_pages": total_pages,
#                     "has_next": page < total_pages,
#                     "has_previous": page > 1
#                 },
#                 "data": user_docs
#             },
#             status_code=status.HTTP_200_OK
#         )


# async def get_anchors(request:Request):
#     #super-anchor,anchor
#     requester_role = request.state.role

#     if requester_role!="SUPER_ANCHOR":
#         return JSONResponse(
#             content={"message":"Forbidden access !","role":requester_role},
#             status_code=status.HTTP_403_FORBIDDEN
#         )
#     else:
#         db = request.app.state.mongo_db 
#         projection = {
#             "$project":{
#                 "_id":0,
#                 "anchor_name":1,
#                 "anchor_code":1,
#                 "login_id":1,
#                 "is_active":1,
#                 "role":1,
#                 "created_at":{"$toString":"$created_at"},
#                 "updated_at":{"$toString":"$updated_at"},
#                 "created_by":{"$toString":"$created_by"},
#                 "updated_by":{"$toString":"$updated_by"}
#             }
#         }
#         anchor_docs = await db.anchors.aggregate([
#             {
#                 "$match":{
#                     "role":"ANCHOR"
#                 }
#             },
#             projection
#         ]).to_list(length=None)

#         if not anchor_docs:
#             return JSONResponse(
#                 content={"message":"No anchors fetched !"},
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
#         else:
#             return JSONResponse(
#                 content={"message":"Anchors fetched successfully","role":requester_role,"data":anchor_docs},
#                 status_code=status.HTTP_200_OK
#             )

