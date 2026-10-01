"""
StudyMate RAG — FastAPI Application

Entry point for the backend. Registers all routers,
configures CORS, creates tables on startup, and serves a health check.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.db.base import Base
from app.db.session import engine

# Import all models so Base.metadata is populated
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # ── Startup ──
    logger.info(f"Starting {settings.app_name}...")

    # Create tables if enabled (dev convenience; disabled in production where Alembic runs)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created / verified via Base.metadata.create_all.")
    else:
        logger.info("Skipping create_all (AUTO_CREATE_TABLES=False); relying on Alembic migrations.")

    # Ensure data directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.vector_store_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Data directories ready.")

    # Re-queue any documents stuck in "processing" from a previous crash
    import asyncio
    from app.db.session import SessionLocal
    from app.models.document import Document
    from app.services.ingestion.pipeline import run_ingestion_pipeline
    db = SessionLocal()
    stuck_ids = []
    try:
        stuck = db.query(Document).filter(Document.status == "processing").all()
        for doc in stuck:
            doc.status = "uploaded"
            doc.progress = 0
            stuck_ids.append(doc.id)
            logger.warning(f"Reset stuck document: id={doc.id} filename={doc.filename}")
        db.commit()
    finally:
        db.close()

    for doc_id in stuck_ids:
        asyncio.create_task(asyncio.to_thread(run_ingestion_pipeline, doc_id))
        logger.info(f"Re-queued ingestion for document id={doc_id}")

    # Pre-warm embedding model into RAM so user queries never wait
    try:
        from app.services.embeddings import get_embedding_model
        get_embedding_model()
        logger.info("Embedding model pre-warmed and ready.")
    except Exception as e:
        logger.warning(f"Could not pre-warm embedding model: {e}")

    yield

    # ── Shutdown ──
    logger.info("Shutting down...")


# ── App Instance ─────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="Ask academic questions over your study PDFs using RAG.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Rate Limiting ────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ── CORS ─────────────────────────────────────────────────────────
origins = list(set([
    settings.frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ─────────────────────────────────────────────
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.history import router as history_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.settings import router as settings_router

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(feedback_router)
app.include_router(settings_router)


# ── Health Check ─────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint — no auth required."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "llm_provider": settings.llm_provider,
    }
