"""Conversation History Routes."""
from fastapi import APIRouter, HTTPException
from app.agents.memory_agent import memory_agent
from app.schemas.models import ConversationHistoryResponse, ConversationSession, ConversationMessage, BaseResponse
from app.utils.logger import get_logger

logger = get_logger("api.history")
router = APIRouter()


@router.get("/history", response_model=ConversationHistoryResponse)
async def get_all_history():
    """Get all conversation sessions."""
    sessions_data = memory_agent.get_all_sessions()
    sessions = []
    for s in sessions_data:
        history = memory_agent.get_session_history(s["session_id"])
        messages = [
            ConversationMessage(
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"],
            )
            for m in history.get("messages", [])[-20:]
        ]
        sessions.append(ConversationSession(
            session_id=s["session_id"],
            messages=messages,
            created_at=s.get("created_at", ""),
            last_active=s.get("last_active", ""),
            total_messages=len(messages),
        ))
    return ConversationHistoryResponse(sessions=sessions, total_sessions=len(sessions))


@router.get("/history/{session_id}")
async def get_session_history(session_id: str):
    """Get history for a specific session."""
    history = memory_agent.get_session_history(session_id)
    if not history.get("messages"):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": history}


@router.delete("/history/{session_id}", response_model=BaseResponse)
async def clear_session(session_id: str):
    """Clear a conversation session."""
    success = memory_agent.clear_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return BaseResponse(message="Session cleared")


@router.get("/history/{session_id}/summary")
async def get_session_summary(session_id: str):
    """Get an AI-generated summary of a session's learning progress."""
    summary = await memory_agent.summarize_session(session_id)
    return {"session_id": session_id, "summary": summary}
