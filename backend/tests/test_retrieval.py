"""
Retrieval Pipeline Tests
=========================
Tests for BM25, vector store, hybrid retrieval, and RRF ranking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.retrieval.bm25_retriever import BM25Retriever
from app.utils.helpers import chunk_text, clean_text


class TestBM25Retriever:
    """Unit tests for BM25 sparse retriever."""

    def setup_method(self):
        """Create fresh BM25 instance for each test."""
        self.retriever = BM25Retriever()

    def test_empty_index_returns_no_results(self):
        """Empty retriever should return no results."""
        docs, scores = self.retriever.retrieve("machine learning")
        assert docs == []
        assert scores == []

    def test_add_and_retrieve_documents(self):
        """Documents added to index should be retrievable."""
        test_docs = [
            {"id": "doc1", "content": "Python is a programming language", "metadata": {"source": "test"}},
            {"id": "doc2", "content": "Machine learning uses algorithms", "metadata": {"source": "test"}},
            {"id": "doc3", "content": "Neural networks are inspired by the brain", "metadata": {"source": "test"}},
        ]
        self.retriever.add_documents(test_docs)

        results, scores = self.retriever.retrieve("Python programming", top_k=2)
        assert len(results) > 0
        # Python doc should rank high
        contents = [r["content"] for r in results]
        assert any("Python" in c for c in contents)

    def test_scores_normalized(self):
        """BM25 scores should be normalized between 0 and 1."""
        test_docs = [
            {"id": "doc1", "content": "Data science and machine learning concepts", "metadata": {}},
            {"id": "doc2", "content": "Web development with JavaScript frameworks", "metadata": {}},
        ]
        self.retriever.add_documents(test_docs)
        _, scores = self.retriever.retrieve("machine learning", top_k=2)

        if scores:
            assert all(0.0 <= s <= 1.0 for s in scores)

    def test_irrelevant_query_returns_low_scores(self):
        """Queries unrelated to documents should return low or no scores."""
        test_docs = [
            {"id": "doc1", "content": "Python programming language features", "metadata": {}},
        ]
        self.retriever.add_documents(test_docs)
        results, scores = self.retriever.retrieve("xyzabc unrelated gibberish", top_k=5)
        # Should return empty or very low scores
        assert len(results) == 0 or (scores and max(scores) < 0.5)

    def test_document_count(self):
        """Document count should reflect added documents."""
        assert self.retriever.get_document_count() == 0
        test_docs = [{"id": f"doc{i}", "content": f"Content {i}", "metadata": {}} for i in range(5)]
        self.retriever.add_documents(test_docs)
        assert self.retriever.get_document_count() == 5

    def test_clear_index(self):
        """Clearing the index should remove all documents."""
        test_docs = [{"id": "doc1", "content": "Test content", "metadata": {}}]
        self.retriever.add_documents(test_docs)
        self.retriever.clear()
        assert self.retriever.get_document_count() == 0


class TestHybridRetrieverRRF:
    """Tests for Reciprocal Rank Fusion logic."""

    def test_rrf_merges_results(self):
        """RRF should merge results from multiple rankers."""
        from app.retrieval.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()

        bm25_results = [
            {"id": "doc1", "content": "Doc 1", "metadata": {}},
            {"id": "doc2", "content": "Doc 2", "metadata": {}},
            {"id": "doc3", "content": "Doc 3", "metadata": {}},
        ]

        vector_results = [
            {"id": "doc2", "content": "Doc 2", "metadata": {}},
            {"id": "doc4", "content": "Doc 4", "metadata": {}},
            {"id": "doc1", "content": "Doc 1", "metadata": {}},
        ]

        fused, scores = retriever._reciprocal_rank_fusion(
            results_list=[
                (bm25_results, 0.5),
                (vector_results, 0.5),
            ],
            k=60,
            top_k=4,
        )

        # doc1 and doc2 appear in both lists — should rank high
        fused_ids = [d["id"] for d in fused]
        assert "doc1" in fused_ids
        assert "doc2" in fused_ids

    def test_rrf_scores_normalized(self):
        """RRF scores should be normalized."""
        from app.retrieval.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()
        results = [{"id": f"doc{i}", "content": f"Content {i}", "metadata": {}} for i in range(5)]
        _, scores = retriever._reciprocal_rank_fusion(
            results_list=[(results, 1.0)],
            k=60,
            top_k=5,
        )
        if scores:
            assert max(scores) <= 1.0
            assert min(scores) >= 0.0


class TestTextProcessing:
    """Tests for text chunking and cleaning utilities."""

    def test_chunk_short_text_returns_single_chunk(self):
        """Short text should return as a single chunk."""
        short = "This is a short text."
        chunks = chunk_text(short, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == short

    def test_chunk_long_text_splits_correctly(self):
        """Long text should be split into multiple chunks."""
        long = "word " * 300  # 1500 chars
        chunks = chunk_text(long, chunk_size=500, chunk_overlap=100)
        assert len(chunks) > 1
        # All chunks should be non-empty
        assert all(c.strip() for c in chunks)

    def test_clean_text_removes_control_chars(self):
        """Clean text should remove control characters."""
        dirty = "Hello\x00World\x01Test"
        cleaned = clean_text(dirty)
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned
        assert "Hello" in cleaned

    def test_clean_text_normalizes_whitespace(self):
        """Multiple spaces should be normalized."""
        messy = "Hello    World   Python"
        cleaned = clean_text(messy)
        assert "  " not in cleaned
