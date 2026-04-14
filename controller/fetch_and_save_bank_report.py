import httpx
from datetime import datetime, timezone
import os
import dotenv

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
            analysis_metadata["Data"] = {k: v for k, v in scoreme_data.items() 
                                         if k not in ["Bank Statement", "Account Details"]}

            # 5. Build the Optimized Document
            optimized_document = {
                "user_id": user_id,
                "reference_id": reference_id,
                "from_date": from_date,           # NEW: Searchable Date
                "to_date": to_date,               # NEW: Searchable Date
                "account_details": account_details,  
                "bank_statments": bank_statements,    
                "analysis_metadata": analysis_metadata, 
                "created_at": datetime.now(timezone.utc),
                "source_url": json_url
            }

            
            await db["bankstatementreport"].insert_one(optimized_document)
            print(f"SUCCESS: Optimized report stored for user {user_id}")
            return True
        
        else:
            print(f"FAILED: ScoreMe status {response.status_code}")
            return False

    except Exception as e:
        print(f"ERROR in fetch_and_save_bank_report: {e}")
        return False