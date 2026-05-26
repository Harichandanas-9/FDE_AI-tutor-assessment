"""Learning Recommendations Routes."""
from fastapi import APIRouter, HTTPException
from app.agents.recommendation_agent import recommendation_agent
from app.agents.memory_agent import memory_agent
from app.schemas.models import RecommendationRequest, RecommendationResponse
from app.utils.logger import get_logger

logger = get_logger("api.recommendations")
router = APIRouter()


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Get personalized learning topic recommendations."""
    topic_history = []
    if request.session_id:
        topic_history = memory_agent.get_topic_history(request.session_id)

    try:
        recommendations = await recommendation_agent.get_recommendations(
            current_topic=request.current_topic or "General Learning",
            skill_level=request.skill_level,
            topic_history=topic_history,
            num_recommendations=request.num_recommendations,
        )
        return RecommendationResponse(
            recommendations=recommendations,
            based_on=request.current_topic or "your learning history",
        )
    except Exception as e:
        logger.error(f"Recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
