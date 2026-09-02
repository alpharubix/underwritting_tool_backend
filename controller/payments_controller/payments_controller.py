import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone
import dotenv
import httpx
import math
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
import json

from config.config import RAZORPAY_CREATE_ORDERS_URL, AnchorRole, AllowedService, PaymentStatus, WalletStatus

dotenv.load_dotenv()

async def get_create_order(request: Request):
    try:
        input_body = await request.json()

        amount = input_body.get("amount")
        currency = input_body.get("currency")
        service = input_body.get("service")
        user_role = request.state.role
        user_id =  request.state.user_id


        if user_role in (AnchorRole.ANCHOR.value, AnchorRole.SUPER_ANCHOR.value):#In this case anchor is initiating the payment behalf of teh customer
            if not input_body.get("user_id") : #guard condition for anchor access levels
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message":"user id is required","data":None})
            user_id = input_body.get("user_id")
        if amount is None or not currency or not service:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message":"Incorrect payload","data":None})

        if service not in (AllowedService.BSA.value, AllowedService.GST.value, AllowedService.ITR.value,AllowedService.CIBIL.value):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message":"Service not supported","data":None})

        url = RAZORPAY_CREATE_ORDERS_URL

        receipt = str(uuid.uuid4())

        payload = {
            "amount": amount*100,
            "currency": currency,
            "receipt": receipt,
            "notes":{
                "user_id": user_id,
                "service": service
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                auth=(
                    os.getenv("RAZORPAY_KEY_ID"),
                    os.getenv("RAZORPAY_KEY_SECRET"),
                ),
            )
        if response.status_code == 200:
            razor_pay_order = response.json()

            order_document = {
                **razor_pay_order,

                # Internal references
                "user_id": user_id,
                "service": service,

                # Payment tracking
                "payment_status":PaymentStatus.PENDING.value,
                "razorpay_payment_id": None,
                "razorpay_signature": None,
                "signature_verified": False,

                # Internal timestamps
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
            }

            orders_response =  await request.app.state.mongo_db["orders"].insert_one(order_document)
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message":"order created","data":{"user_id":user_id,"order_id":razor_pay_order.get("id"),"amount":razor_pay_order.get("amount"),"currency":razor_pay_order.get("currency"),"service":service}})
        else:
            return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"message":"service unavailable","data":None})
    except json.JSONDecodeError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "invalid body","data":None})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message":"Internal server error","data":None})



async def get_validate_payment(request: Request):
    try:
        request_body = await request.json()

        razorpay_payment_id = request_body.get("razorpay_payment_id")
        razorpay_order_id = request_body.get("razorpay_order_id")
        razorpay_signature = request_body.get("razorpay_signature")

        authenticated_user_id = request.state.user_id
        user_role = request.state.role

        # -----------------------------------------
        # 1. Validate request fields
        # -----------------------------------------

        if not all([
            razorpay_payment_id,
            razorpay_order_id,
            razorpay_signature,
        ]):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Payment details are required",
                    "data": None,
                },
            )

        # -----------------------------------------
        # 2. Resolve customer/user
        # -----------------------------------------

        user_id = authenticated_user_id

        if user_role in (
            AnchorRole.ANCHOR.value,
            AnchorRole.SUPER_ANCHOR.value,
        ):
            user_id = request_body.get("user_id")

            if not user_id:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "message": "User id is required",
                        "data": None,
                    },
                )

        db = request.app.state.mongo_db

        orders_collection = db.orders
        payments_collection = db.payments
        wallets_collection = db.wallets

        # -----------------------------------------
        # 3. Find internal order
        # -----------------------------------------

        order_document = await orders_collection.find_one({
            "id": razorpay_order_id,
        })

        if not order_document:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid order id",
                    "data": None,
                },
            )

        # -----------------------------------------
        # 4. Make sure order belongs to customer
        # -----------------------------------------

        if order_document.get("user_id") != user_id:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "message": "You are not authorized for this order",
                    "data": None,
                },
            )

        # -----------------------------------------
        # 5. Verify Razorpay signature
        # -----------------------------------------

        signature_payload = (
            f"{razorpay_order_id}|{razorpay_payment_id}"
        )

        generated_signature = hmac.new(
            os.getenv("RAZORPAY_KEY_SECRET").encode("utf-8"),
            signature_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            generated_signature,
            razorpay_signature,
        ):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid payment signature",
                    "data": None,
                },
            )

        # -----------------------------------------
        # 6. Start MongoDB transaction
        # -----------------------------------------

        async with await request.app.state.mongo_db.client.start_session() as session:

            async with session.start_transaction():

                # -----------------------------------------
                # 6.1 Check whether payment already exists
                # -----------------------------------------

                existing_payment = await payments_collection.find_one(
                    {
                        "razorpay_payment_id": razorpay_payment_id,
                    },
                    session=session,
                )

                if existing_payment:
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "message": "Payment already validated",
                            "data": {
                                "payment_id": razorpay_payment_id,
                            },
                        },
                    )

                now = datetime.now(timezone.utc)

                # -----------------------------------------
                # 6.2 Get service
                # -----------------------------------------

                service = order_document.get("service")
                amount = order_document.get("amount")

                # -----------------------------------------
                # 6.3 Create payment
                # -----------------------------------------

                payment_document = {
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_signature": razorpay_signature,

                    "user_id": user_id,
                    "service": service,

                    "amount": amount,
                    "currency": order_document["currency"],

                    "payment_status": PaymentStatus.AUTHORIZED.value,
                    "signature_verified": True,

                    "wallet_status": WalletStatus.PENDING.value,

                    "created_at": now,
                    "updated_at": None,
                }

                await payments_collection.insert_one(
                    payment_document,
                    session=session,
                )

                # -----------------------------------------
                # 6.4 Update order
                # -----------------------------------------

                order_update_result = await orders_collection.update_one(
                    {
                        "id": razorpay_order_id,
                        "user_id": user_id,
                    },
                    {
                        "$set": {
                            "payment_status": PaymentStatus.AUTHORIZED.value,
                            "razorpay_payment_id": razorpay_payment_id,
                            "signature_verified": True,
                            "updated_at": now,
                        },
                    },
                    session=session,
                )

                # -----------------------------------------
                # 6.5 Atomic wallet credit
                # -----------------------------------------

                await wallets_collection.update_one(
                    {
                        "user_id": user_id,
                        "service": service,
                    },
                    {
                        "$inc": {
                            "available_balance": math.ceil(amount/ 100),
                        },
                        "$set": {
                            "updated_at": now,
                        },
                        "$setOnInsert": {
                            "user_id": user_id,
                            "service": service,
                            "reserved_balance": 0,
                            "created_at": now,
                        },
                    },
                    upsert=True,
                    session=session,
                )

                # -----------------------------------------
                # 6.6 Mark wallet as credited
                # -----------------------------------------

                await payments_collection.update_one(
                    {
                        "razorpay_payment_id": razorpay_payment_id,
                    },
                    {
                        "$set": {
                            "wallet_status":WalletStatus.SUCCESS.value,
                            "updated_at": now,
                        },
                    },
                    session=session,
                )

        # -----------------------------------------
        # 7. Success
        # -----------------------------------------

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Payment validated successfully",
                "data": {
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_order_id": razorpay_order_id,
                    "payment_status": "VERIFIED",
                },
            },
        )

    except Exception as e:

        print(e)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Unable to validate payment",
                "data": None,
            },
        )

