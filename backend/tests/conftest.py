import shutil
import tempfile
from pathlib import Path
import pytest

from app.core.config import settings
from app.services.vectorstore import get_chroma_client

@pytest.fixture(scope="session", autouse=True)
def isolate_test_environment():
    """
    Ensure all tests run with isolated storage and ChromaDB directories
    so they never overwrite or delete dev/production user data in ./data.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="studymate_test_"))
    test_raw_pdfs = temp_dir / "raw_pdfs"
    test_vector_store = temp_dir / "vector_store"
    test_raw_pdfs.mkdir(parents=True, exist_ok=True)
    test_vector_store.mkdir(parents=True, exist_ok=True)

    orig_upload_dir = settings.upload_dir
    orig_vector_store_dir = settings.vector_store_dir

    settings.upload_dir = str(test_raw_pdfs)
    settings.vector_store_dir = str(test_vector_store)
    get_chroma_client.cache_clear()

    yield

    # Restore original settings and cleanup
    settings.upload_dir = orig_upload_dir
    settings.vector_store_dir = orig_vector_store_dir
    get_chroma_client.cache_clear()
    shutil.rmtree(temp_dir, ignore_errors=True)
