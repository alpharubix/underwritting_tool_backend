import logging
import os
from contextlib import asynccontextmanager
import json
import uvicorn
from starlette.middleware.cors import CORSMiddleware
import asyncio

from controller.itr_controller.itr_analyzer_controller import poll_email_link_status
from routes.bank_scoring_routes import bank_scoring_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)



logging.getLogger("motor").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)

from database.databse_config import get_mongo_db,get_postgres_conn
from fastapi import FastAPI
from routes.auth_router import auth_router
from routes.user_route import user_router
from middleware.authorization_middleware import authorization
from routes.bsa_route import bsa_router
from routes.webhook_router import webhook_router
from controller.bsa_uploads import UploadHashMap
from routes.gst_router import gst_router
from routes.itr_router import itr_router

logger = logging.getLogger(__name__)
@asynccontextmanager
async def connect_to_databases(app: FastAPI): #database first approch
    try:
        postgres_conn = await get_postgres_conn()
        mongo_db = await get_mongo_db()
        app.state.mongo_db  = mongo_db
        app.state.postgres_conn = postgres_conn
        print('database connected successfully')
        upload_hashmap = UploadHashMap()
        await seed_database(mongo_db)
        asyncio.create_task(upload_hashmap.clean_expired_entries())
        asyncio.create_task(poll_email_link_status(app.state.mongo_db))
        yield
    except Exception as e:
        print("Error connecting to databases",e)
        raise e


app = FastAPI(lifespan=connect_to_databases)

app.middleware("http")(authorization)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(bsa_router)

app.include_router(webhook_router)

app.include_router(gst_router)

app.include_router(itr_router)

app.include_router(bank_scoring_router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port,reload=True)


#-------------------------------------------ROUGH WORK AND TESTING CODE BELOW DO NOT CONSIDER-------------------------------------------

#SEEDING PART 
async def seed_database(mongo_db):
    bank_parameters_collection = mongo_db["bank_parameters"]
    # --result = -await bank_parameters_collection.delete_many({})
    existing_entry = await bank_parameters_collection.count_documents({})
    if existing_entry > 0:
        print("Bank parameters already seeded")
        return
    with open("bank_params.json", "r") as f:
        bank_parameters = json.load(f)
    await bank_parameters_collection.insert_many(bank_parameters)

    print("Bank parameters seeded successfully")