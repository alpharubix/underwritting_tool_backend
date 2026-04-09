from contextlib import asynccontextmanager
from database.databse_config import get_mongo_db,get_postgres_conn
from fastapi import FastAPI
from uvicorn import run
from routes.auth_router import auth_router
from routes.user_route import user_router
from middleware.authorization_middleware import authorization

from database.db import init_mongo, init_postgres, close_mongo, close_postgres
from routes.bsa_route import router as bsa_router
@asynccontextmanager
async def connect_to_databases(app: FastAPI): #database first approch
    try:
        postgres_conn = await get_postgres_conn()
        mongo_db = await get_mongo_db()
        app.state.mongo_db  = mongo_db
        app.state.postgres_conn = postgres_conn
        print('database connected successfully')

        # i have added this 2 lines for db.py
        await init_mongo()
        await init_postgres()

        yield
    except Exception as e:
        print("Error connecting to databases",e)
        raise e
    finally:
        if postgres_conn:
            await postgres_conn.close()

        if mongo_db is not None:
            mongo_db.client.close()
        
        # ↓  THESE TWO LINES — close your connections on shutdown
        await close_mongo()
        await close_postgres()


app = FastAPI(lifespan=connect_to_databases)
app.middleware("http")(authorization)
app.include_router(auth_router)
app.include_router(user_router)

app.include_router(bsa_router, prefix="/bsa", tags=["BSA"])



# run(app=app, host="localhost", port=8080)
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )