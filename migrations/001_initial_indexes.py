import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import dotenv

dotenv.load_dotenv()

async def apply_indexes():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGODB_DB_NAME")]
    collection = db["bankstatementreport"]

    print("Applying optimized ESR indexes...")

    # Index 1: The Dashboard Lookup (Equality -> Sort)
    # background=True ensures the DB doesn't lock for other users during the build
    await collection.create_index(
        [("user_id", 1), ("created_at", -1)],
        name="idx_user_latest_report",
        background=True
    )

    # Index 2: The Period Analysis (Equality -> Range)
    await collection.create_index(
        [("user_id", 1), ("from_date", 1), ("to_date", 1)],
        name="idx_user_period_range",
        background=True
    )

    print("Indexes applied successfully.")

if __name__ == "__main__":
    asyncio.run(apply_indexes())