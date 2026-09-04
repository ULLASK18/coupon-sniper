"""
Simple regex-based coupon code detector.
No combinatorial mutations. No explosion.
"""
from __future__ import annotations

import re
from typing import Optional


class CouponDetector:
    """Detects coupon codes from text using configurable regex patterns."""

    def __init__(self, pattern: Optional[str] = None):
        # Primary: WORD-WORD style codes (e.g. LUCID-3RT213, ABCD-12345)
        self.primary_pattern = re.compile(
            pattern or r"\b[A-Z0-9]{3,}-[A-Z0-9]{3,}\b"
        )
        # Secondary: "code XYZ" or "code: XYZ" style mentions
        self.keyword_pattern = re.compile(
            r"(?:code|coupon|promo)[\s:\"\'=]+([A-Z0-9][A-Z0-9\-]{3,24})",
            re.IGNORECASE,
        )

    def detect(self, text: str) -> list[str]:
        """
        Extract coupon codes from text.
        Returns a deduplicated list of uppercase codes, ordered by appearance.
        """
        if not text:
            return []

        found: list[str] = []
        seen: set[str] = set()

        # 1. Primary regex matches
        for match in self.primary_pattern.finditer(text.upper()):
            code = match.group(0)
            if code not in seen:
                seen.add(code)
                found.append(code)

        # 2. Keyword-based matches (e.g. "code gs6lhz")
        for match in self.keyword_pattern.finditer(text):
            code = match.group(1).upper().strip()
            if code not in seen and len(code) >= 4:
                seen.add(code)
                found.append(code)

        return found

    def detect_from_ocr(self, ocr_text: str) -> list[str]:
        """
        Apply detection on OCR-extracted text.
        Same logic as detect(), but could be extended for OCR-specific cleanup.
        """
        if not ocr_text:
            return []
        # Clean up common OCR artifacts
        cleaned = ocr_text.replace("|", "I").replace("{", "(").replace("}", ")")
        return self.detect(cleaned)
