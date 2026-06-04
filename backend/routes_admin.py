"""
backend/routes_admin.py
Quản trị Admin: tài khoản, nhãn tài liệu, audit log.
Chỉ QuanTriVien mới truy cập được.
"""
import json
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for

from database import db
from backend.models import NguoiDung, ChucVu, PhongBan, NhanTaiLieu, LichSuThaoTac, TaiLieu
from backend.utils import hash_password

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Decorator kiểm tra quyền Admin ────────────────────────────────────────────

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/admin/api/'):
                return jsonify({'error': 'Chưa đăng nhập'}), 401
            return redirect(url_for('auth.login'))
        if session.get('chuc_vu') != 'QuanTriVien':
            if request.path.startswith('/admin/api/'):
                return jsonify({'error': 'Không có quyền truy cập'}), 403
            return redirect(url_for('auth.dashboard'))
        return view(*args, **kwargs)
    return wrapped


# ── Trang Admin ────────────────────────────────────────────────────────────────

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    stats = {
        'tong_nguoi_dung': NguoiDung.query.count(),
        'tong_tai_lieu': TaiLieu.query.count(),
        'tai_lieu_cho_xac_nhan': TaiLieu.query.filter_by(trang_thai='CHO_XAC_NHAN').count(),
        'tong_nhan': NhanTaiLieu.query.count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/nguoi-dung')
@admin_required
def nguoi_dung_page():
    return render_template('admin/nguoi_dung.html')


@admin_bp.route('/nhan-tai-lieu')
@admin_required
def nhan_page():
    return render_template('admin/nhan.html')


@admin_bp.route('/audit-log')
@admin_required
def audit_log_page():
    return render_template('admin/audit_log.html')


# ── API Quản lý Người dùng ─────────────────────────────────────────────────────

@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    users = NguoiDung.query.order_by(NguoiDung.ngay_tao.desc()).all()
    return jsonify([_serialize_user(u) for u in users])


@admin_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json() or {}
    required = ['ten_dang_nhap', 'mat_khau', 'ho_ten', 'id_chuc_vu']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Thiếu trường: {field}'}), 400

    if NguoiDung.query.filter_by(ten_dang_nhap=data['ten_dang_nhap']).first():
        return jsonify({'error': 'Tên đăng nhập đã tồn tại'}), 409

    user = NguoiDung(
        ten_dang_nhap=data['ten_dang_nhap'].strip(),
        mat_khau_ma_hoa=hash_password(data['mat_khau']),
        ho_ten=data['ho_ten'].strip(),
        email=data.get('email', '').strip() or None,
        id_chuc_vu=data['id_chuc_vu'],
        id_phong_ban=data.get('id_phong_ban'),
        trang_thai_hoat_dong=data.get('trang_thai_hoat_dong', True),
        ngay_tao=datetime.now(),
    )
    db.session.add(user)
    db.session.commit()
    _ghi_audit_admin('TAO_NGUOI_DUNG', {'ten_dang_nhap': user.ten_dang_nhap})
    return jsonify(_serialize_user(user)), 201


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = NguoiDung.query.get_or_404(user_id)
    data = request.get_json() or {}

    if 'ho_ten' in data:
        user.ho_ten = data['ho_ten'].strip()
    if 'email' in data:
        user.email = data['email'].strip() or None
    if 'id_chuc_vu' in data:
        user.id_chuc_vu = data['id_chuc_vu']
    if 'id_phong_ban' in data:
        user.id_phong_ban = data['id_phong_ban']
    if 'trang_thai_hoat_dong' in data:
        user.trang_thai_hoat_dong = bool(data['trang_thai_hoat_dong'])
    if data.get('mat_khau_moi'):
        user.mat_khau_ma_hoa = hash_password(data['mat_khau_moi'])

    db.session.commit()
    _ghi_audit_admin('CAP_NHAT_NGUOI_DUNG', {'user_id': user_id, 'fields': list(data.keys())})
    return jsonify(_serialize_user(user))


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        return jsonify({'error': 'Không thể xóa chính mình'}), 400
    user = NguoiDung.query.get_or_404(user_id)
    ten = user.ten_dang_nhap
    # Vô hiệu hóa thay vì xóa cứng (bảo toàn audit log)
    user.trang_thai_hoat_dong = False
    db.session.commit()
    _ghi_audit_admin('VO_HIEU_NGUOI_DUNG', {'ten_dang_nhap': ten})
    return jsonify({'message': f'Đã vô hiệu hóa tài khoản {ten}'})


# ── API Quản lý Nhãn ───────────────────────────────────────────────────────────

@admin_bp.route('/api/labels', methods=['GET'])
@admin_required
def list_labels():
    labels = NhanTaiLieu.query.order_by(NhanTaiLieu.ten_nhan).all()
    return jsonify([_serialize_label(l) for l in labels])


@admin_bp.route('/api/labels', methods=['POST'])
@admin_required
def create_label():
    data = request.get_json() or {}
    if not data.get('ten_nhan'):
        return jsonify({'error': 'Thiếu ten_nhan'}), 400
    if NhanTaiLieu.query.filter_by(ten_nhan=data['ten_nhan']).first():
        return jsonify({'error': 'Nhãn đã tồn tại'}), 409

    label = NhanTaiLieu(
        ten_nhan=data['ten_nhan'].strip(),
        mau_sac_hien_thi=data.get('mau_sac_hien_thi', '#6c757d'),
    )
    db.session.add(label)
    db.session.commit()
    _ghi_audit_admin('TAO_NHAN', {'ten_nhan': label.ten_nhan})
    return jsonify(_serialize_label(label)), 201


@admin_bp.route('/api/labels/<int:label_id>', methods=['PUT'])
@admin_required
def update_label(label_id):
    label = NhanTaiLieu.query.get_or_404(label_id)
    data = request.get_json() or {}
    if 'ten_nhan' in data:
        label.ten_nhan = data['ten_nhan'].strip()
    if 'mau_sac_hien_thi' in data:
        label.mau_sac_hien_thi = data['mau_sac_hien_thi']
    db.session.commit()
    _ghi_audit_admin('CAP_NHAT_NHAN', {'label_id': label_id})
    return jsonify(_serialize_label(label))


@admin_bp.route('/api/labels/<int:label_id>', methods=['DELETE'])
@admin_required
def delete_label(label_id):
    label = NhanTaiLieu.query.get_or_404(label_id)
    ten = label.ten_nhan
    db.session.delete(label)
    db.session.commit()
    _ghi_audit_admin('XOA_NHAN', {'ten_nhan': ten})
    return jsonify({'message': f'Đã xóa nhãn {ten}'})


# ── API Audit Log ──────────────────────────────────────────────────────────────

@admin_bp.route('/api/audit-log', methods=['GET'])
@admin_required
def get_audit_log():
    """Lấy audit log có phân trang và bộ lọc."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 200)
    hanh_dong = request.args.get('hanh_dong', '').strip()
    user_id = request.args.get('user_id', type=int)
    tu_ngay = request.args.get('tu_ngay', '').strip()
    den_ngay = request.args.get('den_ngay', '').strip()

    q = LichSuThaoTac.query

    if hanh_dong:
        q = q.filter(LichSuThaoTac.hanh_dong.ilike(f'%{hanh_dong}%'))
    if user_id:
        q = q.filter(LichSuThaoTac.id_nguoi_dung == user_id)
    if tu_ngay:
        q = q.filter(LichSuThaoTac.thoi_gian_thuc_hien >= datetime.strptime(tu_ngay, '%Y-%m-%d'))
    if den_ngay:
        q = q.filter(LichSuThaoTac.thoi_gian_thuc_hien <= datetime.strptime(den_ngay + 'T23:59:59', '%Y-%m-%dT%H:%M:%S'))

    pagination = q.order_by(LichSuThaoTac.thoi_gian_thuc_hien.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [_serialize_log(l) for l in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'per_page': per_page,
    })


@admin_bp.route('/api/meta', methods=['GET'])
@admin_required
def get_meta():
    """Trả về danh sách chức vụ và phòng ban để dùng trong form."""
    chuc_vus = ChucVu.query.all()
    phong_bans = PhongBan.query.all()
    return jsonify({
        'chuc_vus': [{'id': c.id_chuc_vu, 'ten': c.ten_chuc_vu} for c in chuc_vus],
        'phong_bans': [{'id': p.id_phong_ban, 'ten': p.ten_phong_ban} for p in phong_bans],
    })


# ── Serializers ────────────────────────────────────────────────────────────────

def _serialize_user(u: NguoiDung) -> dict:
    return {
        'id_nguoi_dung': u.id_nguoi_dung,
        'ten_dang_nhap': u.ten_dang_nhap,
        'ho_ten': u.ho_ten,
        'email': u.email,
        'chuc_vu': u.chuc_vu.ten_chuc_vu if u.chuc_vu else None,
        'id_chuc_vu': u.id_chuc_vu,
        'phong_ban': u.phong_ban.ten_phong_ban if u.phong_ban else None,
        'id_phong_ban': u.id_phong_ban,
        'trang_thai_hoat_dong': u.trang_thai_hoat_dong,
        'ngay_tao': u.ngay_tao.isoformat() if u.ngay_tao else None,
    }


def _serialize_label(l: NhanTaiLieu) -> dict:
    return {
        'id_nhan': l.id_nhan,
        'ten_nhan': l.ten_nhan,
        'mau_sac_hien_thi': l.mau_sac_hien_thi,
        'so_tai_lieu': len(l.tai_lieus),
    }


def _serialize_log(l: LichSuThaoTac) -> dict:
    user = NguoiDung.query.get(l.id_nguoi_dung)
    return {
        'id_log': l.id_log,
        'id_tai_lieu': l.id_tai_lieu,
        'hanh_dong': l.hanh_dong,
        'chi_tiet_thay_doi': l.chi_tiet_thay_doi,
        'thoi_gian_thuc_hien': l.thoi_gian_thuc_hien.isoformat() if l.thoi_gian_thuc_hien else None,
        'ten_nguoi_dung': user.ho_ten if user else f'ID:{l.id_nguoi_dung}',
    }


def _ghi_audit_admin(hanh_dong: str, chi_tiet: dict):
    """Ghi log cho hành động admin (không liên quan tài liệu cụ thể → id_tai_lieu=0)."""
    # Dùng id_tai_lieu=0 như một sentinel cho admin-level actions
    log = LichSuThaoTac(
        id_tai_lieu=0,
        id_nguoi_dung=session['user_id'],
        hanh_dong=f'ADMIN_{hanh_dong}',
        chi_tiet_thay_doi=json.dumps(chi_tiet, ensure_ascii=False),
    )
    db.session.add(log)
    db.session.commit()
