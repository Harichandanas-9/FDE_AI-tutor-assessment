"""
Base Agent Class
================
Abstract base class for all agents in the multi-agent system.
Provides shared functionality: OpenAI client, logging, retry, token tracking.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI

from app.config import settings
from app.utils.logger import AgentLogger
from app.utils.retry import with_async_retry


class BaseAgent(ABC):
    """
    Base class for all agents.
    All agents share:
    - OpenAI async client
    - LangChain ChatOpenAI LLM
    - Structured logging via AgentLogger
    - Retry-wrapped LLM calls
    - Token usage tracking
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = AgentLogger(name)

        # Async OpenAI client for direct API calls
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # LangChain LLM for agent tools / chains
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY,
            streaming=False,
        )

        # Streaming LLM
        self.streaming_llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )

        self._total_tokens = 0

    @abstractmethod
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent logic on the current state.

        Args:
            state: Shared state dict from LangGraph

        Returns:
            Updated state dict
        """
        ...

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Make a retry-wrapped call to OpenAI Chat API.

        Args:
            messages: List of {role, content} message dicts
            temperature: Override temperature (uses settings default if None)
            max_tokens: Override max_tokens (uses settings default if None)

        Returns:
            Response content string
        """
        start = time.perf_counter()
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=temperature or settings.OPENAI_TEMPERATURE,
                max_tokens=max_tokens or settings.OPENAI_MAX_TOKENS,
            )
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            self._total_tokens += tokens_used
            latency_ms = (time.perf_counter() - start) * 1000
            self.logger.log_action(
                "llm_call",
                {"tokens": tokens_used, "latency_ms": round(latency_ms, 1)},
            )
            return content
        except Exception as e:
            self.logger.log_error(f"LLM call failed: {e}", exc_info=True)
            raise

    def get_token_usage(self) -> int:
        """Return total tokens used by this agent."""
        return self._total_tokens

    def _add_trace(self, state: Dict[str, Any], event: str, details: Dict[str, Any] = {}) -> None:
        """Add a trace entry to the shared state."""
        import time as _time
        from datetime import datetime

        trace = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": self.name,
            "event": event,
            "details": details,
        }
        if "agent_traces" not in state:
            state["agent_traces"] = []
        state["agent_traces"].append(trace)
