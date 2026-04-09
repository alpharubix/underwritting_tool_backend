import asyncio
from celery_app import celery_app
from database.db import init_mongo # Import your init function
from services.reconciliation_service import start_reconciliation

def run_async(coro):
    """Helper to run async code inside sync Celery"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@celery_app.task(name="process_reconciliation")
def process_reconciliation(reference_id, json_url):
    print(f"--- CELERY WORKER STARTING FOR {reference_id} ---")
    
    try:
        # FIX: Tell the worker to connect to Mongo before doing the work
        run_async(init_mongo()) 
        
        result = run_async(start_reconciliation(reference_id, json_url))
        print(f"--- CELERY WORKER FINISHED: {result} ---")
        return result
    except Exception as e:
        print(f"--- CELERY WORKER FAILED: {str(e)} ---")
        return f"Failed for {reference_id}"