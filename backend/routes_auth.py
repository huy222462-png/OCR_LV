from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from database import db
from backend.models import NguoiDung
from backend.utils import check_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form or request.get_json() or {}
        username = data.get('ten_dang_nhap') or data.get('username')
        password = data.get('mat_khau') or data.get('password')
        user = NguoiDung.query.filter_by(ten_dang_nhap=username).first()
        if user and check_password(password, user.mat_khau_ma_hoa):
            session['user_id'] = user.id_nguoi_dung
            session['chuc_vu'] = user.chuc_vu.ten_chuc_vu if user.chuc_vu else ''
            session['ho_ten'] = user.ho_ten or user.ten_dang_nhap
            return redirect(url_for('admin.admin_dashboard'))
        return render_template(
            'auth/login.html',
            error='Đăng nhập thất bại. Kiểm tra lại tên đăng nhập và mật khẩu.',
            username_value=username or '',
        ), 401
    return render_template('auth/login.html', error=None, username_value='')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return 'Dashboard'
