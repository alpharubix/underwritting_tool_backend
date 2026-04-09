from celery import Celery
import os

celery_app = Celery(
    "underwriting_tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

# Tell Celery exactly which files to look into for tasks
# celery_app.autodiscover_tasks(['tasks'], related_name='bsa_tasks')

celery_app.conf.imports = ('tasks.bsa_tasks',)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # This helps with the warning you saw earlier
    broker_connection_retry_on_startup=True 
)