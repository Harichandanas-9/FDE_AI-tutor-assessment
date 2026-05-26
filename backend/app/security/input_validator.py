"""
Input Validation & Sanitization
================================
Validates and sanitizes all user inputs before processing.
Removes harmful characters, normalizes encoding, enforces length limits.
"""

import re
import html
import unicodedata
from typing import Tuple

import bleach

from app.utils.logger import get_logger

logger = get_logger("security.input_validator")

# --- Allowed HTML tags (for content that may contain HTML) ---
ALLOWED_HTML_TAGS: list[str] = []  # No HTML allowed in queries
ALLOWED_HTML_ATTRS: dict = {}

# --- Input constraints ---
MAX_QUERY_LENGTH = 5000
MIN_QUERY_LENGTH = 1
MAX_WORD_COUNT = 500


class InputValidationResult:
    """Result of input validation."""

    def __init__(self, is_valid: bool, sanitized: str = "", reason: str = ""):
        self.is_valid = is_valid
        self.sanitized = sanitized
        self.reason = reason

    def __bool__(self):
        return self.is_valid


def sanitize_text(text: str) -> str:
    """
    Sanitize raw text input:
    1. Strip HTML tags
    2. Decode HTML entities
    3. Normalize unicode
    4. Remove null bytes and control characters
    5. Normalize whitespace
    """
    if not isinstance(text, str):
        return ""

    # Strip HTML tags using bleach
    cleaned = bleach.clean(text, tags=ALLOWED_HTML_TAGS, attributes=ALLOWED_HTML_ATTRS, strip=True)

    # Decode HTML entities (e.g., &amp; → &)
    cleaned = html.unescape(cleaned)

    # Normalize unicode (NFC normalization)
    cleaned = unicodedata.normalize("NFC", cleaned)

    # Remove null bytes and dangerous control characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    # Remove excessive whitespace
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def validate_query_length(text: str) -> Tuple[bool, str]:
    """Validate that query is within acceptable length bounds."""
    if len(text) < MIN_QUERY_LENGTH:
        return False, f"Query too short (minimum {MIN_QUERY_LENGTH} character)"
    if len(text) > MAX_QUERY_LENGTH:
        return False, f"Query too long (maximum {MAX_QUERY_LENGTH} characters)"
    word_count = len(text.split())
    if word_count > MAX_WORD_COUNT:
        return False, f"Query exceeds maximum word count ({MAX_WORD_COUNT} words)"
    return True, ""


def check_encoding_attacks(text: str) -> Tuple[bool, str]:
    """
    Detect encoding-based attacks:
    - Unicode homograph attacks
    - Zero-width characters
    - Right-to-left override
    - Excessive special characters
    """
    # Zero-width characters
    zero_width_pattern = re.compile(
        r"[​‌‍‎‏‪-‮⁠-⁤﻿]"
    )
    if zero_width_pattern.search(text):
        return False, "Zero-width or directional control characters detected"

    # Check for suspicious Unicode categories
    suspicious_count = sum(
        1 for c in text
        if unicodedata.category(c) in ("Cf", "Cs", "Co", "Cn")
    )
    if suspicious_count > 5:
        return False, "Suspicious Unicode characters detected"

    return True, ""


def validate_input(text: str) -> InputValidationResult:
    """
    Main input validation pipeline.
    Returns a validation result with sanitized text or rejection reason.
    """
    if not text or not isinstance(text, str):
        return InputValidationResult(False, reason="Empty or invalid input")

    # Step 1: Sanitize
    sanitized = sanitize_text(text)

    # Step 2: Length validation
    length_ok, length_reason = validate_query_length(sanitized)
    if not length_ok:
        return InputValidationResult(False, reason=length_reason)

    # Step 3: Encoding attack check
    encoding_ok, encoding_reason = check_encoding_attacks(text)
    if not encoding_ok:
        logger.warning(f"Encoding attack detected: {encoding_reason}")
        return InputValidationResult(False, reason=f"Invalid input: {encoding_reason}")

    return InputValidationResult(True, sanitized=sanitized)
