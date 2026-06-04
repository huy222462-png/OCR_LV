import os
import logging
from typing import Dict

from bo_xu_ly.tien_xu_ly_anh import preprocess_image
from bo_xu_ly.nhan_dang_ocr import ocr_image
from bo_xu_ly.chuan_hoa_chuoi import normalize_text
from bo_xu_ly.trich_xuat_regex import extract_so_hieu, extract_ngay, extract_trich_yeu

logger = logging.getLogger(__name__)


def xu_ly_tai_lieu(file_path: str) -> Dict:
    """Orchestrate preprocessing -> OCR -> normalize -> extract.

    Returns dict with keys:
      so_hieu_van_ban, ngay_ban_hanh, co_quan_ban_hanh, trich_yeu_noi_dung,
      toan_van_chu_tho, missing_fields
    """
    result = {
        'so_hieu_van_ban': None,
        'ngay_ban_hanh': None,
        'co_quan_ban_hanh': None,
        'trich_yeu_noi_dung': None,
        'toan_van_chu_tho': None,
        'missing_fields': [],
    }

    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    try:
        proc = preprocess_image(file_path)
    except Exception as exc:
        logger.warning('Preprocess failed: %s', exc)
        proc = file_path

    try:
        raw = ocr_image(proc)
    except Exception as exc:
        logger.exception('OCR error: %s', exc)
        raw = ''

    norm = normalize_text(raw)
    result['toan_van_chu_tho'] = norm

    so = extract_so_hieu(norm)
    ngay = extract_ngay(norm)
    trich = extract_trich_yeu(norm)

    result['so_hieu_van_ban'] = so
    result['ngay_ban_hanh'] = ngay
    result['trich_yeu_noi_dung'] = trich

    # co_quan detection via simple heuristic: look for common organization words
    try:
        from bo_xu_ly.nhan_dang_nlp import trich_xuat_co_quan
        co = trich_xuat_co_quan(norm)
        result['co_quan_ban_hanh'] = co
    except Exception:
        result['co_quan_ban_hanh'] = None

    for k in ('so_hieu_van_ban', 'ngay_ban_hanh', 'co_quan_ban_hanh', 'trich_yeu_noi_dung'):
        if not result.get(k):
            result['missing_fields'].append(k)

    return result
