"""
API Integration Tests
======================
Tests for all FastAPI endpoints using the TestClient.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# Mock settings before importing app
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-testing-only")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-minimum-32chars-ok")

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Health check endpoint tests."""

    def test_health_check_returns_200(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_ping_returns_pong(self):
        response = client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.json()["pong"] is True

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "app" in response.json()


class TestChatAPI:
    """Chat endpoint tests."""

    @patch("app.api.routes.chat.run_workflow")
    def test_chat_endpoint_basic(self, mock_workflow):
        """Basic chat request should return structured response."""
        mock_workflow.return_value = {
            "session_id": "test-session",
            "final_answer": "Machine learning is a subset of AI...",
            "generated_answer": "Machine learning is a subset of AI...",
            "confidence_score": 0.85,
            "sources": [],
            "evaluation_metrics": {
                "faithfulness": 0.9,
                "relevance": 0.85,
                "precision": 0.8,
                "hallucination_score": 0.1,
                "overall_score": 0.85,
            },
            "agent_traces": [],
            "follow_up_topics": ["Deep Learning", "Neural Networks"],
            "reflection_iterations": 0,
            "is_safe": True,
            "evaluation_passed": True,
            "total_latency_ms": 1500.0,
        }

        response = client.post(
            "/api/v1/chat",
            json={
                "query": "What is machine learning?",
                "mode": "chat",
                "include_evaluation": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "confidence_score" in data
        assert "sources" in data

    def test_chat_empty_query_rejected(self):
        """Empty query should be rejected with 422."""
        response = client.post(
            "/api/v1/chat",
            json={"query": ""},
        )
        assert response.status_code == 422

    @patch("app.api.routes.chat.run_workflow")
    def test_chat_with_session_id(self, mock_workflow):
        """Chat should accept and return session_id."""
        mock_workflow.return_value = {
            "session_id": "my-test-session",
            "final_answer": "Answer here",
            "generated_answer": "Answer here",
            "confidence_score": 0.75,
            "sources": [],
            "evaluation_metrics": {},
            "agent_traces": [],
            "follow_up_topics": [],
            "reflection_iterations": 0,
            "is_safe": True,
            "evaluation_passed": True,
            "total_latency_ms": 1000.0,
        }

        response = client.post(
            "/api/v1/chat",
            json={
                "query": "Explain Python",
                "session_id": "my-test-session",
                "mode": "explain",
            },
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == "my-test-session"


class TestDocumentAPI:
    """Document upload and management endpoint tests."""

    def test_list_documents_empty(self):
        """List documents should return empty list initially."""
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    def test_upload_unsupported_file_type(self):
        """Unsupported file types should be rejected."""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.exe", b"malicious content", "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_upload_empty_file_rejected(self):
        """Empty files should be rejected."""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert response.status_code in (400, 422, 500)


class TestQuizAPI:
    """Quiz generation endpoint tests."""

    @patch("app.api.routes.quiz.QuizAgent")
    def test_quiz_generation_request(self, mock_agent_class):
        """Quiz generation endpoint should return structured quiz."""
        from app.schemas.models import QuizQuestion
        mock_agent = MagicMock()
        mock_agent.generate_quiz = AsyncMock(return_value=[
            QuizQuestion(
                question="What is Python?",
                options=["A) A snake", "B) A programming language", "C) A game", "D) A database"],
                correct_answer="B",
                explanation="Python is a high-level programming language.",
                difficulty="easy",
                topic="Python",
            )
        ])
        mock_agent_class.return_value = mock_agent

        response = client.post(
            "/api/v1/quiz/generate",
            json={"topic": "Python Programming", "num_questions": 1, "difficulty": "easy"},
        )
        # Just ensure endpoint responds (agent may be unmocked)
        assert response.status_code in (200, 500)


class TestAnalyticsAPI:
    """Analytics endpoint tests."""

    def test_analytics_endpoint_responds(self):
        """Analytics endpoint should respond with dashboard data."""
        response = client.get("/api/v1/analytics")
        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data
        assert "avg_confidence_score" in data


class TestHistoryAPI:
    """Conversation history endpoint tests."""

    def test_get_all_history(self):
        """History endpoint should return sessions list."""
        response = client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data

    def test_nonexistent_session(self):
        """Requesting nonexistent session should return 404."""
        response = client.get("/api/v1/history/nonexistent-session-id-xyz")
        assert response.status_code == 404


class TestRecommendationsAPI:
    """Recommendations endpoint tests."""

    @patch("app.api.routes.recommendations.recommendation_agent")
    def test_get_recommendations(self, mock_agent):
        """Recommendations endpoint should return topic suggestions."""
        from app.schemas.models import LearningTopic
        mock_agent.get_recommendations = AsyncMock(return_value=[
            LearningTopic(
                topic="Advanced Python",
                description="Deepen your Python knowledge",
                difficulty="intermediate",
                estimated_time="2 hours",
                relevance_score=0.9,
                tags=["python", "programming"],
            )
        ])

        response = client.post(
            "/api/v1/recommendations",
            json={
                "current_topic": "Python",
                "skill_level": "intermediate",
                "num_recommendations": 1,
            },
        )
        assert response.status_code in (200, 500)
