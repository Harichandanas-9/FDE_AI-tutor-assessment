"""
Recommendation Agent
=====================
Suggests personalized next learning topics and study paths based on:
- Current query/topic
- Conversation history
- User's skill level
- Knowledge gaps detected in the session
- Related concepts in the knowledge base

Generates structured recommendations with difficulty levels and time estimates.
"""

import json
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.schemas.models import LearningTopic
from app.utils.helpers import extract_json_from_text
from app.utils.logger import get_logger

logger = get_logger("agents.recommendation")

RECOMMENDATION_SYSTEM_PROMPT = """You are an expert Learning Path Advisor for an AI educational system.
Based on what the student has been learning, suggest the next most valuable topics to explore.

Generate a JSON array of learning topic recommendations:
[
  {
    "topic": "Topic Name",
    "description": "Why this topic is important and what it covers",
    "difficulty": "beginner|intermediate|advanced",
    "estimated_time": "30 minutes|2 hours|1 week",
    "relevance_score": 0.0-1.0,
    "tags": ["tag1", "tag2"],
    "prerequisites": ["prereq1"],
    "learning_objectives": ["objective1", "objective2"]
  }
]

Recommendation strategy:
1. Suggest topics that logically follow from what was just learned
2. Include one "review/reinforcement" topic (slightly easier)
3. Include one "stretch goal" topic (slightly harder)
4. Recommend topics that connect different concepts
5. Prefer practical, applicable topics over purely theoretical ones
6. Tailor difficulty to the student's demonstrated understanding level
"""


