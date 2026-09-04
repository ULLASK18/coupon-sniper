"""
EasyOCR-based text extraction from images optimized for high-speed inference.
"""
from __future__ import annotations

import logging
import threading
# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
import numpy as np
from typing import Optional, Union

logger = logging.getLogger("coupon_sniper.ocr")


class OCREngine:
    """Fast EasyOCR wrapper for extracting text from tweet images."""

    def __init__(self):
        self._reader = None
        self._lock = threading.Lock()

    def _get_reader(self):
        """Initialize EasyOCR reader on first use."""
        if self._reader is None:
            with self._lock:
                if self._reader is None:
                    try:
                        # pyrefly: ignore [missing-import]
                        import easyocr
                        logger.info("Pre-warming EasyOCR reader...")
                        self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                        logger.info("EasyOCR reader ready.")
                    except ImportError:
                        logger.error("EasyOCR is not installed. Run: pip install easyocr")
                        raise
        return self._reader

    def warmup(self) -> None:
        """Asynchronously pre-load EasyOCR model into RAM on startup."""
        threading.Thread(target=self._get_reader, daemon=True, name="OCRPrewarmThread").start()

    def extract_text(self, image_source: Union[str, bytes]) -> str:
        """
        Extract text from an image file path or raw image bytes.
        Preprocesses image with OpenCV (grayscale + resize) for <300ms inference speed.
        """
        try:
            reader = self._get_reader()

            # Load image into numpy array
            if isinstance(image_source, bytes):
                img_np = cv2.imdecode(np.frombuffer(image_source, np.uint8), cv2.IMREAD_COLOR)
            else:
                img_np = cv2.imread(image_source)

            if img_np is None:
                return ""

            # Downscale & grayscale for fast OCR
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2]
            if w > 800:
                new_h = int(h * (800.0 / w))
                gray = cv2.resize(gray, (800, new_h), interpolation=cv2.INTER_AREA)

            # Fast inference
            results = reader.readtext(gray, detail=0, canvas_size=800, mag_ratio=1.0)
            combined = " ".join(results)
            logger.info(f"OCR extracted: '{combined[:200]}'")
            return combined
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

