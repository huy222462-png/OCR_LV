"""
Khởi động Celery worker:
    celery -A celery_worker.celery worker --loglevel=info
"""
from app import create_app
from celery_tasks.tasks import celery  # noqa: F401

flask_app = create_app()

# Đẩy app context để các task truy cập db
flask_app.app_context().push()
