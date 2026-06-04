from PIL import Image
import pytesseract
import os

def ocr_image(path: str) -> str:
    """Perform OCR on image file and return extracted text."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    img = Image.open(path)
    try:
        # try Vietnamese model if available
        text = pytesseract.image_to_string(img, lang='vie')
    except Exception:
        text = pytesseract.image_to_string(img)
    return text
