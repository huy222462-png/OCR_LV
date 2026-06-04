# LuanVan OCR — Hướng dẫn triển khai

## Tính năng đã thêm

| Tính năng | Mô tả |
|-----------|-------|
| **Celery + Redis** | OCR xử lý bất đồng bộ, frontend poll task_id |
| **VnCoreNLP** | NER tiếng Việt đầy đủ, tự động fallback regex khi chưa cài |
| **Admin Panel** | Quản lý tài khoản, nhãn, audit log có phân trang |
| **Docker + Nginx** | 5 service: web, celery_worker, flower, redis, nginx |

---

## Chạy nhanh (Docker Compose)

```bash
# 1. Copy và điền cấu hình
cp .env.example .env
# Sửa DATABASE_URL trong .env

# 2. Build và chạy
docker compose up -d --build

# 3. Khởi tạo DB + dữ liệu mẫu (lần đầu)
docker compose exec web python -c "from app import create_app; from database import db; app=create_app(); app.app_context().push(); db.create_all()"
docker compose exec web python SEED.PY

# 4. Truy cập
# App: http://localhost
# Flower (monitor Celery): http://localhost:5555  (admin/admin123)
```

---

## Chạy local (không Docker)

```bash
# Yêu cầu: Python 3.12, Redis, SQL Server, Tesseract + vie lang

# Cài dependencies
pip install -r requirements.txt

# Chạy Flask
python app.py

# Chạy Celery worker (terminal khác)
celery -A celery_worker.celery worker --loglevel=info

# Chạy Flower (tùy chọn)
celery -A celery_worker.celery flower
```

---

## Cài VnCoreNLP (tùy chọn, tăng độ chính xác NER)

```bash
# Tạo thư mục
mkdir -p vncorenlp/models/wordsegmenter vncorenlp/models/ner

# Tải JAR
wget https://github.com/vncorenlp/VnCoreNLP/releases/download/v1.2/VnCoreNLP-1.2.jar \
     -O vncorenlp/VnCoreNLP-1.2.jar

# Tải models (word segmenter + NER)
BASE=https://raw.githubusercontent.com/vncorenlp/VnCoreNLP/master/models
wget $BASE/wordsegmenter/vi-vocab -P vncorenlp/models/wordsegmenter/
wget $BASE/wordsegmenter/wordsegmenter.rdr -P vncorenlp/models/wordsegmenter/
wget $BASE/ner/vi-ner.rdr -P vncorenlp/models/ner/
wget $BASE/ner/vi-ner-vocab.rdr -P vncorenlp/models/ner/

# Cài thư viện Python
pip install vncorenlp

# Bật trong .env
USE_VNCORENLP=true
```

---

## Cấu trúc project

```
LuanVan_OCR/
├── app.py                      # Flask factory
├── config.py                   # Cấu hình (Redis, VnCoreNLP, ...)
├── database.py                 # SQLAlchemy instance
├── celery_worker.py            # Celery app entry point
├── celery_tasks/
│   └── tasks.py                # Task OCR bất đồng bộ
├── backend/
│   ├── models.py               # ORM models
│   ├── routes_auth.py          # Đăng nhập/xuất
│   ├── routes_document.py      # Upload/search/save (async)
│   ├── routes_admin.py         # Admin API
│   └── utils.py                # Helpers
├── bo_xu_ly/
│   ├── __init__.py             # Pipeline OCR
│   ├── tien_xu_ly_anh.py       # OpenCV preprocessing
│   ├── nhan_dang_ocr.py        # Tesseract OCR
│   ├── chuan_hoa_chuoi.py      # Chuẩn hóa text
│   ├── trich_xuat_regex.py     # Trích xuất regex
│   └── nhan_dang_nlp.py        # VnCoreNLP NER + regex fallback
├── templates/
│   ├── admin/                  # Dashboard, quản lý user, nhãn, audit log
│   └── ...
├── nginx/
│   └── nginx.conf              # Reverse proxy config
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Tài khoản mặc định

| Tài khoản | Mật khẩu | Vai trò |
|-----------|----------|---------|
| `admin`   | `admin123` | QuanTriVien |


SQLEXPRESS   : MSSQL16.SQLEXPRESS
SQLEXPRESS01 : MSSQL17.SQLEXPRESS01
MSSQLSERVER  : MSSQL17.MSSQLSERVER
PSPath       : Microsoft.PowerShell.Core\Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Microsoft SQL Server\Instance
               Names\SQL
PSParentPath : Microsoft.PowerShell.Core\Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Microsoft SQL Server\Instance
               Names
PSChildName  : SQL
PSDrive      : HKLM
PSProvider   : Microsoft.PowerShell.Core\Registry

DB URL: mssql+pyodbc://appuser:StrongP@ssw0rd!@host.docker.internal:1500/ocr_vanban?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=no&TrustServerCertificate=yes


$env:Path += ';C:\Program Files\Tesseract-OCR'
tesseract --version

$dir = 'C:\Program Files\Tesseract-OCR'
$current = [Environment]::GetEnvironmentVariable('Path','User')
if ($current -notlike "*$dir*") {
  [Environment]::SetEnvironmentVariable('Path', "$current;$dir",'User')
  Write-Host 'Đã thêm vào PATH (User). Đóng & mở lại PowerShell để có hiệu lực.'
} else {
  Write-Host 'Đã có trong PATH (User).'
}