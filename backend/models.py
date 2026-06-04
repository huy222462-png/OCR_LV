from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from database import db


class ChucVu(db.Model):
    __tablename__ = 'chuc_vu'
    id_chuc_vu = db.Column(db.Integer, primary_key=True)
    ten_chuc_vu = db.Column(db.String(100), nullable=False)


class PhongBan(db.Model):
    __tablename__ = 'phong_ban'
    id_phong_ban = db.Column(db.Integer, primary_key=True)
    ma_phong_ban = db.Column(db.String(50), nullable=False)
    ten_phong_ban = db.Column(db.String(150), nullable=False)
    mo_ta = db.Column(db.String(255))


class NguoiDung(db.Model):
    __tablename__ = 'nguoi_dung'
    id_nguoi_dung = db.Column(db.Integer, primary_key=True)
    ten_dang_nhap = db.Column(db.String(80), unique=True, nullable=False)
    mat_khau_ma_hoa = db.Column(db.String(200), nullable=False)
    ho_ten = db.Column(db.String(200))
    email = db.Column(db.String(200))
    id_chuc_vu = db.Column(db.Integer, db.ForeignKey('chuc_vu.id_chuc_vu'))
    chuc_vu = relationship('ChucVu')
    id_phong_ban = db.Column(db.Integer, db.ForeignKey('phong_ban.id_phong_ban'))
    phong_ban = relationship('PhongBan')
    trang_thai_hoat_dong = db.Column(db.Boolean, default=True)
    ngay_tao = db.Column(db.DateTime, default=datetime.utcnow)


class LoaiTaiLieu(db.Model):
    __tablename__ = 'loai_tai_lieu'
    id_loai_tai_lieu = db.Column(db.Integer, primary_key=True)
    ten_loai = db.Column(db.String(100), nullable=False)


class TaiLieu(db.Model):
    __tablename__ = 'tai_lieu'
    id_tai_lieu = db.Column(db.Integer, primary_key=True)
    id_loai_tai_lieu = db.Column(db.Integer, db.ForeignKey('loai_tai_lieu.id_loai_tai_lieu'))
    loai_tai_lieu = relationship('LoaiTaiLieu')
    ten_file_goc = db.Column(db.String(300))
    duong_dan_file = db.Column(db.String(500))
    trang_thai = db.Column(db.String(50))
    id_nguoi_tao = db.Column(db.Integer)
    so_hieu_van_ban = db.Column(db.String(200))
    ngay_ban_hanh = db.Column(db.Date)
    co_quan_ban_hanh = db.Column(db.String(200))
    trich_yeu_noi_dung = db.Column(db.Text)
    toan_van_chu_tho = db.Column(db.Text)
    ngay_day_len = db.Column(db.DateTime)
    ngay_cap_nhat_cuoi = db.Column(db.DateTime)
    id_nguoi_cap_nhat = db.Column(db.Integer)


class NhanTaiLieu(db.Model):
    __tablename__ = 'nhan_tai_lieu'
    id_nhan = db.Column(db.Integer, primary_key=True)
    ten_nhan = db.Column(db.String(100), nullable=False)
    mau_sac_hien_thi = db.Column(db.String(20), default='#6c757d')
    tai_lieus = relationship('TaiLieu', secondary='tai_lieu_nhan', backref='nhans')


class TaiLieuNhan(db.Model):
    __tablename__ = 'tai_lieu_nhan'
    id = db.Column(db.Integer, primary_key=True)
    id_tai_lieu = db.Column(db.Integer, db.ForeignKey('tai_lieu.id_tai_lieu'))
    id_nhan = db.Column(db.Integer, db.ForeignKey('nhan_tai_lieu.id_nhan'))


class LichSuThaoTac(db.Model):
    __tablename__ = 'lich_su_thao_tac'
    id_log = db.Column(db.Integer, primary_key=True)
    id_tai_lieu = db.Column(db.Integer)
    id_nguoi_dung = db.Column(db.Integer)
    hanh_dong = db.Column(db.String(200))
    chi_tiet_thay_doi = db.Column(db.Text)
    thoi_gian_thuc_hien = db.Column(db.DateTime, default=datetime.utcnow)
