# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps: Cài đặt các công cụ cơ bản, Tesseract, OpenCV, Java (VnCoreNLP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg2 \
    unixodbc-dev \
    tesseract-ocr \
    tesseract-ocr-vie \
    libgl1 \
    libglib2.0-0 \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Nạp khóa Microsoft GPG và cấu hình mssql-release chuẩn chỉnh cho Debian 12 (Sửa triệt để lỗi Malformed)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn celery[redis] redis flower

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM builder AS runtime

WORKDIR /app
COPY . .

RUN mkdir -p media/uploads vncorenlp/models

# Không chạy root trong production
# Không chạy root trong production
RUN useradd -r -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# Ép Python nhận diện thư mục hiện tại để tìm thấy file database.py
ENV PYTHONPATH=/app

EXPOSE 5000

# Gunicorn: Thay đổi cách chỉ định sang dạng module trực tiếp của app
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--chdir", "/app", \
     "app:create_app()"]