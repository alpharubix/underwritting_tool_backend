from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from starlette import status
from config.config import AllowedService, WalletStatus, ServiceRequestStatus, UpstreamStatus

SERVICE_REQUEST_COLLECTION = "service_requests"


def _now():
    return datetime.now(timezone.utc)


def _validate_service(service: str) -> str:
    allowed_services = {allowed_service.value for allowed_service in AllowedService}
    normalized_service = service.upper() if isinstance(service, str) else service

    if normalized_service not in allowed_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid service",
                "allowed_services": sorted(allowed_services),
            },
        )

    return normalized_service




async def create_service_request(
    database: AsyncIOMotorDatabase,
    user_id: str,
    requested_by:str,
    service: str,
    amount: int,
    reference_id: str,
):
    service = _validate_service(service)

    if not user_id:
        return {"message": "User id is required"}

    if amount <= 0:
        return {"message": "Amount is required"}

    reference_id = reference_id
    now = _now()
    service_requests_collection = database[SERVICE_REQUEST_COLLECTION]

    service_request = {
        "reference_id": reference_id,
        "user_id": user_id,
        "requested_by": requested_by,
        "service": service,
        "amount": amount,
        "wallet_status":WalletStatus.RESERVED.value,
        "service_status": ServiceRequestStatus.SERVICE_STATUS_PROCESSING.value,
        "upstream_status": UpstreamStatus.UPSTREAM_STATUS_ACCEPTED.value,
        "created_at": now,
        "updated_at": None,
    }

    insert_result = await service_requests_collection.insert_one(service_request)

    return {"message":"created successfully"}


async def update_service_request(
    database: AsyncIOMotorDatabase,
    reference_id: str,
    fields: dict[str, Any],
):
    if not reference_id:
        return {"message": "Reference id is required"}

    if not fields:
        return {"message": "Fields is required"}

    service_requests_collection = database[
        SERVICE_REQUEST_COLLECTION
    ]

    # Always update updated_at automatically
    fields["updated_at"] = _now()

    updated_document = await service_requests_collection.find_one_and_update(
        {
            "reference_id": reference_id,
            "service_status": ServiceRequestStatus.SERVICE_STATUS_PROCESSING.value,
        },
        {
            "$set": fields,
        },
        return_document=ReturnDocument.AFTER,
    )

    if not updated_document:
       return {"message": "Service request was not updated"}

    return {"message":"updated successfully"}


async def get_service_request(
    database: AsyncIOMotorDatabase,
    filters: dict[str, Any],
) -> dict[str, Any]:

    if not filters:
        return None

    service_requests_collection = database[
        SERVICE_REQUEST_COLLECTION
    ]

    service_request = await service_requests_collection.find_one(
        filters,
        {"created_at":0,"updated_at":0}
    )

    if not service_request:
        return None

    return service_request
