"""
Conversation Memory Store
==========================
Persistent conversation memory for multi-turn dialogue.
Wraps the MemoryAgent's session store with additional persistence capabilities.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger("memory.conversation")


class ConversationMemory:
    """
    Manages conversation history across sessions.
    Acts as a higher-level wrapper for session storage.
    """

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Get an existing session or create a new one."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
                "topics": [],
                "created_at": datetime.utcnow().isoformat(),
                "last_active": datetime.utcnow().isoformat(),
                "query_count": 0,
                "metadata": {},
            }
        return self._sessions[session_id]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a message to a session."""
        session = self.get_or_create_session(session_id)
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
        session["last_active"] = datetime.utcnow().isoformat()
        session["query_count"] += 1 if role == "user" else 0

        # Keep bounded
        if len(session["messages"]) > 50:
            session["messages"] = session["messages"][-50:]

    def get_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for a session."""
        session = self._sessions.get(session_id, {})
        messages = session.get("messages", [])
        return messages[-limit:] if messages else []

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Return summary of all sessions."""
        return [
            {
                "session_id": sid,
                "created_at": data["created_at"],
                "last_active": data["last_active"],
                "message_count": len(data["messages"]),
                "query_count": data["query_count"],
                "topics": data.get("topics", []),
            }
            for sid, data in self._sessions.items()
        ]

    def get_session_detail(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get full session details."""
        return self._sessions.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clear a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
