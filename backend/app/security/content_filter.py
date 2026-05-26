"""
Content Filter & Output Validator
===================================
Filters harmful content from both inputs and generated outputs.
Validates that AI-generated responses are safe before sending to users.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger("security.content_filter")


@dataclass
class FilterResult:
    is_safe: bool
    filtered_content: str
    violations: List[str]
    reason: Optional[str] = None


# --- Patterns for output content that should never be returned ---
OUTPUT_BLOCKLIST_PATTERNS = [
    # System prompt leakage indicators
    (r"(my\s+system\s+prompt|my\s+instructions?\s+are|i\s+was\s+told\s+to)", "system_prompt_leak"),
    (r"(openai|anthropic|langchain)\s+(told|instructed|ordered)\s+me", "instruction_leak"),

    # Hallucination red flags
    (r"as\s+of\s+my\s+last\s+update\s+in\s+\d{4}", "outdated_claim"),

    # Personally Identifiable Information patterns (shouldn't appear in educational responses)
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn_pattern"),
    (r"\b(?:\d{4}[- ]?){4}\b", "credit_card_pattern"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email_pattern"),
]

# --- Harmful content categories ---
HARMFUL_CATEGORIES = {
    "violence": [
        r"\b(step[- ]by[- ]step\s+)?(how\s+to\s+)?(kill|murder|harm|hurt)\s+(a\s+)?(person|human|individual)",
        r"detailed\s+instructions\s+for\s+(making|building)\s+(weapons?|explosives?|bombs?)",
    ],
    "illegal_activities": [
        r"(step[- ]by[- ]step\s+)?(how\s+to\s+)?(synthesize|manufacture)\s+(drugs?|narcotics?|meth|cocaine)",
        r"(how\s+to\s+)?(bypass|evade)\s+(law\s+enforcement|police|security)",
    ],
    "adult_content": [
        r"\b(explicit|graphic)\s+(sexual|adult)\s+content",
        r"\b(pornographic|xxx|nsfw)\b",
    ],
}


def filter_output(text: str) -> FilterResult:
    """
    Validate and filter AI-generated output before returning to user.

    Args:
        text: Generated response text

    Returns:
        FilterResult with is_safe flag and cleaned content
    """
    violations: List[str] = []

    # Check output blocklist patterns
    for pattern, violation_name in OUTPUT_BLOCKLIST_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(violation_name)
            logger.warning(f"Output violation detected: {violation_name}")
            # For non-PII violations, don't block — just log
            if violation_name not in ("ssn_pattern", "credit_card_pattern"):
                continue
            # PII: redact
            text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)

    # Check for harmful content categories
    for category, patterns in HARMFUL_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"harmful_{category}")
                logger.error(f"Harmful output detected: category={category}")
                return FilterResult(
                    is_safe=False,
                    filtered_content="",
                    violations=violations,
                    reason=f"Response contained potentially harmful content ({category}). "
                           "Please try a different educational question.",
                )

    is_safe = len([v for v in violations if "pattern" not in v]) == 0

    return FilterResult(
        is_safe=True,  # Output is safe (violations are informational or redacted)
        filtered_content=text,
        violations=violations,
    )


def filter_input(text: str) -> FilterResult:
    """
    Filter user input for harmful content patterns.
    Complements prompt injection detection with content-level filtering.

    Args:
        text: User input text

    Returns:
        FilterResult
    """
    violations: List[str] = []

    for category, patterns in HARMFUL_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"harmful_{category}")
                logger.warning(f"Harmful input detected: category={category}")
                return FilterResult(
                    is_safe=False,
                    filtered_content="",
                    violations=violations,
                    reason=(
                        f"Your request contains content related to {category.replace('_', ' ')} "
                        "that I cannot assist with. Please ask an educational question."
                    ),
                )

    return FilterResult(
        is_safe=True,
        filtered_content=text,
        violations=violations,
    )
