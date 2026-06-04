import re
from datetime import datetime


def _normalize_date(parts):
    # Try common formats into YYYY-MM-DD
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d %m %Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(parts, fmt).date().isoformat()
        except Exception:
            continue
    # fallback: try to extract digits
    m = re.search(r'(\d{1,4})[^0-9]+(\d{1,2})[^0-9]+(\d{2,4})', parts)
    if m:
        d, mo, y = m.groups()
        if len(y) == 2:
            y = '20' + y
        try:
            return datetime(int(y), int(mo), int(d)).date().isoformat()
        except Exception:
            return None
    return None


def extract_so_hieu(text: str) -> str | None:
    if not text:
        return None
    # e.g. Số: 123/QĐ-UBND or Số 123/QĐ-UBND — allow unicode letters
    m = re.search(r'(?:Số|So)[:\s]*([0-9\w/\-\.]+)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # try lines that look like document id (digits/slash/pattern)
    m2 = re.search(r'\b([0-9]{1,5}/[\w\-\.]+)\b', text)
    if m2:
        return m2.group(1)
    return None


def extract_ngay(text: str) -> str | None:
    if not text:
        return None
    # look for patterns like Ngày 12 tháng 5 năm 2024 or 12/05/2024
    m = re.search(r'([0-3]?\d[\-/\.][0-1]?\d[\-/\.]\d{2,4})', text)
    if m:
        return _normalize_date(m.group(1))
    m2 = re.search(r'Ngày\s*([0-3]?\d)\s*(?:tháng|thang)\s*([0-1]?\d)\s*(?:năm|nam)\s*(\d{4})', text, re.IGNORECASE)
    if m2:
        d, mo, y = m2.groups()
        try:
            return datetime(int(y), int(mo), int(d)).date().isoformat()
        except Exception:
            return None
    return None


def extract_trich_yeu(text: str) -> str | None:
    if not text:
        return None
    # try common prefixes like 'V/v:', 'V:', or lines containing 'Về'
    m = re.search(r'^(?:V\/?v|V|v)[\s\-:\u2013]*(.+)$', text, re.MULTILINE)
    if m:
        # strip common prefixes like 'V/v' or leading punctuation
        candidate = m.group(1).strip()
        # clean OCR noise at start (e.g., 'VAv', 'Av', 'Av:')
        candidate = re.sub(r'^[^A-Za-z0-9À-ỹ]+', '', candidate)
        candidate = re.sub(r'^[VvAaws:]{1,4}\s*[:\-]*', '', candidate)
        # remove leading 'Nội dung' if it was attached
        candidate = re.sub(r'^(?:Nội dung\s*[:\-]?\s*)', '', candidate, flags=re.IGNORECASE)
        if 'về' in candidate.lower() or 've' in candidate.lower():
            return candidate
        return candidate
    # fallback: first non-empty line that is not too long
    for line in text.splitlines():
        s = line.strip()
        if s and len(s) < 200:
            # skip lines that look like header dates or numbers
            if re.search(r'\b(Ngày|Số|So)\b', s, re.IGNORECASE):
                continue
            return s
    return None
