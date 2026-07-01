from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import dotenv
import os
dotenv.load_dotenv(override=True)

async def get_mongo_db():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"),serverSelectionTimeoutMS=5000,maxPoolSize=10,minPoolSize=5)
    try:
        db = client["underwriting"]
        return db
    except Exception as e:
        raise e

async def get_postgres_conn():
    conn = await asyncpg.connect(os.getenv("POSTGRES_URI"),)
    try:
        return conn
    except Exception as e:
        raise  e
