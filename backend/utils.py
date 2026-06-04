import os
import io
import uuid
from functools import wraps
from datetime import datetime

from flask import session, redirect, url_for, request, current_app
import bcrypt
import fitz  # PyMuPDF


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename: str, allowed_set) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def save_upload(file_obj, upload_folder: str):
    os.makedirs(upload_folder, exist_ok=True)
    original = file_obj.filename
    ext = original.rsplit('.', 1)[-1]
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(upload_folder, name)
    file_obj.save(path)
    return original, path


def pdf_to_image(pdf_path: str, upload_folder: str) -> str:
    """Convert first page of PDF to PNG and return image path."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    out = os.path.splitext(os.path.basename(pdf_path))[0] + '.png'
    out_path = os.path.join(upload_folder, out)
    pix.save(out_path)
    return out_path
