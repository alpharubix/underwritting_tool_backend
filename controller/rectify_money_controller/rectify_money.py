from fastapi import HTTPException
from fastapi.requests import Request
from datetime import datetime, timezone
from pymongo import UpdateOne

def get_dpd_days(payment_status: dict) -> list[int]:
    dpd_days = []
    for month, value in payment_status.items():
        if month == "year":
            continue
        if not value:
            continue
        dpd_value = value.split("/")[0]
        if not dpd_value.endswith("+"):
            continue
        try:
            days = int(dpd_value[:-1])
        except ValueError:
            continue
        if days > 0:
            dpd_days.append(days)
    return dpd_days

async def get_rectify_money(cust_id: str, request: Request, reference_id: str):
    db = request.app.state.mongo_db
    report = await db.cibil_report.find_one({
        "user_id": cust_id,
        "reference_id": reference_id
    })
    if not report:
        raise HTTPException(
            status_code=404,
            detail="CIBIL report not found for the user"
        )
    equifax = report.get("cibil_report", {}).get("EquifaxRetail", {})
    active_accounts = equifax.get("accountSummary", {}).get("activeAccounts", {})
    repayment_tracks = equifax.get("activeAccountRepaymentTrack", [])
    
    # Get user selections from rectify_money collection
    rectify_money_docs = await db.rectify_money.find({
        "user_id": cust_id, 
        "reference_id": reference_id
    }).to_list(length=None)
    saved_accounts = {(doc.get("account_number"), doc.get("lender_name")) for doc in rectify_money_docs}

    rectify_accounts = []

    for account_type, accounts in active_accounts.items():
        if not isinstance(accounts, list):
            continue
        for account in accounts:
            if not account:
                continue
            overdue = account.get("overdue")
            try:
                overdue_amount = float(overdue or 0)
            except (TypeError, ValueError):
                continue
            if overdue_amount <= 0:
                continue
            account_no = account.get("accountNo")
            account_repayment_tracks = [
                track for track in repayment_tracks
                if track.get("accountNo") == account_no
            ]
            dpd_days = []

            for track in account_repayment_tracks:
                payment_statuses = track.get("paymentStatus", [])
                for payment_status in payment_statuses:
                    dpd_days.extend(get_dpd_days(payment_status))

            average_dpd = sum(dpd_days) / len(dpd_days) if dpd_days else 0
            
            rectify_accounts.append({
                "lender_name": account.get("lender"),
                "account_number": account_no,
                "opened_date": account.get("accountOpenedDate"),
                "overdue_amount": overdue_amount,
                "average_dpd": round(average_dpd, 2),
                "check_box": (account_no, account.get("lender")) in saved_accounts
                # "dpd": account_repayment_tracks
            })
    return {
        "reference_id": reference_id,
        "accounts": rectify_accounts
    }

async def submit_rectify_money_selections(cust_id: str, request: Request, reference_id: str, selected_accounts: list[dict]):
    db = request.app.state.mongo_db

    if not selected_accounts:
        await db.rectify_money.delete_many({"user_id": cust_id, "reference_id": reference_id})
    else:
        keep_conditions = [{"account_number": acc["account_number"], "lender_name": acc["lender_name"]} for acc in selected_accounts]
        await db.rectify_money.delete_many({
            "user_id": cust_id,
            "reference_id": reference_id,
            "$nor": keep_conditions
        })

        now = datetime.now(timezone.utc).isoformat()
        operations = [
            UpdateOne(
                {
                    "user_id": cust_id,
                    "reference_id": reference_id,
                    "account_number": acc["account_number"],
                    "lender_name": acc["lender_name"]
                },
                {
                    "$set": {
                        "interested": True,
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            for acc in selected_accounts
        ]
        if operations:
            await db.rectify_money.bulk_write(operations)

    return {"message": "Selections submitted successfully"}