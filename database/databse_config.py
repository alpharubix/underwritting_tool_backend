from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import dotenv
import os
dotenv.load_dotenv(override=True)


async def get_mongo_db():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    try:
        db = client["underwritting"]
        return db
    finally:
        client.close()

async def get_postgres_conn():
    conn = await asyncpg.connect(os.getenv("POSTGRES_URI"))
    try:
        return conn
    finally:
        await conn.close()