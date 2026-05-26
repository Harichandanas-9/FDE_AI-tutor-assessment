"""
Hybrid Retriever with Reciprocal Rank Fusion (RRF)
====================================================
Combines BM25 (sparse/keyword) and ChromaDB (dense/semantic) retrieval.
Uses Reciprocal Rank Fusion to merge and re-rank results from both retrievers.

RRF Formula: RRF_score(d) = Σ 1/(k + rank_i(d))
Where k=60 (tuning constant), rank_i = position in each ranker's list.

This produces superior retrieval compared to either method alone:
- BM25 catches exact keyword matches
- Vector search catches semantic meaning
- RRF combines both into a single ranked list
"""

from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.retrieval.bm25_retriever import bm25_retriever, BM25Retriever
from app.retrieval.vector_store import vector_store, VectorStore
from app.utils.logger import get_logger

logger = get_logger("retrieval.hybrid")

# RRF constant (standard value recommended by Cormack et al.)
RRF_K = 60


class HybridRetriever:
    """
    Hybrid retriever that fuses BM25 and vector search results using RRF.

    Retrieval pipeline:
    1. Run BM25 sparse retrieval
    2. Run vector (semantic) dense retrieval
    3. Apply Reciprocal Rank Fusion to merge rankings
    4. Return top-k fused results
    """

    def __init__(
        self,
        bm25: Optional[BM25Retriever] = None,
        vs: Optional[VectorStore] = None,
        alpha: float = None,
    ):
        """
        Args:
            bm25: BM25Retriever instance (uses singleton by default)
            vs: VectorStore instance (uses singleton by default)
            alpha: Weight for vector search vs BM25 (0=all BM25, 1=all vector)
                   Uses settings.HYBRID_SEARCH_ALPHA by default
        """
        self._bm25 = bm25 or bm25_retriever
        self._vs = vs or vector_store
        self._alpha = alpha if alpha is not None else settings.HYBRID_SEARCH_ALPHA

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        fetch_k: int = 20,
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Execute hybrid retrieval with RRF re-ranking.

        Args:
            query: User query string
            top_k: Number of final results to return
            metadata_filter: Metadata filter for vector search
            fetch_k: Number of candidates to fetch from each retriever

        Returns:
            Tuple of (documents, rrf_scores)
        """
        logger.debug(
            f"Hybrid retrieval: query='{query[:60]}' | top_k={top_k} | alpha={self._alpha}"
        )

        # --- Step 1: BM25 Sparse Retrieval ---
        bm25_docs, bm25_scores = self._bm25.retrieve(query, top_k=fetch_k)
        logger.debug(f"BM25: {len(bm25_docs)} results")

        # --- Step 2: Vector Dense Retrieval ---
        vector_docs, vector_scores = await self._vs.search(
            query=query,
            top_k=fetch_k,
            metadata_filter=metadata_filter,
        )
        logger.debug(f"Vector: {len(vector_docs)} results")

        # Handle edge cases
        if not bm25_docs and not vector_docs:
            logger.warning("Both BM25 and vector search returned no results")
            return [], []

        if not bm25_docs:
            return vector_docs[:top_k], vector_scores[:top_k]

        if not vector_docs:
            return bm25_docs[:top_k], bm25_scores[:top_k]

        # --- Step 3: Reciprocal Rank Fusion ---
        fused_docs, fused_scores = self._reciprocal_rank_fusion(
            results_list=[
                (bm25_docs, 1.0 - self._alpha),     # BM25 weight
                (vector_docs, self._alpha),           # Vector weight
            ],
            k=RRF_K,
            top_k=top_k,
        )

        logger.info(
            f"Hybrid retrieval complete: "
            f"bm25={len(bm25_docs)}, vector={len(vector_docs)}, "
            f"fused={len(fused_docs)}"
        )

        return fused_docs, fused_scores

    def _reciprocal_rank_fusion(
        self,
        results_list: List[Tuple[List[Dict[str, Any]], float]],
        k: int = 60,
        top_k: int = 5,
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Apply Reciprocal Rank Fusion across multiple ranked lists.

        Args:
            results_list: List of (documents, weight) tuples
            k: RRF constant (default 60 per paper recommendation)
            top_k: Number of results to return

        Returns:
            (merged_documents, rrf_scores) sorted by RRF score descending
        """
        # Map from document ID to {doc, rrf_score}
        doc_scores: Dict[str, Dict[str, Any]] = {}

        for docs, weight in results_list:
            for rank, doc in enumerate(docs):
                doc_id = doc.get("id", f"doc_{rank}")

                # RRF contribution from this ranker
                rrf_contribution = weight * (1.0 / (k + rank + 1))

                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "doc": doc,
                        "rrf_score": 0.0,
                    }
                doc_scores[doc_id]["rrf_score"] += rrf_contribution

        # Sort by RRF score descending
        sorted_items = sorted(
            doc_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )[:top_k]

        fused_docs = [item["doc"] for item in sorted_items]
        fused_scores = [item["rrf_score"] for item in sorted_items]

        # Normalize RRF scores to [0, 1]
        if fused_scores:
            max_score = fused_scores[0]
            if max_score > 0:
                fused_scores = [s / max_score for s in fused_scores]

        return fused_docs, fused_scores

    async def add_documents(
        self,
        chunks: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """
        Index documents in both BM25 and vector store.

        Args:
            chunks: Document text chunks
            metadatas: Metadata for each chunk
            ids: Unique IDs for each chunk
        """
        documents = [
            {"id": doc_id, "content": content, "metadata": meta}
            for doc_id, content, meta in zip(ids, chunks, metadatas)
        ]

        # Add to BM25 index
        self._bm25.add_documents(documents)

        # Add to vector store
        await self._vs.add_documents(
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info(f"Indexed {len(chunks)} chunks in hybrid retriever")

    def get_stats(self) -> Dict[str, int]:
        """Return retriever statistics."""
        return {
            "bm25_documents": self._bm25.get_document_count(),
            "vector_documents": self._vs.get_document_count(),
        }
