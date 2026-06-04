"""
celery_tasks/tasks.py
Xử lý OCR bất đồng bộ qua Celery + Redis.
"""
import json
import logging
from datetime import datetime

from celery import Celery
from celery.signals import task_failure, task_success

from config import Config

# Khởi tạo Celery tách biệt với Flask app
celery = Celery(
    'luanvan_ocr',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
)
celery.config_from_object({
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'Asia/Ho_Chi_Minh',
    'enable_utc': True,
    'task_track_started': True,
    # Tự động retry khi broker mất kết nối
    'task_acks_late': True,
    'worker_prefetch_multiplier': 1,
})

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name='tasks.process_document',
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=120,   # 2 phút
    time_limit=180,        # hard kill sau 3 phút
)
def process_document(self, doc_id: int, file_path: str):
    """
    Task OCR bất đồng bộ:
    1. Đọc file → tiền xử lý → OCR → trích xuất
    2. Cập nhật DB
    3. Ghi audit log
    """
    # Import ở đây tránh circular import
    from app import create_app
    from database import db
    from backend.models import TaiLieu, LichSuThaoTac
    from bo_xu_ly import xu_ly_tai_lieu

    flask_app = create_app()

    with flask_app.app_context():
        tai_lieu = TaiLieu.query.get(doc_id)
        if not tai_lieu:
            logger.error('Không tìm thấy tài liệu id=%s', doc_id)
            return {'status': 'error', 'message': 'Tài liệu không tồn tại'}

        # Cập nhật trạng thái → DANG_XU_LY
        tai_lieu.trang_thai = 'DANG_XU_LY'
        db.session.commit()

        try:
            # === Pipeline OCR ===
            ket_qua = xu_ly_tai_lieu(file_path)

            ngay_bh = ket_qua.get('ngay_ban_hanh')
            if isinstance(ngay_bh, str) and ngay_bh:
                try:
                    ngay_bh = datetime.strptime(ngay_bh, '%Y-%m-%d').date()
                except ValueError:
                    ngay_bh = None

            tai_lieu.so_hieu_van_ban = ket_qua.get('so_hieu_van_ban')
            tai_lieu.ngay_ban_hanh = ngay_bh
            tai_lieu.co_quan_ban_hanh = ket_qua.get('co_quan_ban_hanh')
            tai_lieu.trich_yeu_noi_dung = ket_qua.get('trich_yeu_noi_dung') or 'Chưa trích xuất'
            tai_lieu.toan_van_chu_tho = ket_qua.get('toan_van_chu_tho')
            tai_lieu.trang_thai = 'CHO_XAC_NHAN'
            tai_lieu.ngay_cap_nhat_cuoi = datetime.now()
            db.session.commit()

            # Ghi audit log
            _ghi_log_system(db, doc_id, tai_lieu.id_nguoi_tao, 'OCR_HOAN_THANH', {
                'task_id': self.request.id,
                'missing_fields': ket_qua.get('missing_fields', []),
            })

            return {
                'status': 'success',
                'doc_id': doc_id,
                'trang_thai': 'CHO_XAC_NHAN',
                'so_hieu_van_ban': ket_qua.get('so_hieu_van_ban'),
                'ngay_ban_hanh': ket_qua.get('ngay_ban_hanh'),
                'missing_fields': ket_qua.get('missing_fields', []),
            }

        except Exception as exc:
            logger.exception('OCR thất bại cho tài liệu id=%s: %s', doc_id, exc)

            # Retry nếu còn lần thử
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                tai_lieu.trang_thai = 'THAT_BAI'
                db.session.commit()
                _ghi_log_system(db, doc_id, tai_lieu.id_nguoi_tao, 'OCR_THAT_BAI', {
                    'error': str(exc),
                    'task_id': self.request.id,
                })
                return {'status': 'error', 'doc_id': doc_id, 'message': str(exc)}


def _ghi_log_system(db, id_tai_lieu, id_nguoi_dung, hanh_dong, chi_tiet):
    """Ghi audit log không cần session Flask."""
    from backend.models import LichSuThaoTac
    log = LichSuThaoTac(
        id_tai_lieu=id_tai_lieu,
        id_nguoi_dung=id_nguoi_dung,
        hanh_dong=hanh_dong,
        chi_tiet_thay_doi=json.dumps(chi_tiet, ensure_ascii=False),
    )
    db.session.add(log)
    db.session.commit()


# ── Test task (không phụ thuộc DB) ─────────────────────────────────────────
@celery.task(name='tasks.ping')
def ping():
    """Simple test task to verify Celery/Flower connectivity."""
    return 'pong'
