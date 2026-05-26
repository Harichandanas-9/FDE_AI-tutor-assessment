# 🎓 AI Multi-Agent Smart Learning Assistant

A **production-grade** multi-agent AI educational platform with hybrid RAG retrieval, reflection/self-correction workflow, DeepEval-powered evaluation, comprehensive security, and a modern React dashboard.

---

## 🏗️ Architecture Overview

```
User Query
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│  Security Layer (Prompt Injection | Sanitization | Content Filter) │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────┐
│   Memory Agent      │  ← Retrieves conversation context
│   (Pre-Generation)  │
└─────────────────────┘
  │
  ▼
┌─────────────────────┐
│  Supervisor Agent   │  ← Routes query to appropriate agent
│  (LangGraph)        │
└─────────────────────┘
  │
  ├──── Quiz Mode ──────→ [ Quiz Agent ] ─────────────┐
  ├──── Recommend ──────→ [ Recommendation Agent ] ───┤
  └──── Chat/Other ─────→ [ Retrieval Agent ]         │
                                │                      │
                          (Hybrid Search:              │
                           BM25 + Vector + RRF)        │
                                │                      │
                          [ Generation Agent ]         │
                                │                      │
                      ┌─────────▼──────────┐           │
                      │   Reflection Loop  │           │
                      │  Critic Agent      │◄──────────┘
                      │  Correction Agent  │
                      └─────────┬──────────┘
                                │
                          [ Reviewer Agent ]
                          (DeepEval Metrics)
                                │
                    ┌───────────▼───────────┐
                    │   Memory Agent        │  ← Stores exchange
                    │   (Post-Generation)   │
                    └───────────────────────┘
                                │
                          Final Response
                  (Answer + Confidence + Sources + Metrics)
```

---

## 🤖 Agents

| Agent | Purpose |
|-------|---------|
| **Supervisor Agent** | Analyzes intent, routes to appropriate agents, manages workflow |
| **Retrieval Agent** | Hybrid BM25 + vector search with RRF re-ranking |
| **Generation Agent** | Produces educational responses grounded in context |
| **Critic Agent** | Reviews answers for hallucinations and quality issues |
| **Correction Agent** | Improves answers based on critic feedback |
| **Reviewer Agent** | Runs DeepEval metrics and generates confidence scores |
| **Quiz Agent** ⭐ | Generates MCQ quizzes from content or topics |
| **Memory Agent** ⭐ | Stores/retrieves conversation history and learning context |
| **Recommendation Agent** ⭐ | Suggests personalized next learning topics and paths |

---

## 🔍 Retrieval Pipeline

```
User Query
  → Embedding Generation (OpenAI text-embedding-3-small)
  → BM25 Sparse Search (keyword matching)
  → Vector Dense Search (ChromaDB semantic similarity)
  → Reciprocal Rank Fusion (RRF) — merges both rankings
  → Top-K Context Selection
  → Pass to Generation Agent
```

**Advanced Features:**
- ✅ Hybrid Search (BM25 + Vector)
- ✅ Reciprocal Rank Fusion (RRF)
- ✅ Metadata filtering
- ✅ Cosine similarity scoring
- ✅ Overlapping text chunking (1000 chars / 200 overlap)

---

## 🛡️ Security Features

- **Prompt Injection Detection**: 25+ regex patterns for injection attacks
- **Input Sanitization**: HTML stripping, unicode normalization, control char removal
- **Harmful Content Filtering**: Violence, illegal activities, adult content detection
- **Output Validation**: Filters AI-generated responses before delivery
- **Tool Permission Control**: Role-based access to different modes
- **Rate Limiting**: Configurable request rate limits

---

## 📊 Evaluation System (DeepEval)

Each response is evaluated on:

| Metric | Description | Threshold |
|--------|-------------|-----------|
| **Faithfulness** | Is the answer grounded in retrieved context? | ≥ 0.70 |
| **Relevance** | Is the answer relevant to the question? | ≥ 0.70 |
| **Precision** | Are the retrieved documents relevant? | ≥ 0.60 |
| **Hallucination** | Does the answer fabricate facts? | ≤ 0.30 |
| **Confidence Score** | Weighted overall quality metric | 0.0 – 1.0 |

> If DeepEval is not configured, the system falls back to heuristic evaluation.

---

## 📁 Project Structure

