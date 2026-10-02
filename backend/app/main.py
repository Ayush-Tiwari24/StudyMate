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

    # Security check: fail startup in production mode if insecure configurations are detected
    if settings.environment == "production":
        if settings.jwt_secret == "change-me-to-a-random-string" or len(settings.jwt_secret) < 32:
            error_msg = (
                "CRITICAL: JWT_SECRET must be at least 32 characters long and cannot be default in production. "
                "Generate one using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        if settings.database_url.startswith("sqlite"):
            error_msg = (
                "CRITICAL: DATABASE_URL cannot be SQLite in production. "
                "Please configure a production PostgreSQL / Neon connection."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        if settings.storage_backend == "local":
            error_msg = (
                "CRITICAL: STORAGE_BACKEND cannot be 'local' in production. "
                "Use 'db' (recommended, stores PDFs in Neon) or 's3'."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        if settings.vector_backend == "chroma":
            error_msg = (
                "CRITICAL: VECTOR_BACKEND cannot be 'chroma' in production. "
                "Use 'pgvector' with Neon serverless Postgres."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
    elif not settings.debug and settings.jwt_secret == "change-me-to-a-random-string":
        error_msg = (
            "CRITICAL: JWT_SECRET is set to the default insecure placeholder. "
            "In non-debug mode, you must set a secure JWT_SECRET in environment variables."
        )
        logger.critical(error_msg)
        raise RuntimeError(error_msg)

    # Log database & backend setup info
    from app.db.session import log_database_startup_info
    log_database_startup_info()

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

    # Pre-warm embedding model into RAM if enabled so user queries never wait
    if settings.prewarm_model:
        try:
            from app.services.embeddings import get_embedding_model
            get_embedding_model()
            logger.info("Embedding model pre-warmed and ready.")
        except Exception as e:
            logger.warning(f"Could not pre-warm embedding model: {e}")

    # Start background keep-alive task for Neon serverless postgres to eliminate cold starts
    keepalive_task = None
    if not settings.database_url.startswith("sqlite"):
        async def keep_neon_alive():
            from sqlalchemy import text
            from app.db.session import engine
            while True:
                try:
                    await asyncio.sleep(180)  # Ping every 3 mins to keep Neon compute & pool warm
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1;"))
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        keepalive_task = asyncio.create_task(keep_neon_alive())
        logger.info("Neon database keep-alive background task started.")

    yield

    # ── Shutdown ──
    if keepalive_task:
        keepalive_task.cancel()
    logger.info("Shutting down...")


# ── App Instance ─────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="Ask academic questions over your study PDFs using RAG.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Rate Limiting (Proxy and User Aware) ──────────────────────────
from fastapi import Request


def get_rate_limit_key(request: Request) -> str:
    """
    Extract rate limit identifier:
    1. Authenticated user ID if present on request state
    2. Client IP from X-Forwarded-For (first IP behind reverse proxy)
    3. Direct client host
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return f"ip:{client_ip}"

    if request.client and request.client.host:
        return f"ip:{request.client.host}"

    return "ip:127.0.0.1"


limiter = Limiter(key_func=get_rate_limit_key, default_limits=[settings.rate_limit])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ── CORS ─────────────────────────────────────────────────────────
configured_origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
origins = list(set(configured_origins + [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=settings.frontend_origin_regex if settings.frontend_origin_regex else None,
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


# ── Health & Readiness Probes ────────────────────────────────────
@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint with component status (no secrets)."""
    db_status = "ok"
    try:
        from app.db.session import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
    except Exception as e:
        logger.error(f"Health check DB probe error: {e}")
        db_status = "error"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "database": db_status,
        "vector_backend": settings.vector_backend,
        "storage_backend": settings.storage_backend,
        "llm_provider": settings.llm_provider,
    }


@app.get("/api/health/ready", tags=["Health"])
def readiness_check():
    """Instant readiness probe so Render health check never times out (>5s) and restarts the instance."""
    return {"status": "ready"}
