/* main.js — OCR Văn bản */

function showAlert(message, type = 'info') {
    const box = document.getElementById('alertBox');
    if (!box) return;
    box.className = `alert alert-${type}`;
    box.textContent = message;
    box.classList.remove('d-none');
}

// ── Upload + Poll Celery Task ────────────────────────────────────────────────

function initUploadPage() {
    const uploadForm = document.getElementById('uploadForm');
    const saveForm = document.getElementById('saveForm');
    if (!uploadForm) return;

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btnAnalyze');
        btn.disabled = true;
        btn.textContent = 'Đang tải lên...';

        const formData = new FormData(uploadForm);
        try {
            const res = await fetch('/api/v1/documents/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Lỗi tải lên');

            showPreview(data.preview_url, uploadForm.file.files[0]?.type);

            if (data.async && data.task_id) {
                // Bất đồng bộ: poll trạng thái Celery task
                showAlert('📤 Đã tải lên. Đang xử lý OCR...', 'info');
                btn.textContent = 'Đang phân tích OCR...';
                await pollTask(data.task_id, data.id_tai_lieu);
            } else {
                // Đồng bộ fallback hoặc Celery không khả dụng
                await fetchDocAndFill(data.id_tai_lieu);
                showAlert('✅ Phân tích hoàn tất. Vui lòng kiểm duyệt trước khi lưu.', 'success');
            }
        } catch (err) {
            showAlert(err.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Phân tích hệ thống';
        }
    });

    saveForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            id_tai_lieu: document.getElementById('docId').value,
            so_hieu_van_ban: document.getElementById('soHieu').value,
            ngay_ban_hanh: document.getElementById('ngayBanHanh').value,
            co_quan_ban_hanh: document.getElementById('coQuan').value,
            trich_yeu_noi_dung: document.getElementById('trichYeu').value,
            toan_van_chu_tho: document.getElementById('toanVan').value,
            id_loai_tai_lieu: document.getElementById('loaiSelect').value || null,
        };

        const res = await fetch('/api/v1/documents/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        showAlert(res.ok ? data.message : (data.error || 'Lỗi lưu trữ'), res.ok ? 'success' : 'danger');
    });
}

/**
 * Poll Celery task mỗi 2s cho đến khi SUCCESS / FAILURE.
 */
async function pollTask(taskId, docId) {
    const MAX_WAIT = 120_000; // 2 phút
    const INTERVAL = 2_000;
    const started = Date.now();

    return new Promise((resolve) => {
        const timer = setInterval(async () => {
            try {
                const r = await fetch(`/api/v1/tasks/${taskId}`);
                const data = await r.json();

                if (data.state === 'SUCCESS') {
                    clearInterval(timer);
                    await fetchDocAndFill(docId);
                    const missing = data.result?.missing_fields || [];
                    showAlert(
                        missing.length
                            ? `✅ OCR xong. Thiếu: ${missing.join(', ')}. Vui lòng bổ sung thủ công.`
                            : '✅ Phân tích OCR hoàn tất. Vui lòng kiểm duyệt trước khi lưu.',
                        'success'
                    );
                    resolve(data.result);

                } else if (data.state === 'FAILURE') {
                    clearInterval(timer);
                    showAlert('❌ OCR thất bại. Vui lòng nhập thủ công.', 'danger');
                    await fetchDocAndFill(docId);
                    resolve(null);

                } else if (Date.now() - started > MAX_WAIT) {
                    clearInterval(timer);
                    showAlert('⏰ Quá thời gian chờ. Thử tải lại trang.', 'warning');
                    resolve(null);
                }
                // PENDING / STARTED / RETRY → tiếp tục poll
            } catch {
                // Bỏ qua lỗi mạng tạm thời
            }
        }, INTERVAL);
    });
}

/**
 * Lấy thông tin tài liệu từ API và điền vào form kiểm duyệt.
 */
async function fetchDocAndFill(docId) {
    const r = await fetch(`/api/v1/documents/${docId}`);
    if (!r.ok) return;
    const doc = await r.json();
    fillExtractedForm({
        id_tai_lieu: doc.id_tai_lieu,
        so_hieu_van_ban: doc.so_hieu_van_ban,
        ngay_ban_hanh: doc.ngay_ban_hanh,
        co_quan_ban_hanh: doc.co_quan_ban_hanh,
        trich_yeu_noi_dung: doc.trich_yeu_noi_dung,
        toan_van_chu_tho: doc.toan_van_chu_tho,
        missing_fields: [],
    });
}

function fillExtractedForm(data) {
    document.getElementById('formCard').classList.remove('d-none');
    document.getElementById('docId').value = data.id_tai_lieu;
    document.getElementById('soHieu').value = data.so_hieu_van_ban || '';
    document.getElementById('ngayBanHanh').value = data.ngay_ban_hanh || '';
    document.getElementById('coQuan').value = data.co_quan_ban_hanh || '';
    document.getElementById('trichYeu').value = data.trich_yeu_noi_dung || '';
    document.getElementById('toanVan').value = data.toan_van_chu_tho || '';

    document.querySelectorAll('.field-input').forEach(el => el.classList.remove('field-missing'));
    (data.missing_fields || []).forEach(field => {
        const map = {
            so_hieu_van_ban: 'soHieu',
            ngay_ban_hanh: 'ngayBanHanh',
            co_quan_ban_hanh: 'coQuan',
            trich_yeu_noi_dung: 'trichYeu',
        };
        const id = map[field];
        if (id) document.getElementById(id)?.classList.add('field-missing');
    });
}

function showPreview(url, mimeType) {
    document.getElementById('previewCard').classList.remove('d-none');
    const img = document.getElementById('previewImg');
    const pdf = document.getElementById('previewPdf');
    if (mimeType === 'application/pdf') {
        img.classList.add('d-none');
        pdf.classList.remove('d-none');
        pdf.src = url;
    } else {
        pdf.classList.add('d-none');
        img.classList.remove('d-none');
        img.src = url + '?t=' + Date.now();
    }
}

// ── Search Page ───────────────────────────────────────────────────────────────

function initSearchPage() {
    const form = document.getElementById('searchForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const params = new URLSearchParams(new FormData(form));
        const res = await fetch('/api/v1/documents/search?' + params.toString());
        const data = await res.json();
        const tbody = document.getElementById('resultBody');
        tbody.innerHTML = '';

        if (!data.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Không tìm thấy kết quả</td></tr>';
            return;
        }

        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.so_hieu_van_ban || '-'}</td>
                <td>${row.ngay_ban_hanh || '-'}</td>
                <td>${row.trich_yeu_noi_dung || ''}</td>
                <td>${row.ten_loai || '-'}</td>
                <td><span class="badge bg-success">${row.trang_thai}</span></td>`;
            tbody.appendChild(tr);
        });
    });
}
