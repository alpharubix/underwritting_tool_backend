import asyncio
import logging
import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from controller.bsa_uploads import UploadHashMap
from controller.itr_controller.itr_analyzer_controller import poll_email_link_status
from database.databse_config import get_mongo_db, get_postgres_conn
from middleware.authorization_middleware import authorization
from routes.accounts_filter_router import accounts_filter_router
from routes.auth_router import auth_router
from routes.bank_scoring_routes import bank_scoring_router
from routes.bsa_route import bsa_router
from routes.cibil_router import cibil_router
from routes.gst_router import gst_router
from routes.itr_router import itr_router
from routes.kyc_router import kyc_router
from routes.ticktes_router import ticket_router
from routes.user_route import user_router
from routes.webhook_router import webhook_router
from routes.anchor_router import anchor_router
from routes.admin_router import admin_router
from routes.payments_router import payments_router
from routes.wallet_router import wallet_router
from routes.rectify_money_router import rectify_money_router
from routes.save_money_route import save_money_router
from routes.access_money_route import access_money_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logging.getLogger("motor").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)
@asynccontextmanager
async def connect_to_databases(app: FastAPI): #database first approch
    try:
        postgres_conn = await get_postgres_conn()
        mongo_db = await get_mongo_db()
        app.state.mongo_db  = mongo_db
        app.state.postgres_conn = postgres_conn
        print('database connected successfully')
        # upload_hashmap = UploadHashMap()
        # asyncio.create_task(upload_hashmap.clean_expired_entries())
        # asyncio.create_task(poll_email_link_status(app.state.mongo_db))
        yield
    except Exception as e:
        print("Error connecting to databases",e)
        raise


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
app.include_router(accounts_filter_router)
app.include_router(bsa_router)
app.include_router(webhook_router)
app.include_router(gst_router)
app.include_router(itr_router)
app.include_router(kyc_router)
app.include_router(cibil_router)
app.include_router(bank_scoring_router)
app.include_router(ticket_router)
app.include_router(admin_router)
app.include_router(anchor_router)
app.include_router(payments_router)
app.include_router(wallet_router)
app.include_router(rectify_money_router)
app.include_router(save_money_router)
app.include_router(access_money_router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)