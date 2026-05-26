"""
BM25 Sparse Retriever
======================
Keyword-based retrieval using BM25 (Best Match 25) algorithm.
Complements semantic search in the hybrid retrieval pipeline.

BM25 excels at:
- Exact keyword matching
- Rare term retrieval
- Short, specific queries
- Technical terminology matching
"""

import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

from app.utils.logger import get_logger

logger = get_logger("retrieval.bm25")

BM25_INDEX_PATH = Path("./data/bm25_index.pkl")


class BM25Retriever:
    """
    BM25-based sparse retriever.
    Maintains an in-memory index of all document chunks.
    The index is persisted to disk and reloaded on startup.
    """

    def __init__(self):
        self._index: Optional[BM25Okapi] = None
        self._documents: List[Dict[str, Any]] = []
        self._tokenized_corpus: List[List[str]] = []
        self._is_initialized = False

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing.
        Lowercases and splits on non-alphanumeric characters.
        """
        # Lowercase and split
        tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
        # Remove very short tokens
        return [t for t in tokens if len(t) > 1]

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the BM25 index.

        Args:
            documents: List of {id, content, metadata} dicts
        """
        if not documents:
            return

        # Extend corpus
        new_tokenized = [self._tokenize(doc["content"]) for doc in documents]
        self._tokenized_corpus.extend(new_tokenized)
        self._documents.extend(documents)

        # Rebuild BM25 index
        if self._tokenized_corpus:
            self._index = BM25Okapi(self._tokenized_corpus)
            self._is_initialized = True
            logger.info(
                f"BM25 index rebuilt: total_docs={len(self._documents)}"
            )

        # Persist to disk
        self._save_index()

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Retrieve top-k documents by BM25 score.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            Tuple of (documents, normalized_scores)
        """
        if not self._is_initialized or not self._index:
            logger.debug("BM25 index not initialized — returning empty results")
            return [], []

        if not self._documents:
            return [], []

        try:
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return [], []

            # Get BM25 scores for all documents
            scores = self._index.get_scores(query_tokens)

            # Get top-k indices
            actual_k = min(top_k, len(scores))
            top_indices = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:actual_k]

            # Filter zero-score results
            top_indices = [i for i in top_indices if scores[i] > 0]

            if not top_indices:
                return [], []

            # Normalize scores to [0, 1]
            max_score = scores[top_indices[0]] if top_indices else 1.0
            normalized_scores = [
                scores[i] / max_score if max_score > 0 else 0.0
                for i in top_indices
            ]

            docs = [self._documents[i] for i in top_indices]

            logger.debug(
                f"BM25 retrieved {len(docs)} results | "
                f"top_score={normalized_scores[0]:.3f}"
            )
            return docs, normalized_scores

        except Exception as e:
            logger.error(f"BM25 retrieval failed: {e}", exc_info=True)
            return [], []

    def _save_index(self) -> None:
        """Persist the BM25 index and documents to disk."""
        try:
            BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(BM25_INDEX_PATH, "wb") as f:
                pickle.dump(
                    {
                        "documents": self._documents,
                        "tokenized_corpus": self._tokenized_corpus,
                    },
                    f,
                )
            logger.debug(f"BM25 index saved: {len(self._documents)} docs")
        except Exception as e:
            logger.warning(f"Failed to save BM25 index: {e}")

    def load_index(self) -> bool:
        """Load persisted BM25 index from disk."""
        if not BM25_INDEX_PATH.exists():
            logger.debug("No persisted BM25 index found — starting fresh")
            return False

        try:
            with open(BM25_INDEX_PATH, "rb") as f:
                data = pickle.load(f)

            self._documents = data["documents"]
            self._tokenized_corpus = data["tokenized_corpus"]

            if self._tokenized_corpus:
                self._index = BM25Okapi(self._tokenized_corpus)
                self._is_initialized = True
                logger.info(
                    f"BM25 index loaded: {len(self._documents)} documents"
                )
            return True

        except Exception as e:
            logger.warning(f"Failed to load BM25 index: {e}")
            return False

    def remove_documents(self, doc_ids: List[str]) -> int:
        """Remove documents by ID from the index."""
        before = len(self._documents)
        self._documents = [d for d in self._documents if d.get("id") not in doc_ids]
        self._tokenized_corpus = [
            self._tokenize(d["content"]) for d in self._documents
        ]
        if self._tokenized_corpus:
            self._index = BM25Okapi(self._tokenized_corpus)
        removed = before - len(self._documents)
        if removed > 0:
            logger.info(f"Removed {removed} documents from BM25 index")
            self._save_index()
        return removed

    def get_document_count(self) -> int:
        """Return number of documents in the BM25 index."""
        return len(self._documents)

    def clear(self) -> None:
        """Clear all documents from the index."""
        self._documents = []
        self._tokenized_corpus = []
        self._index = None
        self._is_initialized = False
        if BM25_INDEX_PATH.exists():
            BM25_INDEX_PATH.unlink()
        logger.info("BM25 index cleared")


# Singleton instance
bm25_retriever = BM25Retriever()
