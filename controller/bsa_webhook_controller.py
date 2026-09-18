import httpx
from datetime import datetime, timezone
import os
import dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from config.config import SCOREME_MERGE_URL
from services.scoreme_service import create_bsa_ref_document

dotenv.load_dotenv()

async def fetch_and_save_bank_report(db, user_id, reference_id, json_url,reference_doc):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(json_url, timeout=60.0, headers={
                "clientId": os.getenv("CLIENT_ID"),
                "clientSecret": os.getenv("CLIENT_SECRET")
            })

        if response.status_code == 200:
            raw_json = response.json()
            scoreme_data = raw_json.get("Data", {})


            entity_type = reference_doc.get("input_data").get("entityType")

            if entity_type != "Individual":
                account_details = scoreme_data.get("Account Details", {})

                account_details["Bank Name"] = account_details.get("Bank Name", "").split(",")[0]

                account_details["Account Number"] = account_details.get("Account Number", "").split(",")[0]

                account_details["AccountType"] = account_details.get("AccountType", "").split(",")[0]
                print("Non Individual Entity Type")

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
                for entry in analysis_metadata.get("Data", {}).get("Cash Flow", []):
                    month_str = entry.get("MonthYear", "")
                    if month_str:
                        try:
                            entry["parsedMonthDate"] = datetime.strptime("01 " + month_str, "%d %b %Y")
                        except ValueError:
                            pass
                for entry in analysis_metadata.get("Data", {}).get("OverView", []):
                    month_str = entry.get("Month", "")
                    if month_str:
                        try:
                            entry["parsedMonthDate"] = datetime.strptime("01 " + month_str, "%d %b %Y")
                        except ValueError:
                            pass


            else:
                account_details = scoreme_data.get("Account Details", {})

                account_details["Bank Name"] = account_details.get(
                    "BankName", ""
                ).split(",")[0]

                account_details["Account Number"] = account_details.get(
                    "Account No", ""
                ).split(",")[0]

                account_details["AccountType"] = account_details.get(
                    "AccountType", ""
                ).split(",")[0]

                # Remove original fields
                account_details.pop("Account No", None)
                account_details.pop("BankName", None)

                print("Individual Entity Type")

                # if no account number found and entity type is individual
                bank_statements = scoreme_data.get("Bank Statement", [])

                period_str = account_details.get("Period", "")

                from_date = None
                to_date = None

                if " to " in period_str:
                    parts = period_str.split(" to ")

                    from_date = datetime.strptime(
                        parts[0].strip(),
                        "%d-%m-%Y"
                    )

                    to_date = datetime.strptime(
                        parts[1].strip(),
                        "%d-%m-%Y"
                    )

                for txn in bank_statements:
                    if isinstance(txn, dict):
                        txn["Debit"] = float(txn.get("Debit", 0) or 0)
                        txn["Credit"] = float(txn.get("Credit", 0) or 0)

                analysis_metadata = {
                    k: v for k, v in raw_json.items()
                    if k != "Data"
                }

                analysis_metadata["Data"] = {
                    k: v for k, v in scoreme_data.items()
                    if k not in ["Bank Statement", "Account Details"]
                }

                # -----------------------------
                # OVERVIEW
                # -----------------------------
                overview = analysis_metadata.get("Data", {}).get("OverView", {})

                if isinstance(overview, dict):

                    for entry in overview.values():

                        if not isinstance(entry, dict):
                            continue

                        month_str = entry.get("monthYear", "")

                        if month_str:
                            try:
                                entry["parsedMonthDate"] = datetime.strptime(
                                    "01 " + month_str,
                                    "%d %b %Y"
                                )
                            except ValueError:
                                pass

                # -----------------------------
                # EOD ANALYSIS
                # -----------------------------
                eod_analysis = analysis_metadata.get(
                    "Data", {}
                ).get(
                    "Eod analysis", {}
                )

                if isinstance(eod_analysis, dict):

                    eod_month_wise = eod_analysis.get(
                        "EOD MONTH WISE",
                        []
                    )

                    if isinstance(eod_month_wise, list):

                        for entry in eod_month_wise:

                            if not isinstance(entry, dict):
                                continue

                            month_str = entry.get("monthYear", "")

                            if month_str:
                                try:
                                    entry["parsedMonthDate"] = datetime.strptime(
                                        "01 " + month_str,
                                        "%d %b %Y"
                                    )
                                except ValueError:
                                    pass

                            max_eod_date = entry.get("maxEodDate", "")

                            if max_eod_date:
                                try:
                                    entry["parsedMaxEodDate"] = datetime.strptime(
                                        max_eod_date,
                                        "%d-%m-%Y"
                                    )
                                except ValueError:
                                    pass

                            min_eod_date = entry.get("minEodDate", "")

                            if min_eod_date:
                                try:
                                    entry["parsedMinEodDate"] = datetime.strptime(
                                        min_eod_date,
                                        "%d-%m-%Y"
                                    )
                                except ValueError:
                                    pass

                # -----------------------------
                # LOAN TRANSACTIONS
                # -----------------------------
                loan_transactions = analysis_metadata.get(
                    "Data", {}
                ).get(
                    "Loan Transactions",
                    {}
                )

                if isinstance(loan_transactions, dict):

                    summary_loan = loan_transactions.get(
                        "Summary Of Loan Tranx",
                        []
                    )

                    if isinstance(summary_loan, list):

                        for entry in summary_loan:

                            if not isinstance(entry, dict):
                                continue

                            month_str = entry.get("Month", "")

                            if month_str:
                                try:
                                    entry["parsedMonthDate"] = datetime.strptime(
                                        "01 " + month_str,
                                        "%d %b %Y"
                                    )
                                except ValueError:
                                    pass

                    details_loan = loan_transactions.get(
                        "Details Of Loan Transactions",
                        []
                    )

                    if isinstance(details_loan, list):

                        for entry in details_loan:

                            if not isinstance(entry, dict):
                                continue

                            date_str = entry.get("Date", "")

                            if date_str:
                                try:
                                    entry["parsedDate"] = datetime.strptime(
                                        date_str,
                                        "%d-%m-%Y"
                                    )
                                except ValueError:
                                    pass

            await db["bsa_merged_bankstatements"].update_one(
                {"user_id": user_id,
                 "account_details.Account Number": account_details.get("Account Number", "").split(",")[0]},
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
    json_url: str,
    mongodb_connection: AsyncIOMotorClient
):
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

            bank_name = account_details.get("Bank Name", "").split(",")[0]

            account_number = account_details.get("Account Number", "").split(",")[0]


        doc = await mongodb_connection["bsa_merged_bankstatements"].find_one(
            {"user_id": user_id,"account_details.Bank Name":bank_name,"account_details.Account Number":account_number,"status": "ACTIVE"},
            sort=[("created_at", -1)]
        )

        if not doc:
            return "NO_EXISTING_DOC",None

        return "MERGABLE",doc

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

    new_reference_id = scoreme_response.get("data").get("referenceId")
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












