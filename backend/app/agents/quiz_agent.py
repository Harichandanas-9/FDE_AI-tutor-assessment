"""
Quiz Agent
===========
Generates MCQ quiz questions from retrieved learning content.
Supports:
- Multiple difficulty levels (easy, medium, hard, mixed)
- Configurable number of questions
- Answer explanations
- Topic-specific question generation
- Both context-based (from docs) and topic-based quiz generation

Integrated into the supervisor workflow when mode='quiz'.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.schemas.models import QuizQuestion
from app.utils.helpers import extract_json_from_text
from app.utils.logger import get_logger

logger = get_logger("agents.quiz")

QUIZ_SYSTEM_PROMPT = """You are an expert educational quiz creator.
Generate high-quality multiple-choice questions (MCQs) based on the provided content.

For each question, create:
1. A clear, specific question
2. Exactly 4 answer options (labeled A, B, C, D)
3. The correct answer (just the letter: A, B, C, or D)
4. A detailed explanation of why the correct answer is right
5. Difficulty level: easy, medium, or hard
6. Topic tag

Output a JSON array of questions:
[
  {
    "question": "What is...?",
    "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
    "correct_answer": "B",
    "explanation": "B is correct because...",
    "difficulty": "medium",
    "topic": "topic name"
  }
]

Rules:
- Questions must test genuine understanding, not just memorization
- Distractors (wrong options) should be plausible but clearly incorrect
- Avoid trivially obvious questions
- Vary question types: definition, application, comparison, analysis
- Ensure all 4 options are roughly similar in length
- One and only one option must be correct
"""

TOPIC_QUIZ_PROMPT = """You are an expert quiz creator for educational topics.
Generate {num_questions} multiple-choice questions about: {topic}

Difficulty distribution: {difficulty_instruction}

