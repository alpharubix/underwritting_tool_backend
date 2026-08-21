import math
from typing import Any

from fastapi import Request,Header
from starlette.responses import JSONResponse
from starlette import status as status




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


    total_anchors = await db.anchors.count_documents({})

    anchor_docs = await (
        db.anchors
        .aggregate([
            {"$match": query},
            projection
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

