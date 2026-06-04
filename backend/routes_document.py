"""
backend/routes_document.py
Upload file → gửi task Celery → trả task_id cho client poll.
"""
import json
import os
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, session, render_template, send_file

from database import db
from backend.models import TaiLieu, LoaiTaiLieu, LichSuThaoTac
from backend.utils import login_required, allowed_file, save_upload, pdf_to_image

document_bp = Blueprint('document', __name__)


# ── Trang giao diện ────────────────────────────────────────────────────────────

@document_bp.route('/tai-len')
@login_required
def upload_page():
    loai_list = LoaiTaiLieu.query.all()
    return render_template('tai_len.html', loai_list=loai_list)


@document_bp.route('/tim-kiem')
@login_required
def search_page():
    loai_list = LoaiTaiLieu.query.all()
    return render_template('tim_kiem.html', loai_list=loai_list)


# ── API Upload (bất đồng bộ) ───────────────────────────────────────────────────

@document_bp.route('/api/v1/documents/upload', methods=['POST'])
@login_required
def upload_document():
    """
    1. Lưu file vào disk
    2. Tạo bản ghi TaiLieu với trạng thái DANG_XU_LY
    3. Gửi task Celery
    4. Trả task_id để client poll
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Không có tệp tải lên'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Tên tệp không hợp lệ'}), 400

    allowed = current_app.config['ALLOWED_EXTENSIONS']
    if not allowed_file(file.filename, allowed):
        return jsonify({'error': 'Chỉ hỗ trợ JPG, PNG, PDF (tối đa 10MB)'}), 400

    upload_folder = current_app.config['UPLOAD_FOLDER']
    ten_goc, path = save_upload(file, upload_folder)

    # Chuyển PDF → ảnh để OCR
    ocr_path = path
    if path.lower().endswith('.pdf'):
        try:
            ocr_path = pdf_to_image(path, upload_folder)
        except Exception:
            return jsonify({
                'error': 'Không đọc được PDF. Vui lòng kiểm tra lại tệp hoặc nhập thủ công.',
                'manual': True,
            }), 422

    # Tạo bản ghi DB với trạng thái DANG_XU_LY
    tai_lieu = TaiLieu(
        id_loai_tai_lieu=request.form.get('id_loai_tai_lieu', type=int),
        trich_yeu_noi_dung='Đang xử lý...',
        ten_file_goc=ten_goc,
        duong_dan_file=path,
        trang_thai='DANG_XU_LY',
        id_nguoi_tao=session['user_id'],
    )
    db.session.add(tai_lieu)
    db.session.commit()

    _ghi_log(tai_lieu.id_tai_lieu, 'TAI_LEN', {'file': ten_goc})

    # Gửi task Celery bất đồng bộ
    try:
        from celery_tasks.tasks import process_document
        task = process_document.delay(tai_lieu.id_tai_lieu, ocr_path)
        task_id = task.id
    except Exception as exc:
        # Nếu Redis không khả dụng → xử lý đồng bộ ngay
        current_app.logger.warning('Celery không khả dụng, xử lý đồng bộ: %s', exc)
        task_id = None
        _xu_ly_dong_bo(tai_lieu, ocr_path)

    return jsonify({
        'id_tai_lieu': tai_lieu.id_tai_lieu,
        'task_id': task_id,
        'trang_thai': tai_lieu.trang_thai,
        'ten_file_goc': ten_goc,
        'preview_url': f'/api/v1/documents/{tai_lieu.id_tai_lieu}/file',
        'message': 'Đang phân tích OCR, vui lòng chờ...' if task_id else 'Xử lý đồng bộ hoàn tất.',
        'async': task_id is not None,
    })


def _xu_ly_dong_bo(tai_lieu: TaiLieu, ocr_path: str):
    """Fallback xử lý đồng bộ khi Celery không khả dụng."""
    from bo_xu_ly import xu_ly_tai_lieu
    try:
        ket_qua = xu_ly_tai_lieu(ocr_path)
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
    except Exception as exc:
        tai_lieu.trang_thai = 'THAT_BAI'
        db.session.commit()


# ── API Poll trạng thái task ───────────────────────────────────────────────────

@document_bp.route('/api/v1/tasks/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    """Frontend poll endpoint để biết OCR đã xong chưa."""
    try:
        from celery_tasks.tasks import celery as celery_app
        task = celery_app.AsyncResult(task_id)
        response = {
            'task_id': task_id,
            'state': task.state,  # PENDING / STARTED / SUCCESS / FAILURE / RETRY
        }
        if task.state == 'SUCCESS':
            response['result'] = task.result
        elif task.state == 'FAILURE':
            response['error'] = str(task.result)
        return jsonify(response)
    except Exception as exc:
        return jsonify({'task_id': task_id, 'state': 'UNKNOWN', 'error': str(exc)})


# ── API Save ───────────────────────────────────────────────────────────────────

@document_bp.route('/api/v1/documents/save', methods=['POST'])
@login_required
def save_document():
    data = request.get_json() or {}
    doc_id = data.get('id_tai_lieu')
    if not doc_id:
        return jsonify({'error': 'Thiếu id_tai_lieu'}), 400

    tai_lieu = TaiLieu.query.get_or_404(doc_id)
    if tai_lieu.id_nguoi_tao != session['user_id'] and session.get('chuc_vu') != 'QuanTriVien':
        return jsonify({'error': 'Không có quyền sửa tài liệu này'}), 403

    tai_lieu.so_hieu_van_ban = data.get('so_hieu_van_ban') or tai_lieu.so_hieu_van_ban
    tai_lieu.co_quan_ban_hanh = data.get('co_quan_ban_hanh') or tai_lieu.co_quan_ban_hanh
    tai_lieu.trich_yeu_noi_dung = data.get('trich_yeu_noi_dung') or tai_lieu.trich_yeu_noi_dung
    tai_lieu.toan_van_chu_tho = data.get('toan_van_chu_tho') or tai_lieu.toan_van_chu_tho
    if data.get('id_loai_tai_lieu'):
        tai_lieu.id_loai_tai_lieu = data['id_loai_tai_lieu']

    ngay = data.get('ngay_ban_hanh')
    if ngay:
        try:
            tai_lieu.ngay_ban_hanh = datetime.strptime(ngay, '%Y-%m-%d').date()
        except ValueError:
            pass

    tai_lieu.trang_thai = 'DA_LUU'
    tai_lieu.id_nguoi_cap_nhat = session['user_id']
    tai_lieu.ngay_cap_nhat_cuoi = datetime.now()
    db.session.commit()

    _ghi_log(doc_id, 'XAC_NHAN_LUU', data)
    return jsonify({'message': 'Đã lưu tài liệu thành công', 'id_tai_lieu': doc_id})


# ── API Search ─────────────────────────────────────────────────────────────────

@document_bp.route('/api/v1/documents/search', methods=['GET'])
@login_required
def search_documents():
    q = TaiLieu.query.filter(TaiLieu.trang_thai == 'DA_LUU')

    so_hieu = request.args.get('so_hieu', '').strip()
    tu_khoa = request.args.get('tu_khoa', '').strip()
    tu_ngay = request.args.get('tu_ngay', '').strip()
    den_ngay = request.args.get('den_ngay', '').strip()
    id_loai = request.args.get('id_loai_tai_lieu', type=int)

    if so_hieu:
        q = q.filter(TaiLieu.so_hieu_van_ban.ilike(f'%{so_hieu}%'))
    if id_loai:
        q = q.filter(TaiLieu.id_loai_tai_lieu == id_loai)
    if tu_ngay:
        q = q.filter(TaiLieu.ngay_ban_hanh >= datetime.strptime(tu_ngay, '%Y-%m-%d').date())
    if den_ngay:
        q = q.filter(TaiLieu.ngay_ban_hanh <= datetime.strptime(den_ngay, '%Y-%m-%d').date())
    if tu_khoa:
        like = f'%{tu_khoa}%'
        q = q.filter(db.or_(
            TaiLieu.trich_yeu_noi_dung.ilike(like),
            TaiLieu.toan_van_chu_tho.ilike(like),
        ))

    results = q.order_by(TaiLieu.ngay_day_len.desc()).limit(50).all()
    return jsonify([_serialize_doc(d) for d in results])


@document_bp.route('/api/v1/documents/<int:doc_id>', methods=['GET'])
@login_required
def get_document(doc_id):
    tai_lieu = TaiLieu.query.get_or_404(doc_id)
    return jsonify(_serialize_doc(tai_lieu, detail=True))


@document_bp.route('/api/v1/documents/<int:doc_id>/file')
@login_required
def get_document_file(doc_id):
    tai_lieu = TaiLieu.query.get_or_404(doc_id)
    if not os.path.exists(tai_lieu.duong_dan_file):
        return jsonify({'error': 'Tệp không tồn tại'}), 404
    return send_file(tai_lieu.duong_dan_file)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize_doc(doc: TaiLieu, detail: bool = False) -> dict:
    data = {
        'id_tai_lieu': doc.id_tai_lieu,
        'so_hieu_van_ban': doc.so_hieu_van_ban,
        'ngay_ban_hanh': doc.ngay_ban_hanh.isoformat() if doc.ngay_ban_hanh else None,
        'co_quan_ban_hanh': doc.co_quan_ban_hanh,
        'trich_yeu_noi_dung': doc.trich_yeu_noi_dung,
        'ten_loai': doc.loai_tai_lieu.ten_loai if doc.loai_tai_lieu else None,
        'trang_thai': doc.trang_thai,
        'ngay_day_len': doc.ngay_day_len.isoformat() if doc.ngay_day_len else None,
    }
    if detail:
        data['toan_van_chu_tho'] = doc.toan_van_chu_tho
        data['ten_file_goc'] = doc.ten_file_goc
        data['preview_url'] = f'/api/v1/documents/{doc.id_tai_lieu}/file'
    return data


def _ghi_log(id_tai_lieu: int, hanh_dong: str, chi_tiet: dict):
    log = LichSuThaoTac(
        id_tai_lieu=id_tai_lieu,
        id_nguoi_dung=session['user_id'],
        hanh_dong=hanh_dong,
        chi_tiet_thay_doi=json.dumps(chi_tiet, ensure_ascii=False),
    )
    db.session.add(log)
    db.session.commit()
