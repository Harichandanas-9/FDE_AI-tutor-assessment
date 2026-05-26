"""
Security Middleware / Guard
============================
Central security orchestrator that runs all security checks in order:
1. Input validation & sanitization
2. Prompt injection detection
3. Harmful content filtering
4. Tool permission validation

This is the single entry point for all security checks.
Every user query MUST pass through this before reaching any agent.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.security.input_validator import validate_input
from app.security.prompt_injection import check_prompt_injection, ThreatLevel
from app.security.content_filter import filter_input
from app.utils.logger import get_logger

logger = get_logger("security.middleware")


@dataclass
class SecurityCheckResult:
    """Result of the complete security pipeline."""
    is_safe: bool
    sanitized_query: str
    threat_level: str
    blocked_reason: Optional[str] = None
    triggered_rules: list = None

    def __post_init__(self):
        if self.triggered_rules is None:
            self.triggered_rules = []


# --- Tool permissions ---
# Maps each tool/mode to allowed roles (extensible for auth)
TOOL_PERMISSIONS: Dict[str, list] = {
    "chat": ["user", "admin"],
    "quiz": ["user", "admin"],
    "summarize": ["user", "admin"],
    "explain": ["user", "admin"],
    "recommend": ["user", "admin"],
    "admin_analytics": ["admin"],
    "delete_documents": ["admin"],
}


def validate_tool_permission(tool: str, user_role: str = "user") -> bool:
    """
    Check if user has permission to use a specific tool/mode.

    Args:
        tool: Tool or mode name
        user_role: User's role (default: 'user')

    Returns:
        True if permitted, False otherwise
    """
    allowed_roles = TOOL_PERMISSIONS.get(tool, ["admin"])
    permitted = user_role in allowed_roles
    if not permitted:
        logger.warning(
            f"Permission denied: tool='{tool}' role='{user_role}'"
        )
    return permitted


async def run_security_checks(
    query: str,
    mode: str = "chat",
    user_role: str = "user",
) -> SecurityCheckResult:
    """
    Execute all security checks on user input.

    Pipeline:
    1. Input validation & sanitization
    2. Prompt injection detection
    3. Harmful content filtering
    4. Tool permission check

    Args:
        query: Raw user query
        mode: Interaction mode (chat/quiz/summarize/etc.)
        user_role: User's role for permission check

    Returns:
        SecurityCheckResult — if is_safe=False, block execution
    """

    # --- STEP 1: Input Validation ---
    validation_result = validate_input(query)
    if not validation_result.is_valid:
        logger.warning(f"Input validation failed: {validation_result.reason}")
        return SecurityCheckResult(
            is_safe=False,
            sanitized_query="",
            threat_level="validation_failure",
            blocked_reason=validation_result.reason,
        )

    sanitized_query = validation_result.sanitized

    # --- STEP 2: Prompt Injection Detection ---
    injection_result = check_prompt_injection(sanitized_query)

    if not injection_result.is_safe:
        logger.warning(
            f"Prompt injection blocked: level={injection_result.threat_level} | "
            f"rules={injection_result.triggered_rules}"
        )
        return SecurityCheckResult(
            is_safe=False,
            sanitized_query=sanitized_query,
            threat_level=injection_result.threat_level.value,
            blocked_reason=injection_result.safe_message,
            triggered_rules=injection_result.triggered_rules,
        )

    # Log low-level threats but allow through
    if injection_result.threat_level == ThreatLevel.LOW:
        logger.info(
            f"Low-level security flag (allowing): rules={injection_result.triggered_rules}"
        )

    # --- STEP 3: Harmful Content Filter ---
    content_result = filter_input(sanitized_query)
    if not content_result.is_safe:
        logger.warning(
            f"Harmful content blocked: violations={content_result.violations}"
        )
        return SecurityCheckResult(
            is_safe=False,
            sanitized_query=sanitized_query,
            threat_level="harmful_content",
            blocked_reason=content_result.reason,
            triggered_rules=content_result.violations,
        )

    # --- STEP 4: Tool Permission Validation ---
    if not validate_tool_permission(mode, user_role):
        return SecurityCheckResult(
            is_safe=False,
            sanitized_query=sanitized_query,
            threat_level="permission_denied",
            blocked_reason=f"You don't have permission to use the '{mode}' feature.",
        )

    # --- ALL CHECKS PASSED ---
    logger.debug(f"Security checks passed for mode='{mode}'")
    return SecurityCheckResult(
        is_safe=True,
        sanitized_query=sanitized_query,
        threat_level=injection_result.threat_level.value,
        triggered_rules=injection_result.triggered_rules,
    )
