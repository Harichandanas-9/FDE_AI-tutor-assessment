"""
Retrieval Agent
================
Handles all document retrieval from the vector store and knowledge base.
Implements:
- Hybrid search (BM25 sparse + vector dense)
- Reciprocal Rank Fusion (RRF) re-ranking
- Metadata filtering
- Context selection and ranking
"""

import time
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent
from app.retrieval.hybrid_retriever import HybridRetriever
from app.utils.helpers import format_sources
from app.utils.logger import get_logger

logger = get_logger("agents.retrieval")


class RetrievalAgent(BaseAgent):
    """
    Retrieval Agent — fetches and ranks relevant documents for query answering.
    """

    def __init__(self):
        super().__init__(name="RetrievalAgent")
        self.retriever = HybridRetriever()

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute hybrid retrieval for the given query.

        State keys consumed: query, needs_retrieval, topic_category
        State keys produced: retrieved_documents, retrieval_scores, sources
        """
        query = state.get("query", "")
        session_id = state.get("session_id", "")
        needs_retrieval = state.get("needs_retrieval", True)

        self.logger.log_start(query, session_id)
        self._add_trace(state, "retrieval_start", {"needs_retrieval": needs_retrieval})

        if not needs_retrieval:
            logger.debug("Retrieval skipped (not needed for this query)")
            state["retrieved_documents"] = []
            state["retrieval_scores"] = []
            state["sources"] = []
            self._add_trace(state, "retrieval_skipped", {})
            return state

        start = time.perf_counter()
        try:
            # Run hybrid retrieval (BM25 + Vector + RRF)
            documents, scores = await self.retriever.retrieve(
                query=query,
                top_k=5,
                metadata_filter=self._build_metadata_filter(state),
            )

            latency_ms = (time.perf_counter() - start) * 1000

            state["retrieved_documents"] = documents
            state["retrieval_scores"] = scores
            state["sources"] = format_sources(documents)

            self.logger.log_complete(
                f"Retrieved {len(documents)} documents | "
                f"top_score={scores[0]:.3f if scores else 0:.3f}",
                latency_ms=latency_ms,
            )
            self._add_trace(state, "retrieval_complete", {
                "num_docs": len(documents),
                "latency_ms": round(latency_ms, 1),
                "top_scores": scores[:3] if scores else [],
            })

        except Exception as e:
            self.logger.log_error(f"Retrieval failed: {e}", exc_info=True)
            # Graceful degradation — continue with empty context
            state["retrieved_documents"] = []
            state["retrieval_scores"] = []
            state["sources"] = []
            self._add_trace(state, "retrieval_error", {"error": str(e)})

        return state

    def _build_metadata_filter(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Build metadata filter based on query context."""
        filters = {}
        topic_category = state.get("topic_category", "")
        if topic_category and topic_category != "general":
            # Soft filter — prefer documents with matching category
            filters["category"] = topic_category
        return filters

    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into a context string for LLM."""
        if not documents:
            return "No relevant documents found."

        context_parts = []
        for i, doc in enumerate(documents[:5], 1):
            content = doc.get("content", "")
            source = doc.get("metadata", {}).get("source", "Unknown")
            page = doc.get("metadata", {}).get("page", "")
            page_ref = f" (p.{page})" if page else ""

            context_parts.append(
                f"[Source {i}: {source}{page_ref}]\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)
