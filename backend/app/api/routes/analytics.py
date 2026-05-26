"""Analytics Dashboard Routes."""
from fastapi import APIRouter, Request
from app.schemas.models import AnalyticsDashboardResponse, EvaluationTrend, AgentPerformance
from app.utils.logger import get_logger

logger = get_logger("api.analytics")
router = APIRouter()


@router.get("/analytics", response_model=AnalyticsDashboardResponse)
async def get_analytics(req: Request, days: int = 7):
    """Get full analytics dashboard data."""
    analytics = req.app.state.analytics

    # Document count
    try:
        from app.retrieval.vector_store import vector_store
        total_docs = vector_store.get_document_count()
    except Exception:
        total_docs = 0

    # Session count
    try:
        from app.agents.memory_agent import memory_agent
        sessions = memory_agent.get_all_sessions()
        total_sessions = len(sessions)
    except Exception:
        total_sessions = 0

    if not analytics:
        return AnalyticsDashboardResponse(
            total_documents=total_docs,
            total_sessions=total_sessions,
        )

    data = analytics.get_dashboard_data(days=days)

    evaluation_trends = [EvaluationTrend(**t) for t in data.get("evaluation_trends", [])]
    agent_performance = [AgentPerformance(**a) for a in data.get("agent_performance", [])]

    return AnalyticsDashboardResponse(
        total_queries=data.get("total_queries", 0),
        avg_confidence_score=data.get("avg_confidence_score", 0.0),
        avg_latency_ms=data.get("avg_latency_ms", 0.0),
        total_documents=total_docs,
        total_sessions=total_sessions,
        evaluation_pass_rate=data.get("evaluation_pass_rate", 0.0),
        evaluation_trends=evaluation_trends,
        agent_performance=agent_performance,
        top_topics=data.get("top_topics", []),
        daily_query_counts=data.get("daily_query_counts", []),
    )
