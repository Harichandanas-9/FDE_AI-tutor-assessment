"""
Main Multi-Agent Workflow (LangGraph)
======================================
Implements the complete agent orchestration using LangGraph StateGraph.

Full Workflow:
  User Input
    → Security Check
    → Memory Agent (pre - retrieve context)
    → Supervisor Agent (routing)
    → Retrieval Agent (hybrid RAG)
    → [Quiz Agent | Recommendation Agent | Generation Agent]
    → Critic Agent (reflection gate)
    → Correction Agent (if needed, loop up to 3x)
    → Reviewer Agent (DeepEval evaluation)
    → Memory Agent (post - store exchange)
    → Final Response

Each node is an agent's run() method.
Edges use conditional routing based on state flags.
"""

import time
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from app.agents.supervisor_agent import SupervisorAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.generation_agent import GenerationAgent
from app.agents.critic_agent import CriticAgent
from app.agents.correction_agent import CorrectionAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.security.security_middleware import run_security_checks
from app.utils.logger import get_logger

logger = get_logger("workflows.main")


# ─────────────────────────────────────────────────────────────
#  Agent instances (shared across workflow invocations)
# ─────────────────────────────────────────────────────────────
supervisor = SupervisorAgent()
retrieval = RetrievalAgent()
generation = GenerationAgent()
critic = CriticAgent()
correction = CorrectionAgent()
reviewer = ReviewerAgent()
quiz = QuizAgent()
memory = MemoryAgent()
recommendation = RecommendationAgent()


# ─────────────────────────────────────────────────────────────
#  Node wrappers (LangGraph nodes must accept and return dict)
# ─────────────────────────────────────────────────────────────

async def security_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run security checks on the raw user query."""
    query = state.get("query", "")
    mode = state.get("mode", "chat")

    result = await run_security_checks(query=query, mode=mode)

    if not result.is_safe:
        logger.warning(
            f"Security check blocked query: level={result.threat_level} | "
            f"reason='{result.blocked_reason[:80]}'"
        )
        state["is_safe"] = False
        state["security_message"] = result.blocked_reason
        state["final_answer"] = result.blocked_reason
        state["confidence_score"] = 0.0
        state["completed"] = True
    else:
        state["is_safe"] = True
        state["query"] = result.sanitized_query  # Use sanitized version
        state["security_message"] = None

    return state


async def memory_pre_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Memory Agent: retrieve context before generation."""
    return await memory.run(state)


async def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Supervisor Agent: analyze intent and route."""
    return await supervisor.run(state)


async def retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieval Agent: hybrid search."""
    return await retrieval.run(state)


async def generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generation Agent: produce answer."""
    return await generation.run(state)


async def quiz_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Quiz Agent: generate MCQ questions."""
    return await quiz.run(state)


async def recommendation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Recommendation Agent: suggest next topics."""
    return await recommendation.run(state)


async def critic_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Critic Agent: evaluate and flag issues."""
    return await critic.run(state)


async def correction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Correction Agent: improve the answer."""
    return await correction.run(state)


async def reviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Reviewer Agent: DeepEval quality assessment."""
    return await reviewer.run(state)


