import httpx
from database.db import get_mongo_db
from datetime import datetime, timezone
import os

async def start_reconciliation(reference_id: str, json_url: str):

    db = get_mongo_db()
    
    # 1. Download the Report from ScoreMe
    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "clientId": os.getenv("SCOREME_CLIENT_ID"),
                "clientSecret": os.getenv("SCOREME_CLIENT_SECRET"),
                "Content-Type": "application/json"
            }
            response = await client.get(json_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            scoreme_report = response.json()
        except Exception as e:
            print(f"Failed to download ScoreMe report: {e}")
            return False

    # 2. Get your "Source of Truth" from MongoDB
    internal_record = await db.bsa_uploads.find_one({"referenceId": reference_id})
    if not internal_record:
        print(f"No internal record found for {reference_id}")
        return False

    # Your data (usually lowercase from your own extraction logic)
    raw_transactions = internal_record.get("extraction", {}).get("rawTransactions", [])
    
    # 3. Get ScoreMe's list of transactions
    # We dig deep into the report structure provided in your sample
    report_data = scoreme_report.get("data", {}).get("report", {})
    external_transactions = report_data.get("allTransactions", [])

    # 4. The Matching Logic (Strong Version)
    matches = 0
    for local_tx in raw_transactions:
        # Your DB keys (Assuming lowercase)
        local_amt = str(local_tx.get('amount', '0')).replace(',', '').strip()
        local_date = str(local_tx.get('date', '')).strip()
        
        for score_tx in external_transactions:
            # ScoreMe keys (Note the CAPITAL letters 'Amount' and 'Date')
            score_amt = str(score_tx.get('Amount', '0')).replace(',', '').strip()
            score_date = str(score_tx.get('Date', '')).strip()
            
            # Match on both Date and Amount
            if local_amt == score_amt and local_date == score_date:
                matches += 1
                break # Move to next local transaction once a match is found
    
    # 5. Update MongoDB with the findings
    await db.bsa_uploads.update_many(
        {"referenceId": reference_id},
        {"$set": {
            "status": "reconciled",
            "reconciliation": {
                "totalMatches": matches,
                "reconciledAt": datetime.now(timezone.utc)
            }
        }}
    )
    
    return f"Reconciliation successful. Matches: {matches}"



async def perform_verification(db, reference_id: str, scoreme_report_json: dict):
    # 1. Fetch your local "Source of Truth"
    local_record = await db.bsa_raw_extractions.find_one({"reference_id": reference_id})
    if not local_record:
        return "Local record not found"

    # 2. Extract ScoreMe's list (Following their deep structure)
    # Based on Mahajan sample: data -> report -> allTransactions
    sm_transactions = scoreme_report_json.get("data", {}).get("report", {}).get("allTransactions", [])
    
    local_transactions = local_record.get("bank_statement", [])
    
    # 3. Matching Logic
    # We use a set of strings for "Amount|Date" to find mismatches quickly
    matched_rows = []
    missing_in_sm = []
    
    for local_tx in local_transactions:
        # We look for a match in ScoreMe's list
        found = False
        for sm_tx in sm_transactions:
            # Check Date, Debit, and Credit (Must be exact string match)
            if (local_tx["Date"] == sm_tx.get("Date") and 
                local_tx["Debit"] == sm_tx.get("Debit") and 
                local_tx["Credit"] == sm_tx.get("Credit")):
                matched_rows.append(local_tx)
                found = True
                break
        
        if not found:
            missing_in_sm.append(local_tx)

    # 4. Final Analysis
    matched_count = len(matched_rows)
    local_count = len(local_transactions)
    sm_count = len(sm_transactions)
    
    v_status = "matched" if matched_count == local_count else "mismatch"
    if local_record["extraction_status"] == "skipped_scan":
        v_status = "skipped_scan"

    # 5. Atomic Update
    await db.bsa_raw_extractions.update_one(
        {"reference_id": reference_id},
        {"$set": {
            "status": "verified",
            "scoreme_count": sm_count,
            "matched_count": matched_count,
            "missing_in_scoreme": missing_in_sm,
            "verification_status": v_status,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Also save the raw report for audit
    await db.bsa_scoreme_reports.insert_one({
        "reference_id": reference_id,
        "report": scoreme_report_json,
        "received_at": datetime.now(timezone.utc)
    })
    
    return v_status