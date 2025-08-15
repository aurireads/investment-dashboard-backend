# Configuração Celery
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    beat_schedule={
        "update-daily-prices-every-24-hours": {
            "task": "app.tasks.daily_tasks.update_all_daily_prices",
            "schedule": 86400.0, # Every 24 hours
        },
        "update-realtime-prices-every-5-seconds": {
            "task": "app.tasks.daily_tasks.update_all_realtime_prices",
            "schedule": 5.0, # Every 5 seconds
        }
    }
)