"""
Local Development Server Entry Point
======================================
Run this file to start the backend locally in VS Code.

Usage:
    python run.py
    # or
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
from pathlib import Path

# Ensure project root is on the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Check .env exists
if not Path(".env").exists():
    print("⚠️  WARNING: .env file not found!")
    print("   Please copy .env.example to .env and fill in your OPENAI_API_KEY")
    print("   Running with defaults (may fail without API key)")

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"🚀 {settings.APP_NAME}")
    print(f"   Version: {settings.APP_VERSION}")
    print(f"   Environment: {settings.APP_ENV}")
    print(f"   API Docs: http://localhost:{settings.PORT}/docs")
    print(f"   Health: http://localhost:{settings.PORT}/api/v1/health")
    print(f"{'='*60}\n")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,  # Auto-reload on code changes
        log_level=settings.LOG_LEVEL.lower(),
    )
