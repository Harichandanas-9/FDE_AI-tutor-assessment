"""Quiz Generation Routes."""
import uuid
from fastapi import APIRouter, HTTPException
from app.agents.quiz_agent import QuizAgent
from app.schemas.models import QuizRequest, QuizResponse
from app.utils.logger import get_logger

logger = get_logger("api.quiz")
router = APIRouter()
_quiz_agent = QuizAgent()


@router.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """Generate a quiz on a given topic or from conversation context."""
    topic = request.topic or "General Knowledge"
    try:
        questions = await _quiz_agent.generate_quiz(
            topic=topic,
            num_questions=request.num_questions,
            difficulty=request.difficulty,
        )
        if not questions:
            raise HTTPException(status_code=500, detail="No questions could be generated")

        return QuizResponse(
            topic=topic,
            questions=questions,
            total_questions=len(questions),
            estimated_time_minutes=len(questions) * 2,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