async def memory_post_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Memory Agent: store exchange after generation."""
    # Only store if we have a real answer
    if state.get("final_answer") or state.get("generated_answer"):
        answer = state.get("final_answer") or state.get("generated_answer", "")
        state_copy = {**state, "generated_answer": answer}
        await memory.run(state_copy)
    return state


# ─────────────────────────────────────────────────────────────
#  Conditional Edge Functions
# ─────────────────────────────────────────────────────────────

def after_security(state: Dict[str, Any]) -> str:
    """Route after security check."""
    if not state.get("is_safe", True):
        return "blocked"
    return "memory_pre"


def after_supervisor(state: Dict[str, Any]) -> str:
    """Route to appropriate generation agent based on intent."""
    primary_agent = state.get("primary_agent", "generation")
    mode = state.get("mode", "chat")

    if mode == "quiz" or primary_agent == "quiz":
        return "quiz"
    if mode == "recommend" or primary_agent == "recommendation":
        return "recommendation"
    return "retrieval"


def after_primary_agent(state: Dict[str, Any]) -> str:
    """
    After primary generation (or quiz/recommendation), decide:
    - If needs_reflection is True: go to critic
    - Otherwise: go directly to reviewer
    """
    needs_reflection = state.get("needs_reflection", False)
    mode = state.get("mode", "chat")

    # Quiz and recommendation modes skip reflection
    if mode in ("quiz", "recommend"):
        return "reviewer"

    if needs_reflection:
        return "critic"
    return "reviewer"


def after_critic(state: Dict[str, Any]) -> str:
    """After critic evaluation, decide whether correction is needed."""
    needs_correction = state.get("reflection_needed", False)
    if needs_correction:
        return "correction"
    return "reviewer"


def after_correction(state: Dict[str, Any]) -> str:
    """After correction, go back to critic for re-evaluation or proceed."""
    iterations = state.get("reflection_iterations", 0)
    max_iterations = 3

    if iterations < max_iterations:
        return "critic"  # Re-evaluate the corrected answer
    return "reviewer"


def is_blocked(state: Dict[str, Any]) -> str:
    """Check if response is blocked."""
    if state.get("completed"):
        return "end"
    return "continue"


# ─────────────────────────────────────────────────────────────
#  Build the LangGraph StateGraph
# ─────────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Construct and compile the full multi-agent workflow graph.

    Graph topology:
      security → [blocked|memory_pre]
      memory_pre → supervisor
      supervisor → [quiz|recommendation|retrieval]
      retrieval → generation
      [quiz|recommendation|generation] → [critic|reviewer]
      critic → [correction|reviewer]
      correction → [critic|reviewer]
      reviewer → memory_post → END
    """
    graph = StateGraph(dict)

    # --- Add nodes ---
    graph.add_node("security", security_node)
    graph.add_node("memory_pre", memory_pre_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("generation", generation_node)
    graph.add_node("quiz", quiz_node)
    graph.add_node("recommendation", recommendation_node)
    graph.add_node("critic", critic_node)
    graph.add_node("correction", correction_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("memory_post", memory_post_node)

    # --- Entry point ---
    graph.set_entry_point("security")

    # --- Edges ---

    # Security → memory_pre (safe) or END (blocked)
    graph.add_conditional_edges(
        "security",
        after_security,
        {
            "blocked": END,
            "memory_pre": "memory_pre",
        },
    )

    # Memory pre → supervisor
    graph.add_edge("memory_pre", "supervisor")

    # Supervisor → quiz | recommendation | retrieval
    graph.add_conditional_edges(
        "supervisor",
        after_supervisor,
        {
            "quiz": "quiz",
            "recommendation": "recommendation",
            "retrieval": "retrieval",
        },
    )

    # Retrieval → generation
    graph.add_edge("retrieval", "generation")

    # Generation → critic | reviewer
    graph.add_conditional_edges(
        "generation",
        after_primary_agent,
        {
            "critic": "critic",
            "reviewer": "reviewer",
        },
    )

    # Quiz → reviewer (no reflection for quiz)
    graph.add_conditional_edges(
        "quiz",
        after_primary_agent,
        {
            "critic": "critic",
            "reviewer": "reviewer",
        },
    )

    # Recommendation → reviewer
    graph.add_conditional_edges(
        "recommendation",
        after_primary_agent,
        {
            "critic": "critic",
            "reviewer": "reviewer",
        },
    )

    # Critic → correction | reviewer
    graph.add_conditional_edges(
        "critic",
        after_critic,
        {
            "correction": "correction",
            "reviewer": "reviewer",
        },
    )

    # Correction → critic (re-evaluate) | reviewer (max iterations)
    graph.add_conditional_edges(
        "correction",
        after_correction,
        {
            "critic": "critic",
            "reviewer": "reviewer",
        },
    )

    # Reviewer → memory_post → END
    graph.add_edge("reviewer", "memory_post")
    graph.add_edge("memory_post", END)

    return graph


# ─────────────────────────────────────────────────────────────
#  Compiled workflow (singleton)
# ─────────────────────────────────────────────────────────────

_workflow_graph = build_workflow()
compiled_workflow = _workflow_graph.compile()


# ─────────────────────────────────────────────────────────────
#  Main execution function
# ─────────────────────────────────────────────────────────────

async def run_workflow(
    query: str,
    session_id: str,
    mode: str = "chat",
    include_evaluation: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """
    Execute the full multi-agent workflow for a user query.

    Args:
        query: User's question
        session_id: Unique session identifier
        mode: chat | quiz | summarize | explain | recommend
        include_evaluation: Whether to run DeepEval metrics
        **kwargs: Additional state parameters (num_questions, difficulty, etc.)

    Returns:
        Final state dict with answer, sources, evaluation, traces
    """
    start_time = time.perf_counter()

    # Initialize state
    initial_state: Dict[str, Any] = {
        "query": query,
        "session_id": session_id,
        "mode": mode,
        "include_evaluation": include_evaluation,
        "is_safe": True,
        "retrieved_documents": [],
        "retrieval_scores": [],
        "generated_answer": "",
        "draft_answer": "",
        "reflection_needed": False,
        "reflection_feedback": "",
        "reflection_iterations": 0,
        "hallucination_detected": False,
        "evaluation_metrics": {},
        "confidence_score": 0.0,
        "evaluation_passed": False,
        "final_answer": "",
        "sources": [],
        "follow_up_topics": [],
        "agent_traces": [],
        "total_tokens": 0,
        "completed": False,
        "error": None,
        **kwargs,
    }

    try:
        logger.info(
            f"Workflow started: session={session_id[:8]} | mode={mode} | "
            f"query='{query[:60]}'"
        )

        # Execute the compiled workflow
        final_state = await compiled_workflow.ainvoke(initial_state)

        total_latency_ms = (time.perf_counter() - start_time) * 1000

        # Ensure final_answer is set
        if not final_state.get("final_answer"):
            final_state["final_answer"] = final_state.get("generated_answer", "")

        final_state["total_latency_ms"] = round(total_latency_ms, 1)

        logger.info(
            f"Workflow completed: session={session_id[:8]} | "
            f"latency={total_latency_ms:.0f}ms | "
            f"confidence={final_state.get('confidence_score', 0):.2f} | "
            f"reflections={final_state.get('reflection_iterations', 0)}"
        )

        return final_state

    except Exception as e:
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Workflow failed: {e}", exc_info=True)

        return {
            **initial_state,
            "final_answer": "I encountered an error processing your request. Please try again.",
            "error": str(e),
            "confidence_score": 0.0,
            "evaluation_metrics": {},
            "total_latency_ms": round(total_latency_ms, 1),
        }
