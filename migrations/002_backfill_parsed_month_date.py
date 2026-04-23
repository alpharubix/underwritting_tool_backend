"""
Migration 002 — Backfill parsedMonthDate on existing bankstatementreport documents.

New documents written after fetch_and_save_bank_report.py was updated already
carry parsedMonthDate as ISODate inside each Summary Of Debit And Credit entry.
This script patches all older documents that are missing that field.

Run once:
    python migrations/002_backfill_parsed_month_date.py

Safe to re-run — skips entries that already have parsedMonthDate.
"""

import asyncio
import os
from datetime import datetime

import dotenv
from motor.motor_asyncio import AsyncIOMotorClient

dotenv.load_dotenv()

COLLECTION = "bankstatementreport"
SUMMARY_KEY = "Summary Of Debit And Credit"


async def backfill(dry_run: bool = False):
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGODB_DB_NAME", "underwritting")]
    collection = db[COLLECTION]

    # Only fetch documents where at least one array entry is missing parsedMonthDate.
    query = {
        f"analysis_metadata.Data.{SUMMARY_KEY}": {"$exists": True},
        f"analysis_metadata.Data.{SUMMARY_KEY}.parsedMonthDate": {"$exists": False}
    }

    total = await collection.count_documents(query)
    print(f"[002] Documents to patch: {total}  (dry_run={dry_run})")

    updated = 0
    failed = 0

    async for doc in collection.find(query, {"_id": 1, f"analysis_metadata.Data.{SUMMARY_KEY}": 1}):
        doc_id = doc["_id"]
        entries = doc.get("analysis_metadata", {}).get("Data", {}).get(SUMMARY_KEY, [])

        patched_entries = []
        changed = False

        for entry in entries:
            if "parsedMonthDate" not in entry:
                month_str = entry.get("month", "")
                if month_str:
                    try:
                        entry["parsedMonthDate"] = datetime.strptime("01 " + month_str, "%d %b %Y")
                        changed = True
                    except ValueError:
                        print(f"  [WARN] _id={doc_id} — could not parse month: '{month_str}'")
            patched_entries.append(entry)

        if not changed:
            continue

        if dry_run:
            print(f"  [DRY RUN] would patch _id={doc_id} ({len(patched_entries)} entries)")
            updated += 1
            continue

        try:
            await collection.update_one(
                {"_id": doc_id},
                {"$set": {f"analysis_metadata.Data.{SUMMARY_KEY}": patched_entries}}
            )
            updated += 1
            print(f"  [OK] patched _id={doc_id}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] _id={doc_id} — {e}")

    print(f"\n[002] Done. patched={updated}  failed={failed}  total={total}")

    if not dry_run:
        await apply_index(collection)

    client.close()


async def apply_index(collection):
    print("[002] Creating multikey index on parsedMonthDate ...")
    await collection.create_index(
        [
            ("user_id", 1),
            (f"analysis_metadata.Data.{SUMMARY_KEY}.parsedMonthDate", 1)
        ],
        name="idx_user_summary_month_date",
        background=True
    )
    print("[002] Index created.")


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    asyncio.run(backfill(dry_run=dry))
