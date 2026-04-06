from contextlib import asynccontextmanager
from database.databse_config import get_mongo_db,get_postgres_conn
from fastapi import FastAPI
from uvicorn import run

@asynccontextmanager
async def connect_to_databases(app: FastAPI): #database first approch
    try:
        postgres_conn = await get_postgres_conn()
        mongo_db = await get_mongo_db()
        app.state.mongo_db  = mongo_db
        app.state.postgres_conn = postgres_conn
        print('database connected successfully')
        yield
    except Exception as e:
        print("Error connecting to databases",e)
        raise e
    finally:
        if postgres_conn:
            await postgres_conn.close()

        if mongo_db:
            mongo_db.client.close()

app = FastAPI(lifespan=connect_to_databases)

run(app=app, host="localhost", port=8080)