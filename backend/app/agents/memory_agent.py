"""
Memory Agent
=============
Manages conversation history and learning context for each user session.
Responsibilities:
- Store and retrieve conversation history
- Maintain short-term memory for ongoing sessions
- Track previously asked topics and user progress
- Build context summaries for the generation agent
- Persist learning progress across sessions

Integrated into the supervisor workflow for context-aware responses.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.utils.logger import get_logger

logger = get_logger("agents.memory")

MEMORY_SUMMARY_PROMPT = """You are a Memory Summarizer for an AI tutor.
Given a conversation history, create a concise context summary that:
1. Lists key topics the student has asked about
2. Notes their current understanding level
3. Highlights any recurring confusion points
4. Summarizes the learning progression

Keep the summary to 150 words or less.
Focus on what's most relevant for answering the NEXT question.
"""


class MemoryAgent(BaseAgent):
    """
    Memory Agent — handles conversation context storage and retrieval.
    Uses in-memory storage per session (extensible to Redis/DB).
    """

    # Class-level session store (shared across all agent instances)
    _session_store: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        super().__init__(name="MemoryAgent")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve memory context for the current session and inject into state.
        Also records the current exchange after generation is complete.

        State keys consumed: session_id, query, generated_answer (if available)
        State keys produced: memory_context, conversation_history, topic_history
        """
        session_id = state.get("session_id", "")
        query = state.get("query", "")
        answer = state.get("generated_answer", "")

        self.logger.log_start(query, session_id)
        self._add_trace(state, "memory_start", {"session_id": session_id[:8]})

        try:
            # Initialize session if it doesn't exist
            if session_id not in self._session_store:
                self._session_store[session_id] = {
                    "messages": [],
                    "topics": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "last_active": datetime.utcnow().isoformat(),
                    "query_count": 0,
                }

            session = self._session_store[session_id]
            session["last_active"] = datetime.utcnow().isoformat()

            # If answer exists (post-generation call), store the exchange
            if answer:
                self._store_exchange(session_id, query, answer, state)
                state["memory_context"] = self._build_context_summary(session_id)
                self.logger.log_complete(f"Memory updated for session={session_id[:8]}")
                self._add_trace(state, "memory_stored", {
                    "total_messages": len(session["messages"]),
                    "total_topics": len(session["topics"]),
                })
            else:
                # Pre-generation call — provide context for current query
                context = self._build_context_summary(session_id)
                state["memory_context"] = context
                state["conversation_history"] = self._get_recent_history(session_id, limit=5)
                state["topic_history"] = session.get("topics", [])

                self.logger.log_complete(
                    f"Memory retrieved: {len(session['messages'])} messages in session"
                )
                self._add_trace(state, "memory_retrieved", {
                    "context_len": len(context),
                    "history_len": len(session["messages"]),
                })

        except Exception as e:
            self.logger.log_error(f"Memory operation failed: {e}", exc_info=True)
            state.setdefault("memory_context", "")
            state.setdefault("conversation_history", [])
            state.setdefault("topic_history", [])
            self._add_trace(state, "memory_error", {"error": str(e)})

        return state

    def _store_exchange(
        self,
        session_id: str,
        query: str,
        answer: str,
        state: Dict[str, Any],
    ) -> None:
        """Store a Q&A exchange in session memory."""
        session = self._session_store[session_id]
        timestamp = datetime.utcnow().isoformat()

        # Add user message
        session["messages"].append({
            "role": "user",
            "content": query,
            "timestamp": timestamp,
        })

        # Add assistant message
        session["messages"].append({
            "role": "assistant",
            "content": answer[:500],  # Truncate to save memory
            "timestamp": timestamp,
            "confidence": state.get("confidence_score", 0.0),
            "sources": [s.get("source", "") for s in state.get("sources", [])[:3]],
        })

        session["query_count"] += 1

        # Track topics from supervisor routing
        topic = state.get("topic_category", "")
        intent = state.get("intent", "")
        if topic and topic not in session["topics"]:
            session["topics"].append(topic)

        # Keep message history bounded (last 20 messages = 10 exchanges)
        if len(session["messages"]) > 20:
            session["messages"] = session["messages"][-20:]

    def _build_context_summary(self, session_id: str) -> str:
        """Build a concise context string from recent conversation history."""
        session = self._session_store.get(session_id, {})
        messages = session.get("messages", [])
        topics = session.get("topics", [])

        if not messages:
            return ""

        # Use last 3 exchanges (6 messages) for context
        recent = messages[-6:] if len(messages) >= 6 else messages

        context_parts = []
        if topics:
            context_parts.append(f"Topics discussed: {', '.join(topics[:5])}")

        for msg in recent:
            role = msg["role"].capitalize()
            content = msg["content"][:200]
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)

    def _get_recent_history(
        self, session_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the N most recent messages for a session."""
        session = self._session_store.get(session_id, {})
        messages = session.get("messages", [])
        return messages[-limit:] if messages else []

    # --- Public API methods (called by history routes) ---

    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Get complete session history."""
        return self._session_store.get(session_id, {
            "messages": [],
            "topics": [],
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
            "query_count": 0,
        })

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get summary of all sessions."""
        sessions = []
        for sid, data in self._session_store.items():
            sessions.append({
                "session_id": sid,
                "message_count": len(data.get("messages", [])),
                "topics": data.get("topics", []),
                "created_at": data.get("created_at", ""),
                "last_active": data.get("last_active", ""),
                "query_count": data.get("query_count", 0),
            })
        return sorted(sessions, key=lambda x: x["last_active"], reverse=True)

    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session."""
        if session_id in self._session_store:
            del self._session_store[session_id]
            return True
        return False

    def get_topic_history(self, session_id: str) -> List[str]:
        """Get list of topics covered in a session."""
        session = self._session_store.get(session_id, {})
        return session.get("topics", [])

    async def summarize_session(self, session_id: str) -> str:
        """
        Generate an LLM-powered summary of the session's learning progress.
        """
        session = self._session_store.get(session_id)
        if not session or not session.get("messages"):
            return "No conversation history available for this session."

        history_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content'][:300]}"
            for m in session["messages"][-12:]
        )

        messages = [
            {"role": "system", "content": MEMORY_SUMMARY_PROMPT},
            {"role": "user", "content": f"Conversation history:\n{history_text}"},
        ]

        try:
            summary = await self.call_llm(messages, temperature=0.3, max_tokens=300)
            return summary
        except Exception as e:
            logger.error(f"Session summarization failed: {e}")
            return f"Topics covered: {', '.join(session.get('topics', ['None']))}"


# Singleton instance shared across the application
memory_agent = MemoryAgent()
