from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status

async def request_loan(request: Request):
    db = request.app.state.mongo_db

    body = await request.json()

    cust_id = body.get("cust_id")
    loan_type = body.get("loan_type")
    amount = body.get("amount")

    if cust_id is None or loan_type is None or amount is None:
        return JSONResponse(
            content={"message": "Please fill all the fields"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if amount <= 0:
        return JSONResponse(
            content={"message": "Amount must be greater than 0"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    access_money_result = await db.access_money.insert_one(
        {
            "user_id": cust_id,
            "loan_type": loan_type,
            "amount": amount
        }
    )

    if not access_money_result.inserted_id:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"}
        )

    return JSONResponse(
        content={"message": "Loan Request accepted successfully"},
        status_code=status.HTTP_202_ACCEPTED
    )