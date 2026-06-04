"""
bo_xu_ly/nhan_dang_nlp.py
NER cho cơ quan ban hành.

Ưu tiên:
  1. VnCoreNLP (Java) — độ chính xác cao, cần cài JAR + models
  2. Regex heuristic — fallback khi chưa cài VnCoreNLP

Cài VnCoreNLP:
    pip install vncorenlp
    # Tải JAR + models:
    mkdir -p vncorenlp/models
    wget https://github.com/vncorenlp/VnCoreNLP/releases/download/v1.2/VnCoreNLP-1.2.jar -O vncorenlp/VnCoreNLP-1.2.jar
    wget https://raw.githubusercontent.com/vncorenlp/VnCoreNLP/master/models/wordsegmenter/vi-vocab -P vncorenlp/models/wordsegmenter/
    wget https://raw.githubusercontent.com/vncorenlp/VnCoreNLP/master/models/wordsegmenter/wordsegmenter.rdr -P vncorenlp/models/wordsegmenter/
    wget https://raw.githubusercontent.com/vncorenlp/VnCoreNLP/master/models/ner/vi-ner.rdr -P vncorenlp/models/ner/
    wget https://raw.githubusercontent.com/vncorenlp/VnCoreNLP/master/models/ner/vi-ner-vocab.rdr -P vncorenlp/models/ner/
    Đặt USE_VNCORENLP=true trong .env
"""
import re
import logging
import os

logger = logging.getLogger(__name__)

# ── Regex fallback ─────────────────────────────────────────────────────────────
PATTERN_CO_QUAN = re.compile(
    r'(Ủy ban nhân dân[^,\n]{0,80}|'
    r'Hội đồng nhân dân[^,\n]{0,80}|'
    r'Văn phòng[^,\n]{0,60}|'
    r'Bộ [A-Za-zÀ-ỹ\s]{3,40}|'
    r'Sở [A-Za-zÀ-ỹ\s]{3,40}|'
    r'Phòng [A-Za-zÀ-ỹ\s]{3,40}|'
    r'Ban [A-Za-zÀ-ỹ\s]{3,40}|'
    r'Cục [A-Za-zÀ-ỹ\s]{3,40}|'
    r'Chi cục [A-Za-zÀ-ỹ\s]{3,40}|'
    r'Trường [A-Za-zÀ-ỹ\s]{3,50}|'
    r'Bệnh viện [A-Za-zÀ-ỹ\s]{3,50}|'
    r'Giám đốc[^,\n]{0,60}|'
    r'Chủ tịch[^,\n]{0,60})',
    re.IGNORECASE
)

# ── VnCoreNLP singleton ────────────────────────────────────────────────────────
_vncorenlp_instance = None


def _get_vncorenlp():
    """Khởi tạo VnCoreNLP một lần, dùng lại cho các request sau."""
    global _vncorenlp_instance
    if _vncorenlp_instance is not None:
        return _vncorenlp_instance

    try:
        from config import Config
        if not Config.USE_VNCORENLP:
            return None

        jar = Config.VNCORENLP_JAR
        models_dir = Config.VNCORENLP_MODELS

        if not os.path.exists(jar):
            logger.warning(
                'VnCoreNLP JAR không tìm thấy tại %s. '
                'Dùng regex heuristic thay thế.\n'
                'Hướng dẫn cài: xem docstring đầu file bo_xu_ly/nhan_dang_nlp.py',
                jar,
            )
            return None

        import vncorenlp  # pip install vncorenlp
        _vncorenlp_instance = vncorenlp.VnCoreNLP(
            jar,
            annotators='wseg,ner',  # word segmentation + NER
            models_dir=models_dir,
        )
        logger.info('VnCoreNLP khởi tạo thành công')
        return _vncorenlp_instance

    except ImportError:
        logger.warning(
            'Thư viện vncorenlp chưa được cài (pip install vncorenlp). '
            'Dùng regex fallback.'
        )
        return None
    except Exception as exc:
        logger.warning('Không khởi tạo được VnCoreNLP: %s. Dùng regex fallback.', exc)
        return None


def _trich_xuat_ner_vncorenlp(text: str) -> str | None:
    """NER với VnCoreNLP — trả về chuỗi tên tổ chức đầu tiên."""
    rdrsegmenter = _get_vncorenlp()
    if rdrsegmenter is None:
        return None

    try:
        # Chỉ lấy 500 ký tự đầu để giảm thời gian xử lý
        short_text = text[:500]
        annotated = rdrsegmenter.annotate(short_text)
        # annotated['sentences'] là list các câu,
        # mỗi câu là list các token dict với keys: form, nerLabel, ...
        orgs = []
        current_org = []
        for sentence in (annotated.get('sentences') or []):
            for token in sentence:
                label = token.get('nerLabel', 'O')
                form = token.get('form', '')
                if label in ('B-ORG', 'I-ORG'):
                    current_org.append(form)
                else:
                    if current_org:
                        orgs.append(' '.join(current_org))
                        current_org = []
            if current_org:
                orgs.append(' '.join(current_org))
                current_org = []

        # Ưu tiên org dài nhất (thường là tên đầy đủ)
        if orgs:
            return max(orgs, key=len).replace('_', ' ').strip()
    except Exception as exc:
        logger.warning('VnCoreNLP NER lỗi: %s', exc)

    return None


def trich_xuat_co_quan(text: str) -> str | None:
    """
    Trích xuất cơ quan/người ban hành.
    Thử VnCoreNLP trước, nếu không có thì dùng regex.
    """
    # Thử VnCoreNLP
    result = _trich_xuat_ner_vncorenlp(text)
    if result:
        return result

    # Fallback regex
    matches = PATTERN_CO_QUAN.findall(text)
    if matches:
        # Clean and filter obvious noisy matches (skip ones containing 'Nội dung')
        cleaned = []
        for m in matches:
            c = m.strip()
            # split off trailing fragments like '\nNội dung' or ': Nội dung'
            c = re.split(r'\n|:|\\.|\\,', c)[0].strip()
            if not c:
                continue
            low = c.lower()
            if 'nội dung' in low or 'nội dung:' in low:
                continue
            cleaned.append(c)

        if cleaned:
            # prefer the longest (likely most complete) match
            return max(cleaned, key=len)
        # fallback to last raw match trimmed
        return matches[-1].strip()

    return None
