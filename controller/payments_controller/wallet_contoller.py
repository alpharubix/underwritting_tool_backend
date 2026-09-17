import json
from datetime import datetime, timezone

from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from config.config import AnchorRole,AllowedService

async def get_service_balance(request: Request,service:str):
    try:
        user_id = request.state.user_id
        user_role =  request.state.role

        requester_body =  await request.json()

        if user_role in (AnchorRole.ANCHOR.value,AnchorRole.SUPER_ANCHOR.value):
            if not requester_body.get("user_id"):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "user_id is required","data": None})
            user_id = requester_body.get("user_id")

        if service not in (AllowedService.BSA.value,AllowedService.GST.value,AllowedService.ITR.value,AllowedService.CIBIL.value):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Invalid service","data": None})

        wallets_collection = request.app.state.mongo_db["wallets"]

        wallet_document = await wallets_collection.find_one(
            {
                "user_id": user_id,
                "service": service,
            },
            {
                "_id": 0,
                "user_id": 1,
                "service": 1,
                "available_balance": 1,
                "reserved_balance": 1,
            },
        )

        if not wallet_document:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Wallet balance fetched successfully",
                    "data": {
                        "service": service,
                        "is_balance_available" :False,
                        "total_balance": 0,
                    },
                },
            )

        available_balance = wallet_document.get(
            "available_balance",
            0,
        )

        reserved_balance = wallet_document.get(
            "reserved_balance",
            0,
        )

        actual_available_balance = available_balance - reserved_balance


        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Wallet balance fetched successfully",
                "data": {
                    "user_id": user_id,
                    "service": service,
                    "is_balance_available" : True if actual_available_balance > 0 else False,
                    "available_balance": available_balance
                },
            },
        )

    except json.JSONDecodeError as err:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid request body","data": None},
        )
    except Exception as e:
        # logger.exception("Unable to fetch wallet balance")
        print(e)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Unable to fetch wallet balance",
                "data": None,
            },
        )


async def reserve_service_balance(
    request: Request,
    service: str,
    user_id: str,
    amount: int,
    reference_id: str,
):
    try:
        wallets_collection = request.app.state.mongo_db["wallets"]


        now = datetime.now(timezone.utc)

        result = await wallets_collection.update_one(
            {
                "user_id": user_id,
                "service": service,
            },
            {
                "$inc": {
                    "available_balance": -amount,
                    "reserved_balance": amount,
                },
                "$set": {
                    "updated_at": now,
                },
            },
        )

        if result.modified_count == 0:
            wallet = await wallets_collection.find_one(
                {
                    "user_id": user_id,
                    "service": service,
                },
                {
                    "_id": 0,
                    "available_balance": 1,
                },
            )

            if not wallet:
                return {
                    "success": False,
                    "message": "Wallet not found",
                    "data": None,
                }

            return {
                "success": False,
                "message": "Insufficient wallet balance",
                "data": {
                    "available_balance": wallet.get(
                        "available_balance",
                        0,
                    ),
                },
            }

        return {
            "success": True,
            "message": "Balance reserved successfully",
            "data": {
                "reference_id": reference_id,
                "service": service,
                "reserved_amount": amount,
            },
        }

    except Exception:
        # logger.exception("Unable to reserve wallet balance")

        return {
            "success": False,
            "message": "Unable to reserve wallet balance",
            "data": None,
        }


async def consume_reserved_balance(
    database,
    service: str,
    user_id: str,
    amount: int,
    reference_id: str,
):
    try:
        wallets_collection = database.wallets

        now = datetime.now(timezone.utc)

        result = await wallets_collection.update_one(
            {
                "user_id": user_id,
                "service": service,
                "reserved_balance": {
                    "$gte": amount
                },
            },
            {
                "$inc": {
                    "reserved_balance": -amount,
                },
                "$set": {
                    "updated_at": now,
                },
            },
        )

        if result.modified_count == 0:
            return {
                "success": False,
                "message": "Reserved balance not found",
                "data": None,
            }

        return {
            "success": True,
            "message": "Reserved balance consumed successfully",
            "data": {
                "reference_id": reference_id,
                "consumed_amount": amount,
            },
        }

    except Exception:
        # logger.exception("Unable to consume reserved balance")

        return {
            "success": False,
            "message": "Unable to consume reserved balance",
            "data": None,
        }


async def release_reserved_balance(
    database,
    service: str,
    user_id: str,
    amount: int,
    reference_id: str,
):
    try:
        wallets_collection = database.wallets

        now = datetime.now(timezone.utc)

        result = await wallets_collection.update_one(
            {
                "user_id": user_id,
                "service": service,
                "reserved_balance": {
                    "$gte": amount
                },
            },
            {
                "$inc": {
                    "available_balance": amount,
                    "reserved_balance": -amount,
                },
                "$set": {
                    "updated_at": now,
                },
            },
        )

        if result.modified_count == 0:
            return {
                "success": False,
                "message": "Reserved balance not found",
                "data": None,
            }

        return {
            "success": True,
            "message": "Reserved balance released successfully",
            "data": {
                "reference_id": reference_id,
                "released_amount": amount,
            },
        }

    except Exception:
        return {
            "success": False,
            "message": "Unable to release reserved balance",
            "data": None,
        }
