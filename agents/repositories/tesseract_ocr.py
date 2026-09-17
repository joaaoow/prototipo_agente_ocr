import io
import os

import pytesseract
from PIL import Image

TESSERACT_LANG = os.getenv("TESSERACT_LANG", "por")

_tesseract_cmd = os.getenv("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


def extract_text(image_bytes: bytes) -> str:
    """OCR bruto via Tesseract — fallback offline usado quando a Gemini API falha (sem rede/cota/erro)."""
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image, lang=TESSERACT_LANG).strip()
