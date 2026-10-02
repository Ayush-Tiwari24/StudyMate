"""
StudyMate RAG — Application Settings

Loads configuration from environment variables / .env file.
All RAG tuning parameters are centralized here.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application-wide settings loaded from .env or environment variables."""

    # ── Application ──────────────────────────────────────────────
    app_name: str = "StudyMate RAG"
    debug: bool = False
    environment: str = "development"  # "development" | "production" | "test"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/app.db"
    migration_database_url: str = ""  # Direct connection URL for Alembic when using Supabase pooler
    auto_create_tables: bool = True
    run_migrations_on_start: bool = True
    db_pool_size: int = 3
    db_max_overflow: int = 2
    db_pool_recycle: int = 240
    db_pool_pre_ping: bool = True

    # ── File Storage ─────────────────────────────────────────────
    storage_backend: str = "local"  # "local" | "s3" | "db"
    upload_dir: str = "./data/raw_pdfs"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    max_upload_mb: int = 10
    user_storage_quota_mb: int = 50
    global_storage_cap_mb: int = 400

    # ── Vector Store ─────────────────────────────────────────────
    vector_backend: str = "chroma"  # "chroma" | "pgvector"
    vector_store_dir: str = "./data/vector_store"
    embedding_dim: int = 384
    hnsw_ef_search: int = 40

    # ── JWT Auth ─────────────────────────────────────────────────
    jwt_secret: str = "change-me-to-a-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    # ── CORS ─────────────────────────────────────────────────────
    frontend_origin: str = "http://localhost:5173"
    frontend_origin_regex: str = ""  # Optional regex, e.g. ^https://studymate-.*\.vercel\.app$

    # ── LLM Provider ────────────────────────────────────────────
    llm_provider: str = "groq"  # "groq" | "openai" | "ollama"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # ── Embeddings & Computation ─────────────────────────────────
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    prewarm_model: bool = True
    torch_num_threads: int = 2

    # ── Chunking ─────────────────────────────────────────────────
    chunk_size: int = 900
    chunk_overlap: int = 150

    # ── Retrieval ────────────────────────────────────────────────
    top_k: int = 5
    fetch_k: int = 10
    use_mmr: bool = True
    score_threshold: float = 0.05

    # ── Reranker ─────────────────────────────────────────────────
    rerank_enabled: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── LLM Generation ───────────────────────────────────────────
    llm_temperature: float = 0.1
    llm_max_tokens: int = 800

    # ── Chat History ─────────────────────────────────────────────
    history_window: int = 4

    # ── Rate Limiting ────────────────────────────────────────────
    rate_limit: str = "30/minute"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def user_storage_quota_bytes(self) -> int:
        return self.user_storage_quota_mb * 1024 * 1024

    @property
    def global_storage_cap_bytes(self) -> int:
        return self.global_storage_cap_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        if not p.is_absolute():
            backend_dir = Path(__file__).resolve().parent.parent.parent
            p = (backend_dir / p).resolve()
        return p

    @property
    def vector_store_path(self) -> Path:
        p = Path(self.vector_store_dir)
        if not p.is_absolute():
            backend_dir = Path(__file__).resolve().parent.parent.parent
            p = (backend_dir / p).resolve()
        return p

    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).resolve().parent.parent.parent / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Singleton instance — import this throughout the app
settings = Settings()
