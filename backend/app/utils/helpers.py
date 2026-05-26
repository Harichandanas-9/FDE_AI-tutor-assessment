"""
General-Purpose Helpers
=======================
Shared utility functions used across agents, retrieval, and API layers.
"""

import hashlib
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def generate_document_id(content: str, source: str = "") -> str:
    """Generate a deterministic document ID based on content hash."""
    combined = f"{source}::{content[:500]}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def truncate_text(text: str, max_chars: int = 500, suffix: str = "...") -> str:
    """Truncate text to a maximum character count."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """
    Clean text by removing excessive whitespace, control characters,
    and normalizing line endings.
    """
    # Remove null bytes and control chars (except newlines/tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize multiple whitespace
    text = re.sub(r" +", " ", text)
    # Normalize multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[str]:
    """
    Split text into overlapping chunks for RAG indexing.

    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between consecutive chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end near the boundary
            boundary = text.rfind(". ", start, end)
            if boundary > start + chunk_size // 2:
                end = boundary + 1

        chunks.append(text[start:end].strip())
        start = end - chunk_overlap
        if start >= len(text):
            break

    return [c for c in chunks if c]


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to extract a JSON object from text that may contain
    other content around the JSON block.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON within markdown code blocks
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Try to find raw JSON object
    brace_pattern = r"\{[\s\S]*\}"
    matches = re.findall(brace_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    return None


def format_sources(documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Format retrieved documents into clean source references.

    Args:
        documents: List of retrieved document dicts with metadata

    Returns:
        List of formatted source reference dicts
    """
    sources = []
    seen_sources = set()

    for doc in documents:
        source = doc.get("metadata", {}).get("source", "Unknown Source")
        page = doc.get("metadata", {}).get("page", "")
        doc_type = doc.get("metadata", {}).get("type", "document")

        source_key = f"{source}:{page}"
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        sources.append({
            "source": source,
            "page": str(page) if page else "",
            "type": doc_type,
            "excerpt": truncate_text(doc.get("content", ""), 150),
        })

    return sources[:5]  # Return top 5 unique sources


def calculate_confidence_score(metrics: Dict[str, float]) -> float:
    """
    Calculate an overall confidence score from individual evaluation metrics.

    Weighted average:
    - Faithfulness: 35%
    - Relevance: 35%
    - Precision: 20%
    - Other: 10%
    """
    weights = {
        "faithfulness": 0.35,
        "relevance": 0.35,
        "precision": 0.20,
    }

    total_weight = 0.0
    weighted_sum = 0.0

    for metric, weight in weights.items():
        if metric in metrics:
            weighted_sum += metrics[metric] * weight
            total_weight += weight

    if total_weight == 0:
        return 0.0

    # Add remaining metrics with equal weight
    remaining_weight = 1.0 - total_weight
    other_metrics = {k: v for k, v in metrics.items() if k not in weights}
    if other_metrics:
        avg_other = sum(other_metrics.values()) / len(other_metrics)
        weighted_sum += avg_other * remaining_weight
    else:
        weighted_sum = weighted_sum / total_weight  # Normalize

    return round(min(max(weighted_sum, 0.0), 1.0), 4)


def get_timestamp() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dict by key path."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def build_topic_suggestions(query: str, context: str) -> List[str]:
    """
    Generate follow-up topic suggestions based on query and context.
    Simple keyword-based extraction for when LLM is not available.
    """
    # Extract key terms from query and context
    combined = f"{query} {context}".lower()

    topic_patterns = [
        (r"\b(machine learning|ml)\b", "Advanced Machine Learning Techniques"),
        (r"\b(neural network|deep learning)\b", "Deep Learning Architectures"),
        (r"\b(python)\b", "Python Programming Best Practices"),
        (r"\b(algorithm)\b", "Algorithm Design and Analysis"),
        (r"\b(data structure)\b", "Data Structures and Applications"),
        (r"\b(database|sql)\b", "Database Design and Optimization"),
        (r"\b(api|rest)\b", "RESTful API Development"),
        (r"\b(security|auth)\b", "Cybersecurity Fundamentals"),
        (r"\b(cloud|aws|azure)\b", "Cloud Computing Platforms"),
        (r"\b(statistics|probability)\b", "Statistical Methods in Data Science"),
    ]

    suggestions = []
    for pattern, topic in topic_patterns:
        if re.search(pattern, combined):
            suggestions.append(topic)
        if len(suggestions) >= 3:
            break

    if not suggestions:
        suggestions = [
            "Explore Related Concepts",
            "Practice Problems and Exercises",
            "Advanced Topics in This Domain",
        ]

    return suggestions
