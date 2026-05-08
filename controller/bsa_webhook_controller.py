import httpx
from datetime import datetime, timezone
import os
import dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from config.config import SCOREME_MERGE_URL
from services.scoreme_service import create_bsa_ref_document

dotenv.load_dotenv()

async def fetch_and_save_bank_report(db, user_id, reference_id, json_url):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(json_url, timeout=60.0, headers={
                "clientId": os.getenv("CLIENT_ID"),
                "clientSecret": os.getenv("CLIENT_SECRET")
            })

        if response.status_code == 200:
            raw_json = response.json()
            scoreme_data = raw_json.get("Data", {})

            account_details = scoreme_data.get("Account Details", {})
            bank_statements = scoreme_data.get("Bank Statement", [])

            period_str = account_details.get("Period", "")
            from_date = None
            to_date = None
            if " to " in period_str:
                parts = period_str.split(" to ")
                from_date = datetime.strptime(parts[0].strip(), "%d-%m-%Y")
                to_date = datetime.strptime(parts[1].strip(), "%d-%m-%Y")

            for txn in bank_statements:
                txn["Debit"] = float(txn.get("Debit", 0) or 0)
                txn["Credit"] = float(txn.get("Credit", 0) or 0)

            analysis_metadata = {k: v for k, v in raw_json.items() if k != "Data"}
            analysis_metadata["Data"] = {
                k: v for k, v in scoreme_data.items()
                if k not in ["Bank Statement", "Account Details"]
            }

            for entry in analysis_metadata.get("Data", {}).get("Summary Of Debit And Credit", []):
                month_str = entry.get("month", "")
                if month_str:
                    try:
                        entry["parsedMonthDate"] = datetime.strptime("01 " + month_str, "%d %b %Y")
                    except ValueError:
                        pass

            await db["bsa_merged_bankstatements"].update_one(
                {
                    "user_id": user_id,
                },
                {
                    "$set": {
                        "user_id": user_id,
                        "last_merged_reference_id": reference_id,  # always update to latest
                        "from_date": from_date,
                        "to_date": to_date,
                        "account_details": account_details,
                        "bank_statments": bank_statements,
                        "analysis_metadata": analysis_metadata,
                        "updated_at": datetime.now(timezone.utc),
                        "source_url": json_url,
                        "status": "ACTIVE",
                    },
                    "$addToSet": {
                        "merged_reference_id": reference_id  # appends, no duplicates
                    },
                    "$setOnInsert": {
                        # created_at only set once when document is first created
                        "created_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True
            )

            print(f"SUCCESS: Report stored/updated for user {user_id}, reference_id {reference_id}")

            # Mark this reference_id as consumed in bsa_reference
            await db['bsa_reference'].update_one(
                {"reference_id": reference_id},
                {
                    "$set": {
                        "is_consumed": True,
                        "consumed_at": datetime.now(timezone.utc),
                    }
                }
            )
            return True

        else:
            print(f"FAILED: ScoreMe status {response.status_code}")
            # Fixed — filter was missing before
            await db['bsa_reference'].update_one(
                {"reference_id": reference_id},
                {
                    "$set": {
                        "is_consumed": False,
                        "consumed_at": datetime.now(timezone.utc),
                    }
                }
            )
            return False

    except Exception as e:
        print(f"ERROR in fetch_and_save_bank_report: {e}")
        return False



async def is_reference_id_mergable(
    user_id: str,
    reference_id: str,
    json_url: str,
    mongodb_connection: AsyncIOMotorClient
):
    try:
        doc = await mongodb_connection["bsa_merged_bankstatements"].find_one(
            {"user_id": user_id, "status": "ACTIVE"},
            sort=[("created_at", -1)]
        )

        if not doc:
            return "NO_EXISTING_DOC"

        return "MERGABLE"

    except Exception as e:
        print(f"ERROR in is_reference_id_mergable: {e}")
        raise e





async def merge_reference_ids(
    user_id: str,
    reference_ids: list,
    mongodb_connection: AsyncIOMotorClient
):
    request_initiated_time = datetime.now(timezone.utc)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=SCOREME_MERGE_URL,
            timeout=60.0,
            headers={
                "clientId": os.getenv("CLIENT_ID"),
                "clientSecret": os.getenv("CLIENT_SECRET")
            },
            json={"referenceIds": reference_ids}
        )

    if response.status_code != 200:
        raise Exception(f"Merge API failed: {response.text}")

    scoreme_response = response.json()

    new_reference_id = scoreme_response.get("data", {}).get("referenceId")
    response_message = scoreme_response.get("responseMessage")
    response_code = scoreme_response.get("responseCode")

    await create_bsa_ref_document(
        user_id=user_id,
        reference_id=new_reference_id,
        input_data=reference_ids,
        bsa_request_status="Submitted",
        bsa_request_initiated_time=request_initiated_time,
        bsa_request_response_message=response_message,
        bsa_request_response_code=response_code,
        mongobd_connection=mongodb_connection,
        is_merge_request=True,
        merge_request_status="PENDING"
    )

    return new_reference_id












