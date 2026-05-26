"""
Main FastAPI Application Entry Point
=====================================
Configures the FastAPI app with:
- CORS middleware
- Request logging middleware
- Rate limiting
- Exception handlers
- All API routers
- Startup/shutdown lifespan events
"""

import time
import traceback
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.utils.logger import get_logger, setup_logging, request_logger
from app.api.routes import chat, documents, quiz, history, analytics, recommendations, health

# Initialize logging
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger("app.main")


# ==============================================================
# LIFESPAN (startup / shutdown)
# ==============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup initialization and graceful shutdown.
    """
    # --- STARTUP ---
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   Debug: {settings.DEBUG}")
    logger.info(f"   OpenAI Model: {settings.OPENAI_MODEL}")
    logger.info("=" * 60)

    # Initialize ChromaDB collection
    try:
        from app.retrieval.vector_store import VectorStore
        vector_store = VectorStore()
        await vector_store.initialize()
        app.state.vector_store = vector_store
        logger.info("✅ ChromaDB vector store initialized")
    except Exception as e:
        logger.error(f"❌ ChromaDB initialization failed: {e}")
        app.state.vector_store = None

    # Initialize memory store
    try:
        from app.memory.conversation_memory import ConversationMemory
        app.state.memory = ConversationMemory()
        logger.info("✅ Conversation memory initialized")
    except Exception as e:
        logger.error(f"❌ Memory initialization failed: {e}")
        app.state.memory = None

    # Initialize analytics store
    try:
        from app.analytics.tracker import AnalyticsTracker
        app.state.analytics = AnalyticsTracker()
        logger.info("✅ Analytics tracker initialized")
    except Exception as e:
        logger.error(f"❌ Analytics initialization failed: {e}")
        app.state.analytics = None

    # Configure LangSmith if enabled
    if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        logger.info(f"✅ LangSmith tracing enabled (project: {settings.LANGCHAIN_PROJECT})")

    logger.info("✅ Application startup complete — ready to serve requests")
    logger.info(f"   Docs: http://{settings.HOST}:{settings.PORT}/docs")

    yield

    # --- SHUTDOWN ---
    logger.info("🛑 Shutting down application...")
    logger.info("✅ Shutdown complete")


# ==============================================================
# APP FACTORY
# ==============================================================

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Returns a production-ready FastAPI instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## AI Multi-Agent Smart Learning Assistant API

A production-grade multi-agent AI system for educational assistance with:
- **Multi-Agent Orchestration** (Supervisor, Retrieval, Generation, Reviewer)
- **Reflection/Self-Correction** workflow
- **Hybrid RAG Pipeline** (BM25 + Vector + Re-ranking)
- **DeepEval Evaluation** (Faithfulness, Relevance, Precision, Hallucination)
- **Security Layer** (Prompt injection detection, content filtering)
- **Conversation Memory** and **Analytics**

### Workflow
```
User Input → Security → Supervisor → Retrieval → Generation
          → Reflection → Correction → Review → Final Response
```
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- MIDDLEWARE ---

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # --- CUSTOM REQUEST LOGGING MIDDLEWARE ---
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Skip health check logging
        if request.url.path not in ("/health", "/ping"):
            request_logger.log_request(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                latency_ms=latency_ms,
                client_ip=request.client.host if request.client else "",
            )

        # Add latency header
        response.headers["X-Process-Time-Ms"] = f"{latency_ms:.1f}"
        return response

    # --- EXCEPTION HANDLERS ---

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        logger.warning(f"Validation error on {request.url.path}: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Request validation failed",
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error_id = f"ERR-{int(time.time())}"
        logger.error(
            f"Unhandled exception [{error_id}] on {request.url.path}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An internal server error occurred",
                "error_id": error_id,
                "detail": str(exc) if settings.DEBUG else "Contact support with error_id",
            },
        )

    # --- ROUTERS ---
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
    app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
    app.include_router(quiz.router, prefix="/api/v1", tags=["Quiz"])
    app.include_router(history.router, prefix="/api/v1", tags=["History"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
    app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])

    # --- ROOT ENDPOINT ---
    @app.get("/", include_in_schema=False)
    async def root() -> Dict[str, Any]:
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create the app instance
app = create_application()


# ==============================================================
# ENTRY POINT
# ==============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS if not settings.DEBUG else 1,
        log_level=settings.LOG_LEVEL.lower(),
    )
