"""Celery application instance (T-3026: async task queue setup).

Run a worker:
    celery -A app.core.celery_app worker --loglevel=info

Reuses settings.redis_url (app/core/cache.py's Redis wrapper does the same)
as both broker and result backend rather than adding a new setting.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "edgp",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.document_tasks"],
)

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
