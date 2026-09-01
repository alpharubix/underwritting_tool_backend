from fastapi import HTTPException
from fastapi.requests import Request
from datetime import datetime, timezone
from pymongo import UpdateOne

async def get_save_money(cust_id: str, request: Request, reference_id: str):
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
    
    # Get user selections from save_money collection
    save_money_docs = await db.save_money.find({
        "user_id": cust_id, 
        "reference_id": reference_id
    }).to_list(length=None)
    saved_accounts = {(doc.get("account_number"), doc.get("lender_name")) for doc in save_money_docs}

    save_money_accounts = []

    for account_type, accounts in active_accounts.items():
        if not isinstance(accounts, list):
            continue

        for account in accounts:
            if not account or not any(account.values()):
                continue

            save_money_accounts.append({
                "lender_name": account.get("lender"),
                "account_number": account.get("accountNo"),
                "opened_date": account.get("accountOpenedDate"),
                "current_balance": account.get("currentBalance"),
                "check_box": (account.get("accountNo"), account.get("lender")) in saved_accounts
            })

    return {
        "reference_id": reference_id,
        "accounts": save_money_accounts
    }

async def submit_save_money_selections(cust_id: str, request: Request, reference_id: str, selected_accounts: list[dict]):
    db = request.app.state.mongo_db

    if not selected_accounts:
        await db.save_money.delete_many({"user_id": cust_id, "reference_id": reference_id})
    else:
        keep_conditions = [{"account_number": acc["account_number"], "lender_name": acc["lender_name"]} for acc in selected_accounts]
        await db.save_money.delete_many({
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
            await db.save_money.bulk_write(operations)

    return {"message": "Selections submitted successfully"}