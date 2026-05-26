"""
Logging System
==============
Structured logging with Rich console output and file rotation.
Supports agent tracing, request logging, evaluation logging, error tracking.
"""

import logging
import logging.handlers
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
from functools import wraps

import structlog
from rich.console import Console
from rich.logging import RichHandler

# --- Ensure log directory exists ---
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- Rich Console ---
console = Console(stderr=True)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure the global logging system.
    Sets up:
    - Rich console handler for development
    - Rotating file handler for production
    - Structlog for structured JSON logging
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    handlers = [
        RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
    ]

    # Add rotating file handler
    log_path = LOG_DIR / (log_file or "app.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handlers.append(file_handler)

    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        format="%(message)s",
    )

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(name)


class AgentLogger:
    """
    Specialized logger for agent activities.
    Tracks agent state transitions, tool calls, and inter-agent communication.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_logger(f"agent.{agent_name}")
        self._traces: list[Dict[str, Any]] = []

    def log_start(self, query: str, session_id: str = "") -> None:
        """Log agent activation."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "event": "start",
            "session_id": session_id,
            "query_preview": query[:100],
        }
        self._traces.append(entry)
        self.logger.info(
            f"[{self.agent_name}] Started | session={session_id} | query='{query[:80]}...'"
        )

    def log_action(self, action: str, details: Dict[str, Any] = {}) -> None:
        """Log a specific agent action."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "event": "action",
            "action": action,
            "details": details,
        }
        self._traces.append(entry)
        self.logger.info(f"[{self.agent_name}] {action} | {json.dumps(details)[:200]}")

    def log_complete(self, result_summary: str, latency_ms: float = 0) -> None:
        """Log agent completion."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "event": "complete",
            "result_summary": result_summary[:200],
            "latency_ms": latency_ms,
        }
        self._traces.append(entry)
        self.logger.info(
            f"[{self.agent_name}] Completed | latency={latency_ms:.0f}ms | {result_summary[:80]}"
        )

    def log_error(self, error: str, exc_info: bool = False) -> None:
        """Log agent error."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "event": "error",
            "error": error,
        }
        self._traces.append(entry)
        self.logger.error(
            f"[{self.agent_name}] ERROR | {error}", exc_info=exc_info
        )

    def get_traces(self) -> list[Dict[str, Any]]:
        """Return all recorded traces for this agent."""
        return self._traces.copy()


class EvaluationLogger:
    """
    Specialized logger for evaluation metrics.
    Persists evaluation results to a dedicated log file.
    """

    def __init__(self):
        self.logger = get_logger("evaluation")
        self.eval_log_path = LOG_DIR / "evaluations.jsonl"

    def log_evaluation(
        self,
        session_id: str,
        query: str,
        response: str,
        metrics: Dict[str, float],
        passed: bool,
    ) -> None:
        """Persist evaluation results to JSONL log file."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "query_preview": query[:100],
            "response_preview": response[:200],
            "metrics": metrics,
            "passed": passed,
            "confidence_score": metrics.get("overall_score", 0.0),
        }

        # Append to JSONL file
        with open(self.eval_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        status = "✅ PASSED" if passed else "❌ FAILED"
        self.logger.info(
            f"Evaluation {status} | session={session_id} | "
            f"faithfulness={metrics.get('faithfulness', 0):.2f} | "
            f"relevance={metrics.get('relevance', 0):.2f} | "
            f"confidence={metrics.get('overall_score', 0):.2f}"
        )


class RequestLogger:
    """Logs API request/response details with latency tracking."""

    def __init__(self):
        self.logger = get_logger("api.request")

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        client_ip: str = "",
    ) -> None:
        level = logging.WARNING if status_code >= 400 else logging.INFO
        self.logger.log(
            level,
            f"{method} {path} | status={status_code} | latency={latency_ms:.0f}ms | ip={client_ip}",
        )


def timing(logger_instance: Optional[logging.Logger] = None):
    """Decorator: measures and logs function execution time."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                log = logger_instance or get_logger(func.__module__)
                log.debug(f"{func.__name__} completed in {elapsed_ms:.1f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                log = logger_instance or get_logger(func.__module__)
                log.error(f"{func.__name__} failed after {elapsed_ms:.1f}ms: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                log = logger_instance or get_logger(func.__module__)
                log.debug(f"{func.__name__} completed in {elapsed_ms:.1f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                log = logger_instance or get_logger(func.__module__)
                log.error(f"{func.__name__} failed after {elapsed_ms:.1f}ms: {e}")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Initialize logging on module import
setup_logging()

# Module-level logger
logger = get_logger("app")
agent_logger_factory = AgentLogger
evaluation_logger = EvaluationLogger()
request_logger = RequestLogger()
