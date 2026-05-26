"""
Pydantic Schemas / Data Models
================================
All request/response models used by the API and agents.
"""

from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


# ==============================================================
# BASE MODELS
# ==============================================================

class BaseResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: str = "OK"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ==============================================================
# CHAT / QUERY MODELS
# ==============================================================

class ChatRequest(BaseModel):
    """Incoming chat query from the user."""
    query: str = Field(..., min_length=1, max_length=5000, description="User's question")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation continuity")
    mode: Literal["chat", "quiz", "summarize", "explain", "recommend"] = Field(
        default="chat", description="Interaction mode"
    )
    include_evaluation: bool = Field(default=True, description="Include evaluation metrics in response")
    stream: bool = Field(default=False, description="Enable streaming response")
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @validator("query")
    def strip_query(cls, v):
        return v.strip()


class SourceReference(BaseModel):
    """A source document reference."""
    source: str
    page: Optional[str] = ""
    type: str = "document"
    excerpt: Optional[str] = ""
    relevance_score: Optional[float] = None


class EvaluationMetrics(BaseModel):
    """Response evaluation metrics from DeepEval."""
    faithfulness: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    precision: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_score: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    passed: bool = False
    evaluation_time_ms: Optional[float] = None


class AgentTrace(BaseModel):
    """A single agent activity trace entry."""
    timestamp: str
    agent: str
    event: str
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None


class ChatResponse(BaseModel):
    """Full response returned to the user."""
    session_id: str
    query: str
    answer: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    sources: List[SourceReference] = []
    evaluation: Optional[EvaluationMetrics] = None
    agent_traces: List[AgentTrace] = []
    follow_up_topics: List[str] = []
    mode: str = "chat"
    reflection_iterations: int = 0
    total_latency_ms: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ==============================================================
# PDF / DOCUMENT MODELS
# ==============================================================

class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    document_id: str
    filename: str
    file_size_bytes: int
    num_chunks: int
    collection_name: str
    message: str = "Document processed and indexed successfully"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class DocumentListItem(BaseModel):
    """Summary of an indexed document."""
    document_id: str
    filename: str
    file_type: str
    num_chunks: int
    indexed_at: str
    file_size_bytes: Optional[int] = None


class DocumentListResponse(BaseResponse):
    """List of all indexed documents."""
    documents: List[DocumentListItem] = []
    total: int = 0


# ==============================================================
# QUIZ MODELS
# ==============================================================

class QuizQuestion(BaseModel):
    """A single quiz question with multiple choice answers."""
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    options: List[str] = Field(..., min_items=2, max_items=5)
    correct_answer: str
    explanation: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    topic: Optional[str] = None


class QuizRequest(BaseModel):
    """Request to generate a quiz."""
    topic: Optional[str] = Field(default=None, description="Topic for quiz generation")
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    session_id: Optional[str] = None


class QuizResponse(BaseResponse):
    """Generated quiz."""
    quiz_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    topic: str
    questions: List[QuizQuestion]
    total_questions: int
    estimated_time_minutes: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ==============================================================
# CONVERSATION HISTORY MODELS
# ==============================================================

class ConversationMessage(BaseModel):
    """A single message in conversation history."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: Literal["user", "assistant"] = "user"
    content: str
    timestamp: str
    confidence_score: Optional[float] = None
    sources: List[SourceReference] = []


class ConversationSession(BaseModel):
    """A complete conversation session."""
    session_id: str
    messages: List[ConversationMessage] = []
    created_at: str
    last_active: str
    total_messages: int = 0


class ConversationHistoryResponse(BaseResponse):
    """Response containing conversation history."""
    sessions: List[ConversationSession] = []
    total_sessions: int = 0


# ==============================================================
# ANALYTICS MODELS
# ==============================================================

class AnalyticsMetric(BaseModel):
    """A single analytics data point."""
    label: str
    value: float
    unit: Optional[str] = None
    change_pct: Optional[float] = None


class EvaluationTrend(BaseModel):
    """Evaluation metric trend over time."""
    date: str
    faithfulness: float
    relevance: float
    precision: float
    overall: float


class AgentPerformance(BaseModel):
    """Per-agent performance statistics."""
    agent_name: str
    total_calls: int
    avg_latency_ms: float
    error_rate: float
    success_rate: float


class AnalyticsDashboardResponse(BaseResponse):
    """Full analytics dashboard data."""
    total_queries: int = 0
    avg_confidence_score: float = 0.0
    avg_latency_ms: float = 0.0
    total_documents: int = 0
    total_sessions: int = 0
    evaluation_pass_rate: float = 0.0
    evaluation_trends: List[EvaluationTrend] = []
    agent_performance: List[AgentPerformance] = []
    top_topics: List[Dict[str, Any]] = []
    daily_query_counts: List[Dict[str, Any]] = []


# ==============================================================
# RECOMMENDATION MODELS
# ==============================================================

class LearningTopic(BaseModel):
    """A recommended learning topic."""
    topic: str
    description: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_time: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    tags: List[str] = []


class RecommendationRequest(BaseModel):
    """Request for learning recommendations."""
    session_id: Optional[str] = None
    current_topic: Optional[str] = None
    skill_level: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    num_recommendations: int = Field(default=5, ge=1, le=10)


class RecommendationResponse(BaseResponse):
    """Recommended learning topics."""
    recommendations: List[LearningTopic] = []
    based_on: str = ""


# ==============================================================
# AGENT STATE MODEL (Internal - used by LangGraph)
# ==============================================================

class AgentState(BaseModel):
    """
    Shared state object passed between agents in the LangGraph workflow.
    This is the central state machine data structure.
    """
    # Input
    query: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: str = "chat"

    # Security
    is_safe: bool = True
    security_message: Optional[str] = None

    # Retrieval
    retrieved_documents: List[Dict[str, Any]] = []
    retrieval_scores: List[float] = []

    # Generation
    generated_answer: str = ""
    draft_answer: str = ""

    # Reflection
    reflection_needed: bool = False
    reflection_feedback: str = ""
    reflection_iterations: int = 0
    hallucination_detected: bool = False

    # Evaluation
    evaluation_metrics: Dict[str, float] = {}
    confidence_score: float = 0.0
    evaluation_passed: bool = False

    # Output
    final_answer: str = ""
    sources: List[Dict[str, Any]] = []
    follow_up_topics: List[str] = []

    # Traces
    agent_traces: List[Dict[str, Any]] = []

    # Metadata
    total_tokens: int = 0
    error: Optional[str] = None
    completed: bool = False

    class Config:
        arbitrary_types_allowed = True
