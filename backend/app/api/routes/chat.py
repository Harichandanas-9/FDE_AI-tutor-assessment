"""
Chat API Routes
================
Handles all chat/query interactions with the multi-agent system.
Supports: standard responses and streaming responses.
"""

import uuid
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.schemas.models import (
    ChatRequest, ChatResponse, SourceReference,
    EvaluationMetrics, AgentTrace,
)
from app.workflows.main_workflow import run_workflow
from app.agents.generation_agent import GenerationAgent
from app.retrieval.hybrid_retriever import HybridRetriever
from app.utils.helpers import generate_session_id
from app.utils.logger import get_logger

logger = get_logger("api.chat")
router = APIRouter()

_generation_agent = GenerationAgent()
_retriever = HybridRetriever()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """
    Main chat endpoint — processes user query through the full multi-agent workflow.

    Workflow:
    Security → Memory → Supervisor → Retrieval → Generation → Reflection → Review
    """
    session_id = request.session_id or generate_session_id()

    logger.info(
        f"Chat request: session={session_id[:8]} | mode={request.mode} | "
        f"query='{request.query[:60]}'"
    )

    # Run the full workflow
    state = await run_workflow(
        query=request.query,
        session_id=session_id,
        mode=request.mode,
        include_evaluation=request.include_evaluation,
    )

    # Check if blocked by security
    if not state.get("is_safe", True):
        return ChatResponse(
            session_id=session_id,
            query=request.query,
            answer=state.get("security_message", "Request blocked for security reasons."),
            confidence_score=0.0,
            sources=[],
            evaluation=None,
            agent_traces=[],
            follow_up_topics=[],
            mode=request.mode,
        )

    # Build evaluation metrics object
    eval_metrics = None
    if request.include_evaluation and state.get("evaluation_metrics"):
        m = state["evaluation_metrics"]
        eval_metrics = EvaluationMetrics(
            faithfulness=m.get("faithfulness", 0.0),
            relevance=m.get("relevance", 0.0),
            precision=m.get("precision", 0.0),
            hallucination_score=m.get("hallucination_score", 0.0),
            overall_score=m.get("overall_score", 0.0),
            passed=state.get("evaluation_passed", False),
            evaluation_time_ms=m.get("evaluation_time_ms"),
        )

    # Build sources
    sources = [
        SourceReference(**s) if isinstance(s, dict) else s
        for s in state.get("sources", [])
    ]

    # Build agent traces
    traces = [
        AgentTrace(**t) if isinstance(t, dict) else t
        for t in state.get("agent_traces", [])
    ]

    # Track analytics
    try:
        analytics = req.app.state.analytics
        if analytics:
            analytics.record_query(
                session_id=session_id,
                query=request.query,
                mode=request.mode,
                response_length=len(state.get("final_answer", "")),
                confidence_score=state.get("confidence_score", 0.0),
                evaluation_metrics=state.get("evaluation_metrics", {}),
                latency_ms=state.get("total_latency_ms", 0.0),
                reflection_iterations=state.get("reflection_iterations", 0),
                num_sources=len(sources),
                error=state.get("error"),
            )
    except Exception as e:
        logger.warning(f"Analytics recording failed: {e}")

    return ChatResponse(
        session_id=session_id,
        query=request.query,
        answer=state.get("final_answer") or state.get("generated_answer", ""),
        confidence_score=state.get("confidence_score", 0.0),
        sources=sources,
        evaluation=eval_metrics,
        agent_traces=traces,
        follow_up_topics=state.get("follow_up_topics", []),
        mode=request.mode,
        reflection_iterations=state.get("reflection_iterations", 0),
        total_latency_ms=state.get("total_latency_ms"),
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """
    Streaming chat endpoint — sends tokens as they are generated.
    Frontend connects via SSE (Server-Sent Events).
    """
    session_id = request.session_id or generate_session_id()

    # First run retrieval to get context
    from app.security.security_middleware import run_security_checks
    security = await run_security_checks(query=request.query, mode=request.mode)

    if not security.is_safe:
        async def blocked_stream():
            yield f"data: {security.blocked_reason}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(blocked_stream(), media_type="text/event-stream")

    # Get context via retrieval
    docs, _ = await _retriever.retrieve(query=security.sanitized_query, top_k=5)

    state = {
        "query": security.sanitized_query,
        "retrieved_documents": docs,
        "intent": request.mode,
        "mode": request.mode,
        "estimated_difficulty": "intermediate",
    }

    async def generate_stream():
        try:
            async for chunk in _generation_agent.generate_streaming(state):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
