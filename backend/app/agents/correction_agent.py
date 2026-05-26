"""
Correction Agent (Self-Correction Layer)
==========================================
Improves the generated answer based on Critic Agent feedback.
Addresses:
- Hallucination corrections
- Missing information
- Clarity improvements
- Accuracy fixes
- Better source grounding

Part of the Reflection/Self-Correction workflow.
"""

from typing import Any, Dict

from app.agents.base_agent import BaseAgent
from app.utils.logger import get_logger

logger = get_logger("agents.correction")

CORRECTION_SYSTEM_PROMPT = """You are a Correction Agent for an AI educational system.
You receive a generated answer and specific feedback about its issues.
Your task is to produce an improved version that addresses ALL the identified issues.

Rules:
1. Fix ALL issues mentioned in the correction feedback
2. Remove any hallucinated or unverified claims
3. Strengthen grounding in the provided source context
4. Maintain the same educational tone and structure
5. Do NOT change correct parts of the answer
6. Keep the answer focused and educational
7. Cite sources when making specific factual claims
8. If a fact cannot be verified from context, say "Based on general knowledge:"

Produce ONLY the corrected answer — no preamble or meta-commentary.
"""


class CorrectionAgent(BaseAgent):
    """
    Correction Agent — produces an improved answer based on critic feedback.
    """

    def __init__(self):
        super().__init__(name="CorrectionAgent")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Correct the generated answer based on critic feedback.

        State keys consumed: query, generated_answer, retrieved_documents,
                             reflection_feedback, hallucination_detected
        State keys produced: generated_answer (updated), reflection_iterations (incremented)
        """
        query = state.get("query", "")
        original_answer = state.get("generated_answer", "")
        feedback = state.get("reflection_feedback", "")
        documents = state.get("retrieved_documents", [])
        session_id = state.get("session_id", "")
        iteration = state.get("reflection_iterations", 0)
        hallucination = state.get("hallucination_detected", False)

        self.logger.log_start(query, session_id)
        self._add_trace(state, "correction_start", {
            "iteration": iteration,
            "hallucination": hallucination,
            "feedback_len": len(feedback),
        })

        if not feedback and not hallucination:
            logger.debug("No correction needed — skipping")
            state["reflection_iterations"] = iteration + 1
            return state

        try:
            # Build source context for grounding
            context = self._build_context(documents)

            user_message = (
                f"Original Question: {query}\n\n"
                f"Source Context for Grounding:\n{context}\n\n"
                f"Original Answer (with issues):\n{original_answer}\n\n"
                f"Issues to Fix:\n{feedback}\n"
                f"Hallucination Detected: {hallucination}\n\n"
                "Please produce a corrected, improved answer that addresses all issues above."
            )

            messages = [
                {"role": "system", "content": CORRECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]

            corrected_answer = await self.call_llm(messages, temperature=0.3, max_tokens=2048)

            # Update state with corrected answer
            state["generated_answer"] = corrected_answer
            state["reflection_iterations"] = iteration + 1

            self.logger.log_complete(
                f"Correction applied (iteration {iteration + 1}) | "
                f"answer_len={len(corrected_answer)}"
            )
            self._add_trace(state, "correction_complete", {
                "iteration": iteration + 1,
                "answer_len": len(corrected_answer),
                "hallucination_fixed": hallucination,
            })

        except Exception as e:
            self.logger.log_error(f"Correction failed: {e}", exc_info=True)
            # Keep original answer on failure
            state["reflection_iterations"] = iteration + 1
            self._add_trace(state, "correction_error", {"error": str(e)})

        return state

    def _build_context(self, documents: list) -> str:
        """Format documents into context for correction grounding."""
        if not documents:
            return "No source documents available — use general knowledge carefully."

        parts = []
        for i, doc in enumerate(documents[:4], 1):
            content = doc.get("content", "")[:400]
            source = doc.get("metadata", {}).get("source", "Document")
            parts.append(f"[{i}. {source}]: {content}")

        return "\n\n".join(parts)
