"""
Prompt Injection Detection
===========================
Detects and blocks prompt injection attacks, jailbreak attempts,
system prompt extraction, and role manipulation attacks.

Detection Strategies:
1. Pattern-based matching (regex rules)
2. Keyword blacklist matching
3. Structural anomaly detection
4. Semantic similarity (heuristic)
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from app.utils.logger import get_logger

logger = get_logger("security.prompt_injection")


class ThreatLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InjectionDetectionResult:
    is_safe: bool
    threat_level: ThreatLevel
    triggered_rules: List[str]
    safe_message: str
    original_query: str

    def __bool__(self):
        return self.is_safe


# ==============================================================
# DETECTION RULES
# ==============================================================

# High-severity injection patterns
CRITICAL_PATTERNS = [
    # System prompt extraction
    (r"ignore\s+(previous|all|prior|above)\s+instructions?", "ignore_instructions"),
    (r"disregard\s+(previous|all|prior|above|your)\s+instructions?", "disregard_instructions"),
    (r"forget\s+(previous|all|prior|above|your)\s+instructions?", "forget_instructions"),
    (r"override\s+(your|all|previous)\s+(instructions?|rules?|guidelines?)", "override_instructions"),

    # System prompt leakage
    (r"(reveal|show|print|output|display|repeat)\s+(your\s+)?(system\s+prompt|instructions?|prompt)", "reveal_system_prompt"),
    (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?|guidelines?)", "expose_system_prompt"),
    (r"(tell|show)\s+me\s+(your\s+)?(internal|hidden|secret)\s+(prompt|instructions?)", "expose_hidden_prompt"),

    # Role manipulation
    (r"you\s+are\s+now\s+(a\s+)?(different|new|evil|unrestricted)", "role_manipulation"),
    (r"act\s+as\s+(an?\s+)?(unrestricted|jailbroken|evil|dan|dna|dev|developer\s+mode)", "jailbreak_persona"),
    (r"pretend\s+(you\s+are|to\s+be)\s+(an?\s+)?(unrestricted|evil|malicious)", "pretend_evil"),
    (r"(DAN|JAILBREAK|DEVELOPER\s+MODE|UNRESTRICTED\s+MODE)", "jailbreak_keyword"),

    # Delimiter injection
    (r"```\s*(system|user|assistant)\s*\n", "delimiter_injection"),
    (r"<\|?(system|user|assistant|end|start)\|?>", "token_injection"),
    (r"\[INST\]|\[\/INST\]|<<SYS>>|<\/SYS>", "llama_token_injection"),

    # Command injection patterns
    (r"now\s+output\s+(the\s+)?following", "command_output"),
    (r"translate\s+(the\s+)?above\s+(to|into)", "translation_attack"),
]

# Medium-severity suspicious patterns
MEDIUM_PATTERNS = [
    (r"what\s+(would|will)\s+you\s+do\s+if\s+(there\s+were|you\s+had)\s+no\s+rules?", "no_rules_scenario"),
    (r"(bypass|circumvent|avoid|evade)\s+(your\s+)?(safety|filter|restriction|guideline)", "bypass_safety"),
    (r"(disable|turn\s+off|remove)\s+(your\s+)?(filter|safety|restriction|limit)", "disable_filter"),
    (r"in\s+(hypothetical|fictional|imaginary)\s+world\s+where\s+you\s+(can|have\s+no)", "hypothetical_bypass"),
    (r"for\s+educational\s+purposes\s+only\s*[,:]?\s*(explain|show|tell)\s+how\s+to", "edu_bypass"),
    (r"as\s+a\s+researcher\s*(,|;)?\s*tell\s+me\s+how\s+to", "researcher_bypass"),
    (r"my\s+grandmother\s+used\s+to\s+tell\s+me", "grandma_jailbreak"),
    (r"(write|create|generate)\s+(a\s+)?story\s+where\s+(the\s+)?character\s+(explains?|shows?)", "story_bypass"),
]

# Low-severity suspicious keywords
SUSPICIOUS_KEYWORDS = [
    "jailbreak", "prompt leak", "system message", "hidden instruction",
    "base64 decode", "roleplay as", "no restrictions", "without filters",
    "unfiltered response", "raw output", "ignore ethics",
]

# Harmful content keywords
HARMFUL_CONTENT_PATTERNS = [
    (r"\b(synthesize|manufacture|create|make|build)\s+(meth|cocaine|heroin|fentanyl|explosives?|bombs?)\b", "drug_weapon_synthesis"),
    (r"\b(how\s+to\s+)(hack|crack|exploit|break\s+into)\s+(a\s+)?(computer|server|database|account|system)\b", "hacking_instructions"),
    (r"\b(child|minor|underage)\s+(pornography|exploitation|sexual|nude)\b", "csam_content"),
    (r"\b(kill|murder|assassinate)\s+(a\s+specific\s+)?(person|individual|someone)\b", "violence_planning"),
    (r"\b(steal|rob|fraud|scam)\s+(credit\s+card|identity|money|bank)\b", "financial_crime"),
]


class PromptInjectionDetector:
    """
    Multi-layer prompt injection detector.
    Checks input against patterns, keywords, and structural anomalies.
    """

    def __init__(self):
        # Compile patterns for performance
        self._critical = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), rule)
            for pattern, rule in CRITICAL_PATTERNS
        ]
        self._medium = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), rule)
            for pattern, rule in MEDIUM_PATTERNS
        ]
        self._harmful = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), rule)
            for pattern, rule in HARMFUL_CONTENT_PATTERNS
        ]

    def detect(self, text: str) -> InjectionDetectionResult:
        """
        Run full injection detection pipeline on input text.

        Returns:
            InjectionDetectionResult with threat level and triggered rules
        """
        triggered_rules: List[str] = []
        threat_level = ThreatLevel.SAFE

        # --- Check critical patterns ---
        for pattern, rule in self._critical:
            if pattern.search(text):
                triggered_rules.append(rule)
                threat_level = ThreatLevel.CRITICAL
                logger.warning(
                    f"CRITICAL injection detected: rule='{rule}' | "
                    f"text_preview='{text[:100]}'"
                )

        # --- Check harmful content ---
        for pattern, rule in self._harmful:
            if pattern.search(text):
                triggered_rules.append(rule)
                if threat_level != ThreatLevel.CRITICAL:
                    threat_level = ThreatLevel.HIGH
                logger.warning(f"Harmful content detected: rule='{rule}'")

        # --- Check medium patterns ---
        if threat_level == ThreatLevel.SAFE:
            for pattern, rule in self._medium:
                if pattern.search(text):
                    triggered_rules.append(rule)
                    threat_level = ThreatLevel.MEDIUM

        # --- Check suspicious keywords ---
        if threat_level == ThreatLevel.SAFE:
            text_lower = text.lower()
            for keyword in SUSPICIOUS_KEYWORDS:
                if keyword in text_lower:
                    triggered_rules.append(f"keyword:{keyword}")
                    threat_level = ThreatLevel.LOW

        # --- Check structural anomalies ---
        structural_issues = self._check_structural_anomalies(text)
        if structural_issues:
            triggered_rules.extend(structural_issues)
            if threat_level == ThreatLevel.SAFE:
                threat_level = ThreatLevel.LOW

        is_safe = threat_level in (ThreatLevel.SAFE, ThreatLevel.LOW)

        return InjectionDetectionResult(
            is_safe=is_safe,
            threat_level=threat_level,
            triggered_rules=triggered_rules,
            safe_message=self._get_safe_message(threat_level, triggered_rules),
            original_query=text,
        )

    def _check_structural_anomalies(self, text: str) -> List[str]:
        """Detect structural anomalies that may indicate injection."""
        issues = []

        # Unusually many special characters
        special_char_ratio = sum(1 for c in text if not c.isalnum() and c not in " \n.,?!-'\"") / max(len(text), 1)
        if special_char_ratio > 0.3:
            issues.append("high_special_char_ratio")

        # Very long single line (may hide injection)
        if any(len(line) > 500 for line in text.split("\n")):
            issues.append("excessively_long_line")

        # Repeated character sequences (obfuscation)
        if re.search(r"(.)\1{10,}", text):
            issues.append("repeated_char_sequence")

        # Multiple language switching (may indicate injection attempt)
        has_rtl = bool(re.search(r"[؀-ۿݐ-ݿ]", text))
        has_ltr_dominant = len(re.findall(r"[a-zA-Z]", text)) > 10
        if has_rtl and has_ltr_dominant and len(text) < 100:
            issues.append("mixed_script_anomaly")

        return issues

    def _get_safe_message(self, threat_level: ThreatLevel, rules: List[str]) -> str:
        """Generate an appropriate safe response message for blocked requests."""
        if threat_level == ThreatLevel.CRITICAL:
            return (
                "I'm unable to process this request. It appears to contain instructions "
                "that attempt to override my guidelines or extract system information. "
                "Please ask an educational question and I'll be happy to help."
            )
        elif threat_level == ThreatLevel.HIGH:
            return (
                "This request contains content that I'm not able to assist with. "
                "I'm designed to help with educational topics. "
                "Please rephrase your question."
            )
        elif threat_level == ThreatLevel.MEDIUM:
            return (
                "Your request contains patterns that appear to attempt to bypass "
                "my safety guidelines. I'm here to help with legitimate educational "
                "questions — please try again."
            )
        else:
            return (
                "Your request could not be processed as submitted. "
                "Please rephrase your educational question."
            )


# Singleton detector instance
detector = PromptInjectionDetector()


def check_prompt_injection(text: str) -> InjectionDetectionResult:
    """
    Main entry point for prompt injection checking.

    Args:
        text: User input text to check

    Returns:
        InjectionDetectionResult (bool-compatible: True = safe)
    """
    return detector.detect(text)
