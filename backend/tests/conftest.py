import shutil
import tempfile
from pathlib import Path
import pytest

from app.core.config import settings
from app.services.vectorstore import get_chroma_client


@pytest.fixture(scope="session", autouse=True)
def isolate_test_environment():
    """
    Ensure all tests run with:
     - An in-memory/temp SQLite database (not the live Neon DB in .env)
     - Isolated ChromaDB vector store directory
     - Local file storage (not db/s3)
     - Chroma vector backend (not pgvector, which requires live Postgres)

    Tests that need live Postgres should supply their own TEST_DATABASE_URL
    override (see test_pgvector_store.py and test_neon_connection.py).
    """

    temp_dir = Path(tempfile.mkdtemp(prefix="studymate_test_"))
    test_raw_pdfs = temp_dir / "raw_pdfs"
    test_vector_store = temp_dir / "vector_store"
    test_db_path = temp_dir / "test.db"
    test_raw_pdfs.mkdir(parents=True, exist_ok=True)
    test_vector_store.mkdir(parents=True, exist_ok=True)

    # Override settings to isolate from live Neon / production
    orig_upload_dir = settings.upload_dir
    orig_vector_store_dir = settings.vector_store_dir
    orig_database_url = settings.database_url
    orig_migration_database_url = settings.migration_database_url
    orig_vector_backend = settings.vector_backend
    orig_storage_backend = settings.storage_backend
    orig_auto_create_tables = settings.auto_create_tables

    sqlite_url = f"sqlite:///{test_db_path}"
    settings.upload_dir = str(test_raw_pdfs)
    settings.vector_store_dir = str(test_vector_store)
    settings.database_url = sqlite_url
    settings.migration_database_url = ""
    settings.vector_backend = "chroma"
    settings.storage_backend = "local"
    settings.auto_create_tables = True

    get_chroma_client.cache_clear()

    yield

    # Restore all original settings
    settings.upload_dir = orig_upload_dir
    settings.vector_store_dir = orig_vector_store_dir
    settings.database_url = orig_database_url
    settings.migration_database_url = orig_migration_database_url
    settings.vector_backend = orig_vector_backend
    settings.storage_backend = orig_storage_backend
    settings.auto_create_tables = orig_auto_create_tables

    get_chroma_client.cache_clear()
    shutil.rmtree(temp_dir, ignore_errors=True)
