"""
Tests — PostgreSQL pgvector Vector Store

Tests:
1. Fail-fast error if VECTOR_BACKEND=pgvector on non-PostgreSQL engine.
2. (Skipped unless TEST_DATABASE_URL is a PostgreSQL database):
   - Insert chunks with vector embeddings.
   - Idempotent re-insertion (ON CONFLICT update).
   - Filtered similarity search by user_id and document_ids list.
   - Ordering by cosine similarity.
   - Delete by document.
   - Delete by user.
   - Model mismatch guard refusal.
"""

import os
import pytest
from app.core.config import settings
import app.services.vectorstore as vs


def test_pgvector_fails_fast_on_sqlite(monkeypatch):
    """VECTOR_BACKEND=pgvector must fail fast with a clear error on non-PostgreSQL engines."""
    monkeypatch.setattr(settings, "vector_backend", "pgvector")
    from app.db.session import engine

    if engine.dialect.name != "postgresql":
        with pytest.raises(RuntimeError) as exc_info:
            vs.add_chunks(
                ids=["test_1"],
                embeddings=[[0.1] * 384],
                documents=["test content"],
                metadatas=[{"user_id": 1, "document_id": 1}],
            )
        assert "requires PostgreSQL with the vector extension enabled" in str(exc_info.value)

        with pytest.raises(RuntimeError) as exc_info:
            vs.search([0.1] * 384, n_results=1)
        assert "requires PostgreSQL with the vector extension enabled" in str(exc_info.value)

        with pytest.raises(RuntimeError) as exc_info:
            vs.delete_vectors_by_document(1)
        assert "requires PostgreSQL with the vector extension enabled" in str(exc_info.value)

        with pytest.raises(RuntimeError) as exc_info:
            vs.delete_vectors_by_user(1)
        assert "requires PostgreSQL with the vector extension enabled" in str(exc_info.value)


TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.mark.skipif(
    not TEST_DB_URL.startswith("postgresql"),
    reason="Requires PostgreSQL test database in TEST_DATABASE_URL",
)
class TestPgvectorStore:
    @pytest.fixture(autouse=True)
    def setup_pgvector(self, monkeypatch):
        from sqlalchemy import create_engine, text
        from app.db import session as db_session

        orig_engine = db_session.engine
        test_engine = create_engine(TEST_DB_URL)
        db_session.engine = test_engine
        monkeypatch.setattr(settings, "vector_backend", "pgvector")
        monkeypatch.setattr(settings, "embedding_dim", 384)

        with test_engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS chunk_vectors (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    document_id INTEGER NOT NULL,
                    filename TEXT,
                    page INTEGER,
                    chunk_index INTEGER,
                    content TEXT NOT NULL,
                    embedding vector(384) NOT NULL
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vector_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """))
            conn.execute(text("TRUNCATE TABLE chunk_vectors;"))
            conn.execute(text("""
                INSERT INTO vector_meta (key, value)
                VALUES ('embedding_model', :model), ('embedding_dim', '384')
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            """), {"model": settings.embedding_model})

        yield test_engine

        with test_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE chunk_vectors;"))

        test_engine.dispose()
        db_session.engine = orig_engine

    def test_insert_search_and_delete(self):
        # 1. Insert chunks
        dim = 384
        emb_1 = [0.0] * dim
        emb_1[0] = 1.0  # vector [1, 0, 0, ...]
        emb_2 = [0.0] * dim
        emb_2[1] = 1.0  # vector [0, 1, 0, ...]

        vs.add_chunks(
            ids=["doc_1_c_0", "doc_1_c_1"],
            embeddings=[emb_1, emb_2],
            documents=["First chunk about algorithms", "Second chunk about trees"],
            metadatas=[
                {"user_id": 10, "document_id": 1, "filename": "cs.pdf", "page": 1, "chunk_index": 0},
                {"user_id": 10, "document_id": 1, "filename": "cs.pdf", "page": 2, "chunk_index": 1},
            ],
        )

        # 2. Search exact match
        res = vs.search(query_embedding=emb_1, n_results=2, where={"user_id": 10})
        assert len(res["ids"][0]) == 2
        assert res["ids"][0][0] == "doc_1_c_0"
        assert res["distances"][0][0] < 0.001  # Exact match cosine distance ~ 0

        # 3. User isolation in search
        res_other = vs.search(query_embedding=emb_1, n_results=2, where={"user_id": 99})
        assert len(res_other["ids"][0]) == 0

        # 4. Document filter with $in
        res_doc = vs.search(
            query_embedding=emb_1,
            n_results=2,
            where={"$and": [{"user_id": 10}, {"document_id": {"$in": [1]}}]},
        )
        assert len(res_doc["ids"][0]) == 2

        res_wrong_doc = vs.search(
            query_embedding=emb_1,
            n_results=2,
            where={"$and": [{"user_id": 10}, {"document_id": {"$in": [999]}}]},
        )
        assert len(res_wrong_doc["ids"][0]) == 0

        # 5. Idempotent re-insert
        vs.add_chunks(
            ids=["doc_1_c_0"],
            embeddings=[emb_1],
            documents=["Updated first chunk content"],
            metadatas=[{"user_id": 10, "document_id": 1, "filename": "cs.pdf", "page": 1, "chunk_index": 0}],
        )
        res_updated = vs.search(query_embedding=emb_1, n_results=1, where={"user_id": 10})
        assert res_updated["documents"][0][0] == "Updated first chunk content"

        # 6. Delete by document
        vs.delete_vectors_by_document(1)
        res_after_del = vs.search(query_embedding=emb_1, n_results=5, where={"user_id": 10})
        assert len(res_after_del["ids"][0]) == 0

    def test_model_mismatch_guard(self, monkeypatch):
        dim = 384
        emb = [0.1] * dim
        # Artificially change configured embedding model
        monkeypatch.setattr(settings, "embedding_model", "different/model-name")

        with pytest.raises(ValueError) as exc_info:
            vs.add_chunks(
                ids=["doc_1_c_0"],
                embeddings=[emb],
                documents=["test content"],
                metadatas=[{"user_id": 10, "document_id": 1}],
            )
        assert "Embedding model mismatch" in str(exc_info.value)