class RecommendationAgent(BaseAgent):
    """
    Recommendation Agent — generates personalized learning path suggestions.
    """

    def __init__(self):
        super().__init__(name="RecommendationAgent")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate learning recommendations based on current query and history.

        State keys consumed: query, topic_category, topic_history,
                             estimated_difficulty, generated_answer
        State keys produced: recommendations, generated_answer (if mode=recommend)
        """
        query = state.get("query", "")
        session_id = state.get("session_id", "")
        topic_category = state.get("topic_category", "general")
        topic_history = state.get("topic_history", [])
        difficulty = state.get("estimated_difficulty", "intermediate")
        num_recs = state.get("num_recommendations", 5)
        current_topic = state.get("quiz_topic") or topic_category

        self.logger.log_start(query, session_id)
        self._add_trace(state, "recommendation_start", {
            "topic": current_topic,
            "history_len": len(topic_history),
            "difficulty": difficulty,
        })

        try:
            recommendations = await self._generate_recommendations(
                query=query,
                current_topic=current_topic,
                topic_history=topic_history,
                difficulty=difficulty,
                num_recommendations=num_recs,
            )

            validated = self._validate_recommendations(recommendations)

            state["recommendations"] = [r.dict() for r in validated]

            # If this is a recommendation-mode call, format as answer
            if state.get("intent") == "recommend" or state.get("mode") == "recommend":
                state["generated_answer"] = self._format_recommendations_as_text(
                    validated, current_topic
                )

            self.logger.log_complete(
                f"Generated {len(validated)} recommendations for topic='{current_topic}'"
            )
            self._add_trace(state, "recommendation_complete", {
                "num_recommendations": len(validated),
                "topics": [r.topic for r in validated[:3]],
            })

        except Exception as e:
            self.logger.log_error(f"Recommendation failed: {e}", exc_info=True)
            # Provide fallback recommendations
            fallback = self._get_fallback_recommendations(current_topic, difficulty)
            state["recommendations"] = [r.dict() for r in fallback]
            if state.get("intent") == "recommend":
                state["generated_answer"] = self._format_recommendations_as_text(
                    fallback, current_topic
                )
            self._add_trace(state, "recommendation_fallback", {"error": str(e)})

        return state

    async def get_recommendations(
        self,
        current_topic: str,
        skill_level: str = "intermediate",
        topic_history: Optional[List[str]] = None,
        num_recommendations: int = 5,
    ) -> List[LearningTopic]:
        """
        Public method to get recommendations (called directly by API routes).

        Args:
            current_topic: The topic currently being studied
            skill_level: beginner|intermediate|advanced
            topic_history: Previously covered topics
            num_recommendations: Number of suggestions to return

        Returns:
            List of LearningTopic recommendations
        """
        topic_history = topic_history or []
        raw = await self._generate_recommendations(
            query=current_topic,
            current_topic=current_topic,
            topic_history=topic_history,
            difficulty=skill_level,
            num_recommendations=num_recommendations,
        )
        return self._validate_recommendations(raw)

    async def _generate_recommendations(
        self,
        query: str,
        current_topic: str,
        topic_history: List[str],
        difficulty: str,
        num_recommendations: int,
    ) -> List[Dict[str, Any]]:
        """Generate raw recommendation data via LLM."""
        history_text = (
            f"Previously studied topics: {', '.join(topic_history[:10])}"
            if topic_history
            else "No previous topics recorded."
        )

        messages = [
            {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current query: {query}\n"
                    f"Current topic area: {current_topic}\n"
                    f"Student skill level: {difficulty}\n"
                    f"{history_text}\n\n"
                    f"Generate {num_recommendations} learning topic recommendations.\n"
                    "Return ONLY a valid JSON array."
                ),
            },
        ]

        response = await self.call_llm(messages, temperature=0.5, max_tokens=2000)

        recommendations = extract_json_from_text(response)
        if isinstance(recommendations, dict):
            recommendations = recommendations.get("recommendations", [])

        return recommendations if isinstance(recommendations, list) else []

    def _validate_recommendations(
        self, raw_recs: List[Dict[str, Any]]
    ) -> List[LearningTopic]:
        """Validate and convert raw recommendation dicts to LearningTopic objects."""
        validated = []
        for rec in raw_recs:
            try:
                topic = LearningTopic(
                    topic=rec.get("topic", "Unknown Topic"),
                    description=rec.get("description", "No description available."),
                    difficulty=rec.get("difficulty", "intermediate"),
                    estimated_time=rec.get("estimated_time", "1-2 hours"),
                    relevance_score=float(rec.get("relevance_score", 0.7)),
                    tags=rec.get("tags", [])[:5],
                )
                validated.append(topic)
            except Exception as e:
                logger.warning(f"Skipping invalid recommendation: {e}")
                continue
        return validated

    def _get_fallback_recommendations(
        self, topic: str, difficulty: str
    ) -> List[LearningTopic]:
        """Return safe fallback recommendations if LLM fails."""
        return [
            LearningTopic(
                topic=f"Deep Dive: {topic}",
                description=f"Explore advanced concepts in {topic} with practical examples.",
                difficulty="advanced" if difficulty != "beginner" else "intermediate",
                estimated_time="2-3 hours",
                relevance_score=0.9,
                tags=[topic.lower()],
            ),
            LearningTopic(
                topic=f"Practice Problems: {topic}",
                description=f"Reinforce your understanding of {topic} with exercises.",
                difficulty=difficulty,
                estimated_time="1 hour",
                relevance_score=0.85,
                tags=["practice", topic.lower()],
            ),
            LearningTopic(
                topic="Related Concepts",
                description="Explore topics that connect with what you've been learning.",
                difficulty=difficulty,
                estimated_time="1-2 hours",
                relevance_score=0.75,
                tags=["related"],
            ),
        ]

    def _format_recommendations_as_text(
        self, recommendations: List[LearningTopic], topic: str
    ) -> str:
        """Format recommendations as readable markdown for the generated_answer field."""
        if not recommendations:
            return "No recommendations could be generated at this time."

        lines = [
            f"## 📚 Learning Recommendations for: {topic}\n",
            "Here are your personalized next learning topics:\n",
        ]

        for i, rec in enumerate(recommendations, 1):
            difficulty_emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(
                rec.difficulty, "🔵"
            )
            lines.append(
                f"\n### {i}. {rec.topic} {difficulty_emoji}\n"
                f"**Description:** {rec.description}\n"
                f"**Difficulty:** {rec.difficulty.capitalize()} | "
                f"**Estimated Time:** {rec.estimated_time} | "
                f"**Relevance:** {rec.relevance_score:.0%}\n"
            )
            if rec.tags:
                lines.append(f"**Tags:** {', '.join(rec.tags)}\n")

        return "\n".join(lines)


# Singleton instance
recommendation_agent = RecommendationAgent()
