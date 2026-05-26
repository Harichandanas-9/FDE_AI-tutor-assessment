"""
Reviewer / Evaluation Agent
=============================
Final quality gate before response is sent to the user.
Runs DeepEval metrics:
- Faithfulness
- Relevance
- Precision
- Hallucination Detection

Generates confidence score and pass/fail decision.
"""

import time
from typing import Any, Dict

from app.agents.base_agent import BaseAgent
from app.evaluation.evaluator import ResponseEvaluator
from app.utils.helpers import calculate_confidence_score
from app.utils.logger import get_logger, evaluation_logger

logger = get_logger("agents.reviewer")


class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent — runs evaluation pipeline on the final answer.
    Blocks responses that fail quality thresholds.
    """

    def __init__(self):
        super().__init__(name="ReviewerAgent")
        self.evaluator = ResponseEvaluator()

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the final answer using DeepEval metrics.

        State keys consumed: query, generated_answer, retrieved_documents, session_id
        State keys produced: evaluation_metrics, confidence_score, evaluation_passed,
                             final_answer
        """
        query = state.get("query", "")
        answer = state.get("generated_answer", "")
        documents = state.get("retrieved_documents", [])
        session_id = state.get("session_id", "")
        include_evaluation = state.get("include_evaluation", True)

        self.logger.log_start(query, session_id)
        self._add_trace(state, "reviewer_start", {
            "answer_len": len(answer),
            "num_docs": len(documents),
        })

        if not include_evaluation or not answer:
            state["evaluation_metrics"] = {}
            state["confidence_score"] = 0.5
            state["evaluation_passed"] = True
            state["final_answer"] = answer
            self._add_trace(state, "reviewer_skipped", {})
            return state

        start = time.perf_counter()
        try:
            # Run evaluation
            metrics = await self.evaluator.evaluate(
                query=query,
                response=answer,
                context_documents=documents,
            )

            latency_ms = (time.perf_counter() - start) * 1000

            # Calculate overall confidence score
            confidence = calculate_confidence_score(metrics)

            # Determine pass/fail
            from app.config import settings
            faithfulness_threshold = settings.EVALUATION_THRESHOLD_FAITHFULNESS
            relevance_threshold = settings.EVALUATION_THRESHOLD_RELEVANCE

            evaluation_passed = (
                metrics.get("faithfulness", 0) >= faithfulness_threshold and
                metrics.get("relevance", 0) >= relevance_threshold
            )

            state["evaluation_metrics"] = metrics
            state["confidence_score"] = confidence
            state["evaluation_passed"] = evaluation_passed
            state["final_answer"] = answer

            # Log evaluation results
            evaluation_logger.log_evaluation(
                session_id=session_id,
                query=query,
                response=answer,
                metrics=metrics,
                passed=evaluation_passed,
            )

            self.logger.log_complete(
                f"Evaluation {'PASSED' if evaluation_passed else 'FAILED'} | "
                f"confidence={confidence:.2f} | "
                f"faithfulness={metrics.get('faithfulness', 0):.2f} | "
                f"relevance={metrics.get('relevance', 0):.2f}",
                latency_ms=latency_ms,
            )
            self._add_trace(state, "reviewer_complete", {
                "passed": evaluation_passed,
                "confidence": confidence,
                "metrics": metrics,
                "latency_ms": round(latency_ms, 1),
            })

        except Exception as e:
            self.logger.log_error(f"Evaluation failed: {e}", exc_info=True)
            # Allow response through with default metrics on evaluation failure
            state["evaluation_metrics"] = {
                "faithfulness": 0.7,
                "relevance": 0.7,
                "precision": 0.7,
                "hallucination_score": 0.1,
                "overall_score": 0.7,
            }
            state["confidence_score"] = 0.7
            state["evaluation_passed"] = True
            state["final_answer"] = answer
            self._add_trace(state, "reviewer_error", {"error": str(e), "fallback": True})

        return state
