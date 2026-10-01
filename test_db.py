import asyncio
import os
import dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg

dotenv.load_dotenv(override=True)


async def test_mongo():
    try:
        client = AsyncIOMotorClient(
            os.getenv("MONGO_URI"), serverSelectionTimeoutMS=5000
        )
        await client.admin.command("ping")
        print("Mongo connected successfully")
    except Exception as e:
        print(f"Mongo connection failed: {e}")


async def test_postgres():
    try:
        conn = await asyncpg.connect(os.getenv("POSTGRES_URI"))
        print("Postgres connected successfully")
        await conn.close()
    except Exception as e:
        print(f"Postgres connection failed: {e}")


async def main():
    await test_mongo()
    await test_postgres()


asyncio.run(main())
