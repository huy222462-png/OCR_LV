import re
import unicodedata

def normalize_text(text: str) -> str:
    if not text:
        return ''
    # normalize unicode
    s = unicodedata.normalize('NFC', text)

    # common OCR artifacts fixes / post-processing
    # map characters that Tesseract often returns (Eth) to Vietnamese Đ/đ
    s = s.replace('\u00d0', 'Đ').replace('\u00f0', 'đ')
    s = s.replace('Ð', 'Đ').replace('ð', 'đ')

    # common noisy sequences and punctuation issues
    replacements = {
        '\\': '',
        '\\u2013': '-',
        '\\u2014': '-',
        '\u2013': '-',
        '\u2014': '-',
        'QOÐ': 'QĐ',
        'QOĐ': 'QĐ',
        'QO0': 'Q0',
        'OÐ': 'Đ',
        ' O0 ': ' O ',
        '\ufffd': '',
    }
    for k, v in replacements.items():
        s = s.replace(k, v)

    # common word-level OCR fixes (lower/upper-insensitive)
    COMMON_OCR_FIXES = {
        'quy che': 'quy chế',
        'quy che\b': 'quy chế',
        'trich yeu': 'trích yếu',
        'trich xuat': 'trích xuất',
        'trich yếu': 'trích yếu',
        'ban hanh': 'ban hành',
        'so hieu': 'số hiệu',
        'so:': 'Số:',
        'v/v': 'V/v',
        'vav': 'V/v',
        'vav:': 'V/v',
        'av:': 'V/v',
        'vv:': 'V/v',
        'v\/v': 'V/v',
    }
    for k, v in COMMON_OCR_FIXES.items():
        try:
            s = re.sub(r'\b' + k + r'\b', v, s, flags=re.IGNORECASE)
        except re.error:
            # if pattern invalid, skip
            s = s.replace(k, v)

    # unify newlines and spaces
    s = re.sub(r'[\t\r\n]+', '\n', s)
    s = re.sub(r'\s{2,}', ' ', s)
    # trim whitespace on each line
    s = '\n'.join([ln.strip() for ln in s.splitlines() if ln.strip()])
    return s
