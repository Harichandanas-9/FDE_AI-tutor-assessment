"""Pytest configuration and shared fixtures."""
import os
import pytest

# Set test environment variables before any app imports
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-testing-only")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-minimum-32chars-ok")
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")

@pytest.fixture(scope="session")
def sample_documents():
    return [
        {
            "id": "sample_doc_1",
            "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
            "metadata": {"source": "test_doc.pdf", "page": "1", "type": "pdf"},
        },
        {
            "id": "sample_doc_2",
            "content": "Neural networks are computational models inspired by biological neural structures.",
            "metadata": {"source": "test_doc.pdf", "page": "2", "type": "pdf"},
        },
        {
            "id": "sample_doc_3",
            "content": "Python is a high-level programming language known for its simplicity and readability.",
            "metadata": {"source": "python_guide.pdf", "page": "1", "type": "pdf"},
        },
    ]