Output valid JSON array following this schema:
[
  {{
    "question": "Question text?",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "A",
    "explanation": "Detailed explanation...",
    "difficulty": "easy|medium|hard",
    "topic": "{topic}"
  }}
]
"""


class QuizAgent(BaseAgent):
    """
    Quiz Agent — generates educational MCQ quizzes from content or topics.
    """

    def __init__(self):
        super().__init__(name="QuizAgent")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate quiz questions from retrieved content or specified topic.

        State keys consumed: query, retrieved_documents, num_questions, difficulty, topic
        State keys produced: quiz_questions, quiz_topic, generated_answer
        """
        query = state.get("query", "")
        session_id = state.get("session_id", "")
        documents = state.get("retrieved_documents", [])
        num_questions = state.get("num_questions", 5)
        difficulty = state.get("difficulty", "mixed")
        topic = state.get("quiz_topic") or self._extract_topic(query)

        self.logger.log_start(query, session_id)
        self._add_trace(state, "quiz_start", {
            "topic": topic,
            "num_questions": num_questions,
            "difficulty": difficulty,
            "has_context": len(documents) > 0,
        })

        try:
            questions = await self._generate_questions(
                query=query,
                documents=documents,
                num_questions=num_questions,
                difficulty=difficulty,
                topic=topic,
            )

            # Format as QuizQuestion objects
            validated_questions = self._validate_and_format(questions, topic)

            # Store in state
            state["quiz_questions"] = [q.dict() for q in validated_questions]
            state["quiz_topic"] = topic

            # Also set generated_answer for consistent pipeline flow
            state["generated_answer"] = self._format_quiz_as_text(validated_questions, topic)

            self.logger.log_complete(
                f"Generated {len(validated_questions)} quiz questions for topic='{topic}'"
            )
            self._add_trace(state, "quiz_complete", {
                "num_generated": len(validated_questions),
                "topic": topic,
                "difficulties": [q.difficulty for q in validated_questions],
            })

        except Exception as e:
            self.logger.log_error(f"Quiz generation failed: {e}", exc_info=True)
            state["quiz_questions"] = []
            state["quiz_topic"] = topic
            state["generated_answer"] = f"Sorry, I couldn't generate quiz questions about '{topic}'. Please try again."
            self._add_trace(state, "quiz_error", {"error": str(e)})

        return state

    async def generate_quiz(
        self,
        topic: str,
        num_questions: int = 5,
        difficulty: str = "mixed",
        context_documents: Optional[List[Dict[str, Any]]] = None,
    ) -> List[QuizQuestion]:
        """
        Public method to generate a quiz (used directly by API route).

        Args:
            topic: Topic to generate questions about
            num_questions: Number of questions
            difficulty: easy|medium|hard|mixed
            context_documents: Optional retrieved documents for context-based quiz

        Returns:
            List of QuizQuestion objects
        """
        documents = context_documents or []
        raw = await self._generate_questions(
            query=topic,
            documents=documents,
            num_questions=num_questions,
            difficulty=difficulty,
            topic=topic,
        )
        return self._validate_and_format(raw, topic)

    async def _generate_questions(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        num_questions: int,
        difficulty: str,
        topic: str,
    ) -> List[Dict[str, Any]]:
        """Generate raw question data via LLM."""
        difficulty_instruction = self._build_difficulty_instruction(difficulty, num_questions)

        if documents:
            # Context-based quiz from retrieved documents
            context = self._build_context(documents)
            messages = [
                {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Create {num_questions} MCQ questions based on this educational content:\n\n"
                        f"{context}\n\n"
                        f"Topic focus: {topic}\n"
                        f"Difficulty: {difficulty_instruction}\n\n"
                        "Return ONLY a valid JSON array of questions."
                    ),
                },
            ]
        else:
            # Topic-based quiz from general knowledge
            prompt = TOPIC_QUIZ_PROMPT.format(
                num_questions=num_questions,
                topic=topic,
                difficulty_instruction=difficulty_instruction,
            )
            messages = [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        f"Generate {num_questions} MCQ questions about: {topic}\n"
                        f"Additional context from query: {query}\n\n"
                        "Return ONLY a valid JSON array of questions."
                    ),
                },
            ]

        response = await self.call_llm(messages, temperature=0.6, max_tokens=3000)

        questions = extract_json_from_text(response)
        if isinstance(questions, dict):
            # Sometimes LLM wraps in an outer object
            questions = questions.get("questions", [])

        return questions if isinstance(questions, list) else []

    def _validate_and_format(
        self, raw_questions: List[Dict[str, Any]], default_topic: str
    ) -> List[QuizQuestion]:
        """Validate and convert raw question dicts to QuizQuestion objects."""
        validated = []
        for q in raw_questions:
            try:
                # Ensure required fields exist
                if not all(k in q for k in ("question", "options", "correct_answer", "explanation")):
                    continue

                # Ensure 4 options
                options = q.get("options", [])
                if len(options) < 2:
                    continue

                # Normalize correct answer
                correct = q.get("correct_answer", "A").strip().upper()
                if correct not in ["A", "B", "C", "D"]:
                    correct = "A"

                quiz_q = QuizQuestion(
                    question=q["question"].strip(),
                    options=options[:4],
                    correct_answer=correct,
                    explanation=q.get("explanation", "No explanation provided."),
                    difficulty=q.get("difficulty", "medium"),
                    topic=q.get("topic", default_topic),
                )
                validated.append(quiz_q)
            except Exception as e:
                logger.warning(f"Skipping invalid question: {e}")
                continue

        return validated

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format documents for quiz context."""
        parts = []
        for i, doc in enumerate(documents[:5], 1):
            content = doc.get("content", "")[:600]
            source = doc.get("metadata", {}).get("source", "Document")
            parts.append(f"[Section {i} from {source}]:\n{content}")
        return "\n\n".join(parts)

    def _extract_topic(self, query: str) -> str:
        """Extract topic from query string."""
        # Remove common quiz request phrases
        import re
        query_clean = re.sub(
            r"(generate|create|make|give me|quiz|questions?|MCQ|test|on|about|for)\s*",
            " ", query, flags=re.IGNORECASE
        ).strip()
        return query_clean[:50] if query_clean else "General Knowledge"

    def _build_difficulty_instruction(self, difficulty: str, num_questions: int) -> str:
        """Build difficulty distribution instruction."""
        if difficulty == "mixed":
            easy = num_questions // 3
            hard = num_questions // 3
            medium = num_questions - easy - hard
            return f"{easy} easy, {medium} medium, {hard} hard questions"
        return f"all {difficulty} difficulty"

    def _format_quiz_as_text(self, questions: List[QuizQuestion], topic: str) -> str:
        """Format quiz as readable text for the generated_answer field."""
        if not questions:
            return f"No quiz questions could be generated for topic: {topic}"

        lines = [f"## Quiz: {topic}\n", f"**{len(questions)} Questions**\n"]
        for i, q in enumerate(questions, 1):
            lines.append(f"\n**Q{i}.** {q.question}")
            for opt in q.options:
                lines.append(f"  {opt}")
            lines.append(f"  *(Difficulty: {q.difficulty})*")

        return "\n".join(lines)
