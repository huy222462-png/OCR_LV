import os
import cv2
import numpy as np

def _deskew(image):
    # compute moments to estimate skew from non-empty pixels
    coords = np.column_stack(np.where(image > 0))
    if coords.shape[0] < 10:
        return image
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return rotated


def preprocess_image(path: str) -> str:
    """Load image, convert to grayscale, denoise, binarize, deskew and save.

    Returns path to preprocessed PNG image.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('Cannot read image: ' + path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # denoise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # adaptive threshold / Otsu
    _, th = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # deskew
    try:
        deskewed = _deskew(th)
    except Exception:
        deskewed = th

    out_name = os.path.splitext(os.path.basename(path))[0] + '_proc.png'
    out_path = os.path.join(os.path.dirname(path), out_name)
    # use imencode + tofile to support Windows unicode paths
    _, encoded = cv2.imencode('.png', deskewed)
    encoded.tofile(out_path)
    return out_path
