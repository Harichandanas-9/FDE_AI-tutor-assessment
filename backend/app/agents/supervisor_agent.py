"""
Supervisor Agent
================
Orchestrates the multi-agent workflow by:
1. Analyzing user intent
2. Routing to the correct agents
3. Managing state transitions
4. Determining if reflection is needed
5. Selecting appropriate mode (chat/quiz/summarize/recommend)

The Supervisor is the "brain" of the system — it decides WHAT to do and WHO does it.
"""

import json
from typing import Any, Dict, Literal

from app.agents.base_agent import BaseAgent
from app.utils.helpers import extract_json_from_text
from app.utils.logger import get_logger

logger = get_logger("agents.supervisor")

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor Agent of an AI educational learning system.
Your role is to analyze user queries and determine the optimal processing strategy.

Available agents and their responsibilities:
- retrieval: Fetch relevant learning materials from the knowledge base
- generation: Generate educational explanations and answers
- quiz: Generate quiz questions and MCQs
- memory: Store and retrieve conversation context
- recommendation: Suggest learning paths and next topics
- reflection: Critically evaluate and improve generated answers (use for complex queries)
- reviewer: Evaluate response quality and check for hallucinations

For each query, output a JSON object with:
{
  "intent": "explain|quiz|summarize|recommend|answer|notes",
  "complexity": "simple|moderate|complex",
  "needs_retrieval": true|false,
  "needs_reflection": true|false,
  "primary_agent": "generation|quiz|recommendation",
  "reasoning": "brief explanation of routing decision",
  "topic_category": "math|science|programming|history|language|general",
  "estimated_difficulty": "beginner|intermediate|advanced"
}

Rules:
- needs_reflection = true for complex, multi-step, or technical queries
- needs_reflection = false for simple factual questions or quiz requests
- needs_retrieval = true unless the query is purely conversational
- For quiz mode: primary_agent = "quiz"
- For recommendations: primary_agent = "recommendation"
"""


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent — routes queries, manages workflow decisions.
    """

    def __init__(self):
        super().__init__(name="SupervisorAgent")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the query and populate routing decisions in state.

        State keys consumed: query, mode
        State keys produced: intent, needs_reflection, needs_retrieval,
                             primary_agent, topic_category, complexity
        """
        query = state.get("query", "")
        mode = state.get("mode", "chat")
        session_id = state.get("session_id", "")

        self.logger.log_start(query, session_id)
        self._add_trace(state, "supervisor_start", {"mode": mode, "query_len": len(query)})

        # Handle explicit modes directly without LLM routing
        if mode == "quiz":
            state.update({
                "intent": "quiz",
                "complexity": "moderate",
                "needs_retrieval": True,
                "needs_reflection": False,
                "primary_agent": "quiz",
                "topic_category": "general",
                "estimated_difficulty": "mixed",
            })
            self.logger.log_complete("Routed to quiz mode (explicit)")
            self._add_trace(state, "supervisor_complete", {"routing": "quiz_explicit"})
            return state

        if mode == "recommend":
            state.update({
                "intent": "recommend",
                "complexity": "simple",
                "needs_retrieval": False,
                "needs_reflection": False,
                "primary_agent": "recommendation",
                "topic_category": "general",
                "estimated_difficulty": "mixed",
            })
            self.logger.log_complete("Routed to recommendation mode (explicit)")
            self._add_trace(state, "supervisor_complete", {"routing": "recommend_explicit"})
            return state

        # Use LLM for intelligent routing
        try:
            messages = [
                {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Query: {query}\nMode hint: {mode}"},
            ]
            response = await self.call_llm(messages, temperature=0.1, max_tokens=512)

            routing = extract_json_from_text(response)
            if not routing:
                # Fallback defaults if JSON extraction fails
                routing = {
                    "intent": mode,
                    "complexity": "moderate",
                    "needs_retrieval": True,
                    "needs_reflection": len(query) > 200,
                    "primary_agent": "generation",
                    "topic_category": "general",
                    "estimated_difficulty": "intermediate",
                }

            state.update({
                "intent": routing.get("intent", mode),
                "complexity": routing.get("complexity", "moderate"),
                "needs_retrieval": routing.get("needs_retrieval", True),
                "needs_reflection": routing.get("needs_reflection", False),
                "primary_agent": routing.get("primary_agent", "generation"),
                "topic_category": routing.get("topic_category", "general"),
                "estimated_difficulty": routing.get("estimated_difficulty", "intermediate"),
                "supervisor_reasoning": routing.get("reasoning", ""),
            })

            self.logger.log_complete(
                f"Routed: intent={routing.get('intent')} | "
                f"reflection={routing.get('needs_reflection')} | "
                f"primary={routing.get('primary_agent')}"
            )
            self._add_trace(state, "supervisor_complete", {
                "intent": routing.get("intent"),
                "primary_agent": routing.get("primary_agent"),
                "needs_reflection": routing.get("needs_reflection"),
            })

        except Exception as e:
            self.logger.log_error(f"Supervisor routing failed: {e}", exc_info=True)
            # Safe defaults on error
            state.update({
                "intent": "answer",
                "complexity": "moderate",
                "needs_retrieval": True,
                "needs_reflection": False,
                "primary_agent": "generation",
                "topic_category": "general",
                "estimated_difficulty": "intermediate",
                "supervisor_reasoning": "fallback_due_to_error",
            })

        return state
