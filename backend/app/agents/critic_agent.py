"""
Critic Agent (Reflection Layer)
================================
Reviews the generated answer critically to detect:
- Hallucinations / fabricated facts
- Incomplete or vague explanations
- Logical errors
- Missing source grounding
- Accuracy issues

Part of the Reflection/Self-Correction workflow.
If the Critic finds issues, it triggers the Correction Agent.
"""

import json
from typing import Any, Dict

from app.agents.base_agent import BaseAgent
from app.utils.helpers import extract_json_from_text
from app.utils.logger import get_logger

logger = get_logger("agents.critic")

CRITIC_SYSTEM_PROMPT = """You are a Critical Reviewer Agent for an AI educational system.
Your job is to carefully evaluate a generated answer for quality issues.

Evaluate the answer against these criteria:
1. FAITHFULNESS: Is the answer grounded in the provided context? Does it hallucinate facts?
2. COMPLETENESS: Does it fully answer the user's question?
3. ACCURACY: Are facts, formulas, and concepts correct?
4. CLARITY: Is the explanation clear and well-structured?
5. RELEVANCE: Is the response relevant to what was asked?

Output a JSON evaluation:
{
  "needs_correction": true|false,
  "issues_found": ["list of specific issues found"],
  "hallucination_detected": true|false,
  "hallucination_details": "describe specific hallucinations if any",
  "completeness_score": 0.0-1.0,
  "accuracy_score": 0.0-1.0,
  "clarity_score": 0.0-1.0,
  "correction_instructions": "specific instructions for how to improve the answer",
  "overall_quality": "poor|acceptable|good|excellent"
}

Be strict: prefer false positives over false negatives.
If uncertain about a fact in the answer, flag it as a potential hallucination.
"""


class CriticAgent(BaseAgent):
    """
    Critic Agent — critically reviews generated answers before finalization.
    Triggers correction if quality issues are found.
    """

    def __init__(self):
        super().__init__(name="CriticAgent")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Critically evaluate the generated answer.

        State keys consumed: query, generated_answer, retrieved_documents, reflection_iterations
        State keys produced: reflection_needed, reflection_feedback, hallucination_detected
        """
        query = state.get("query", "")
        answer = state.get("generated_answer", "")
        documents = state.get("retrieved_documents", [])
        session_id = state.get("session_id", "")
        iteration = state.get("reflection_iterations", 0)
        max_iterations = 3  # from settings

        self.logger.log_start(query, session_id)
        self._add_trace(state, "critic_start", {"iteration": iteration, "answer_len": len(answer)})

        # Don't reflect more than max_iterations times
        if iteration >= max_iterations:
            logger.info(f"Max reflection iterations ({max_iterations}) reached — accepting answer")
            state["reflection_needed"] = False
            self._add_trace(state, "critic_max_iterations", {"iteration": iteration})
            return state

        if not answer:
            state["reflection_needed"] = False
            return state

        try:
            # Build context summary for critic
            context_summary = self._summarize_context(documents)

            messages = [
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"User Question: {query}\n\n"
                        f"Available Source Context:\n{context_summary}\n\n"
                        f"Generated Answer to Evaluate:\n{answer}\n\n"
                        f"This is reflection iteration {iteration + 1}. "
                        "Be thorough but avoid being overly critical of minor style issues."
                    ),
                },
            ]

            response = await self.call_llm(messages, temperature=0.1, max_tokens=1024)
            evaluation = extract_json_from_text(response)

            if not evaluation:
                # If JSON parsing fails, default to no correction needed
                state["reflection_needed"] = False
                state["reflection_feedback"] = ""
                state["hallucination_detected"] = False
                self._add_trace(state, "critic_parse_failure", {})
                return state

            needs_correction = evaluation.get("needs_correction", False)
            hallucination = evaluation.get("hallucination_detected", False)
            quality = evaluation.get("overall_quality", "acceptable")
            issues = evaluation.get("issues_found", [])
            correction_instructions = evaluation.get("correction_instructions", "")

            state["reflection_needed"] = needs_correction
            state["reflection_feedback"] = correction_instructions
            state["hallucination_detected"] = hallucination
            state["critic_scores"] = {
                "completeness": evaluation.get("completeness_score", 0.8),
                "accuracy": evaluation.get("accuracy_score", 0.8),
                "clarity": evaluation.get("clarity_score", 0.8),
                "overall_quality": quality,
            }

            self.logger.log_complete(
                f"Critic evaluation: needs_correction={needs_correction} | "
                f"hallucination={hallucination} | quality={quality} | "
                f"issues={len(issues)}"
            )
            self._add_trace(state, "critic_complete", {
                "needs_correction": needs_correction,
                "hallucination": hallucination,
                "quality": quality,
                "issues": issues[:3],  # Log first 3 issues
            })

        except Exception as e:
            self.logger.log_error(f"Critic evaluation failed: {e}", exc_info=True)
            state["reflection_needed"] = False
            state["hallucination_detected"] = False
            self._add_trace(state, "critic_error", {"error": str(e)})

        return state

    def _summarize_context(self, documents: list) -> str:
        """Create a concise summary of retrieved documents for the critic."""
        if not documents:
            return "No source documents retrieved."

        summaries = []
        for i, doc in enumerate(documents[:3], 1):
            content = doc.get("content", "")[:300]
            source = doc.get("metadata", {}).get("source", "Unknown")
            summaries.append(f"[Source {i}: {source}] {content}...")

        return "\n\n".join(summaries)
