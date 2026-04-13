import httpx
from datetime import datetime, timezone
import os
import dotenv
dotenv.load_dotenv()

async def fetch_and_save_bank_report(db, user_id,reference_id,json_url):
    try:
        async with httpx.AsyncClient() as client:
            # 1. Get the data from ScoreMe

            response = await client.get(json_url, timeout=60.0,headers={
                    "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                    "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                })
            
        if response.status_code == 200:
            # This 'report_content' is the big JSON object you shared
            report_content = response.json() 

            # 2. Link the data with userid
            # We wrap the ScoreMe data to keep the userid as a searchable index
            final_document = {
                "user_id": user_id,
                "reference_id":reference_id,
                "report_data": report_content,  # This contains the 'Data', 'OverView', etc.
                "created_at": datetime.now(timezone.utc),
                "source_url": json_url
            }

            # 3. Save to the legacy collection
            await db["bankstatementreport"].insert_one(final_document)
            print(f"SUCCESS: Report ingested and linked for user {user_id}")
            return True
        else:
            print(f"FAILED: ScoreMe returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"ERROR in fetch_and_save_bank_report: {e}")
        return False
    

