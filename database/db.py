from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv(override=True)

_mongo_client: AsyncIOMotorClient | None = None
_postgres_pool: asyncpg.Pool | None = None


async def init_mongo() -> None:
    global _mongo_client
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise ValueError("MONGO_URI not found in environment")
    _mongo_client = AsyncIOMotorClient(uri)
    await _mongo_client.admin.command("ping")
    print("[MongoDB] Connected successfully")


async def init_postgres() -> None:
    global _postgres_pool
    uri = os.getenv("POSTGRES_URI")
    if not uri:
        raise ValueError("POSTGRES_URI not found in environment")
    _postgres_pool = await asyncpg.create_pool(
        dsn=uri,
        min_size=2,
        max_size=10,
    )
    print("[Postgres] Connected successfully")


async def close_mongo() -> None:
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        print("[MongoDB] Connection closed")


async def close_postgres() -> None:
    global _postgres_pool
    if _postgres_pool is not None:
        await _postgres_pool.close()
        _postgres_pool = None
        print("[Postgres] Connection closed")


def get_mongo_db():
    if _mongo_client is None:
        raise RuntimeError("MongoDB not initialized")

    db_name = os.getenv("MONGODB_DB_NAME", "underwritting")

    return _mongo_client[db_name]


def get_postgres_pool():
    if _postgres_pool is None:
        raise RuntimeError("Postgres not initialized")
    return _postgres_pool