```
AI tutor assessment/
├── backend/
│   ├── app/
│   │   ├── agents/              # All 9 agent implementations
│   │   │   ├── supervisor_agent.py
│   │   │   ├── retrieval_agent.py
│   │   │   ├── generation_agent.py
│   │   │   ├── critic_agent.py
│   │   │   ├── correction_agent.py
│   │   │   ├── reviewer_agent.py
│   │   │   ├── quiz_agent.py       ⭐ NEW
│   │   │   ├── memory_agent.py     ⭐ NEW
│   │   │   └── recommendation_agent.py ⭐ NEW
│   │   ├── workflows/           # LangGraph orchestration
│   │   │   └── main_workflow.py
│   │   ├── retrieval/           # RAG pipeline
│   │   │   ├── vector_store.py  # ChromaDB
│   │   │   ├── bm25_retriever.py
│   │   │   ├── hybrid_retriever.py  # BM25 + Vector + RRF
│   │   │   └── document_processor.py
│   │   ├── evaluation/          # DeepEval integration
│   │   │   └── evaluator.py
│   │   ├── security/            # Security middleware
│   │   │   ├── input_validator.py
│   │   │   ├── prompt_injection.py
│   │   │   ├── content_filter.py
│   │   │   └── security_middleware.py
│   │   ├── memory/              # Conversation memory
│   │   │   └── conversation_memory.py
│   │   ├── analytics/           # Observability
│   │   │   └── tracker.py
│   │   ├── api/routes/          # FastAPI endpoints
│   │   │   ├── chat.py
│   │   │   ├── documents.py
│   │   │   ├── quiz.py
│   │   │   ├── history.py
│   │   │   ├── analytics.py
│   │   │   ├── recommendations.py
│   │   │   └── health.py
│   │   ├── schemas/             # Pydantic models
│   │   │   └── models.py
│   │   ├── config/              # Settings
│   │   │   └── settings.py
│   │   ├── utils/               # Shared utilities
│   │   │   ├── logger.py
│   │   │   ├── retry.py
│   │   │   └── helpers.py
│   │   └── main.py              # FastAPI app entry point
│   ├── tests/                   # Test suite
│   ├── data/                    # Local data (uploads, vectordb)
│   ├── logs/                    # Application logs
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/               # 6 pages
    │   ├── components/          # Reusable components
    │   ├── services/            # API layer
    │   ├── types/               # TypeScript interfaces
    │   ├── store/               # Global state
    │   └── layouts/             # Layout components
    ├── package.json
    └── vite.config.ts
```

---

## ⚡ Local Setup & Running (No Docker)

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- OpenAI API key

### Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env and set your OPENAI_API_KEY and SECRET_KEY

# 5. Create required data directories
mkdir -p data/uploads data/vectordb logs

# 6. Run the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: **http://localhost:8000**
API docs: **http://localhost:8000/docs**

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

Frontend will be available at: **http://localhost:5173**

---

## 🧪 Running Tests

```bash
cd backend

# Install test dependencies (already in requirements.txt)
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_security.py -v
pytest tests/test_api.py -v
pytest tests/test_retrieval.py -v
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat` | Main chat with full agent workflow |
| `POST` | `/api/v1/chat/stream` | Streaming chat (SSE) |
| `POST` | `/api/v1/documents/upload` | Upload PDF/text for indexing |
| `GET` | `/api/v1/documents` | List indexed documents |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document |
| `POST` | `/api/v1/quiz/generate` | Generate MCQ quiz |
| `GET` | `/api/v1/history` | Get all conversation sessions |
| `GET` | `/api/v1/history/{session_id}` | Get session history |
| `DELETE` | `/api/v1/history/{session_id}` | Clear a session |
| `GET` | `/api/v1/analytics` | Analytics dashboard data |
| `POST` | `/api/v1/recommendations` | Learning recommendations |
| `GET` | `/api/v1/health` | Health check |

---

## 🔧 Configuration (.env)

```bash
# Required
OPENAI_API_KEY=sk-your-key-here
SECRET_KEY=your-secret-key-min-32-chars

# Model configuration
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Evaluation
EVALUATION_THRESHOLD_FAITHFULNESS=0.7
EVALUATION_THRESHOLD_RELEVANCE=0.7

# Agent behavior
MAX_REFLECTION_ITERATIONS=3
RETRIEVAL_TOP_K=5
HYBRID_SEARCH_ALPHA=0.5  # 0=all BM25, 1=all vector

# Optional: LangSmith observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-your-key
LANGCHAIN_PROJECT=ai-learning-assistant
```

---

## 📈 Observability

- **Application logs**: `backend/logs/app.log`
- **Evaluation logs**: `backend/logs/evaluations.jsonl`
- **Analytics data**: `backend/logs/analytics.jsonl`
- **LangSmith**: Optional agent traces at smith.langchain.com

---

## 🛠️ Tech Stack

### Backend
- **Python 3.10+** + **FastAPI** — REST API framework
- **LangGraph** — Multi-agent state machine orchestration
- **LangChain** + **OpenAI GPT-4o** — LLM integration
- **ChromaDB** — Vector database for semantic search
- **BM25 (rank-bm25)** — Sparse keyword retrieval
- **DeepEval** — Response evaluation metrics
- **pypdf + pdfplumber** — PDF text extraction
- **bleach** — Input sanitization
- **structlog + rich** — Structured logging
- **tenacity** — Retry logic

### Frontend
- **React 18** + **TypeScript** — UI framework
- **Vite** — Build tool
- **Tailwind CSS** — Utility-first styling
- **Framer Motion** — Animations
- **Recharts** — Analytics charts
- **Axios** — HTTP client
- **React Router v6** — Navigation
- **Lucide React** — Icons

---

## 📝 Example Usage

### Chat Request
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain the concept of gradient descent in machine learning",
    "mode": "explain",
    "include_evaluation": true
  }'
```

### Upload Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/document.pdf" \
  -F "collection_name=ml-textbooks"
```

### Generate Quiz
```bash
curl -X POST http://localhost:8000/api/v1/quiz/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Neural Networks",
    "num_questions": 5,
    "difficulty": "mixed"
  }'
```

---

## 🔒 Security Notes

- Never commit your `.env` file
- Use a strong `SECRET_KEY` (min 32 characters) in production
- Rate limiting is enabled by default (100 req/min)
- All inputs are sanitized before processing
- All outputs are filtered before delivery

---

*Built with production-style architecture for educational AI assistance.*
