from app import create_app
from database import db
from backend.models import ChucVu, PhongBan, NguoiDung, LoaiTaiLieu
from backend.utils import hash_password, check_password


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        if not ChucVu.query.filter_by(ten_chuc_vu='QuanTriVien').first():
            cv = ChucVu(ten_chuc_vu='QuanTriVien')
            db.session.add(cv)
            db.session.commit()

        if not PhongBan.query.filter_by(ten_phong_ban='HanhChinh').first():
            pb = PhongBan(ma_phong_ban='PB001', ten_phong_ban='HanhChinh')
            db.session.add(pb)
            db.session.commit()

        admin = NguoiDung.query.filter_by(ten_dang_nhap='admin').first()
        if not admin:
            cv = ChucVu.query.filter_by(ten_chuc_vu='QuanTriVien').first()
            pb = PhongBan.query.first()
            admin = NguoiDung(
                ten_dang_nhap='admin',
                mat_khau_ma_hoa=hash_password('admin123'),
                ho_ten='Admin',
                email='admin@example.com',
                id_chuc_vu=cv.id_chuc_vu if cv else None,
                id_phong_ban=pb.id_phong_ban if pb else None,
                trang_thai_hoat_dong=True,
            )
            db.session.add(admin)
            db.session.commit()
        elif not check_password('admin123', admin.mat_khau_ma_hoa):
            admin.mat_khau_ma_hoa = hash_password('admin123')
            db.session.commit()

        # Add a couple of document types
        if not LoaiTaiLieu.query.first():
            db.session.add(LoaiTaiLieu(ten_loai='Công văn'))
            db.session.add(LoaiTaiLieu(ten_loai='Quyết định'))
            db.session.commit()

        print('Seed completed.')


if __name__ == '__main__':
    main()
