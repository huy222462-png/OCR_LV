import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'luanvan_ocr_secret_key_2026')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'media', 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    SESSION_TIMEOUT_MINUTES = 30

    # ── Celery + Redis ─────────────────────────────────────────
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

    # ── VnCoreNLP ──────────────────────────────────────────────
    # Tải model tại: https://github.com/vncorenlp/VnCoreNLP
    VNCORENLP_JAR = os.getenv(
        'VNCORENLP_JAR',
        os.path.join(BASE_DIR, 'vncorenlp', 'VnCoreNLP-1.2.jar')
    )
    VNCORENLP_MODELS = os.getenv(
        'VNCORENLP_MODELS',
        os.path.join(BASE_DIR, 'vncorenlp', 'models')
    )
    USE_VNCORENLP = os.getenv('USE_VNCORENLP', 'false').lower() == 'true'
