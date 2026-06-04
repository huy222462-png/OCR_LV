Chưa có / Triển khai chưa đầy đủ (ưu tiên):

Core processing pipeline (BLOCKER, độ ưu tiên cao)

Thiếu module/entrypoint bo_xu_ly.xu_ly_tai_lieu và các bước con:
bo_xu_ly/tien_xu_ly_anh.py — deskew, grayscale, Otsu, denoise (OpenCV).
bo_xu_ly/nhan_dang_ocr.py — pytesseract wrapper + config (vi traineddata).
bo_xu_ly/chuan_hoa_chuoi.py — text normalization (whitespace, unicode, punctuation).
bo_xu_ly/trich_xuat_regex.py — regex functions: extract_so_hieu, extract_ngay, extract_trich_yeu.
bo_xu_ly/xu_ly_tai_lieu.py (hoặc __init__.py xuất hàm xu_ly_tai_lieu) — phối hợp các bước trên, trả dict: so_hieu_van_ban, ngay_ban_hanh (YYYY-MM-DD), co_quan_ban_hanh, trich_yeu_noi_dung, toan_van_chu_tho, missing_fields.
Hiện Celery gọi bo_xu_ly.xu_ly_tai_lieu nhưng file này chưa có → pipeline không chạy.
Trích xuất (Regex) — cần triển khai cụ thể

Văn bản chỉ ra các mẫu chính xác (ví dụ Số: .../QĐ-..., ngày), nhưng repo chưa có trich_xuat_regex.py với bộ regex đã test/unit.
Cần unit tests để đạt yêu cầu độ chính xác theo tài liệu.
Tiền xử lý ảnh (OpenCV) — chưa triển khai

pdf_to_image có, nhưng chưa có deskew / binarize / gaussian filter như đề xuất.
Full‑text search / chỉ mục nâng cao

Tài liệu đề xuất Full‑Text Search và chỉ mục. Hiện search dùng ilike trên 2 cột (fallback). Nếu cần FTS (SQL Server Full-Text Index hoặc PG fulltext), cần script DDL + migration.
Bảo mật file upload / media access

Hiện allowed_file kiểm tra đuôi file, thiếu MIME/magic validation; nginx comment gợi ý X-Accel-Redirect nhưng chưa bật/triển khai để bảo vệ media/uploads. Cần:
Kiểm tra magic bytes (MIME) trước lưu.
Lưu ngoài webroot hoặc dùng X‑Accel + sendfile bảo vệ.
Giới hạn kích thước, sanitize tên file (hiện dùng UUID — tốt).
Cấu hình VnCoreNLP & models

nhan_dang_nlp.py đã có fallback, nhưng nếu muốn NER chính xác cần hướng dẫn tải JAR/models và bật USE_VNCORENLP=true (docstring đã có).
Scripts & SQL DDL

Tài liệu có DDL (tables, FTS, trigger). Repo chưa có file SQL sẵn (docs/db_schema.sql). Nên thêm để deploy vào SQL Server.
Testing / Evaluation

Chưa thấy scripts để tính CER / F1 trên tập mẫu (tài liệu đề nghị dataset 50–100). Cần tool nhỏ để đo accuracy.
Non‑functional: HTTPS, session timeout, RBAC chi tiết

nginx có cấu hình comment cho HTTPS — cần bật certs.
RBAC: model tồn tại; code có check cơ bản (ví dụ save_document kiểm quyền) nhưng cần kiểm tra toàn bộ route/operation để enforce theo spec (Staff vs Admin).
Session timeout, CSRF, Content Security Policy chưa đánh giá chi tiết.