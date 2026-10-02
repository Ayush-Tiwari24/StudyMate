"""
StudyMate RAG — Vector Store Abstraction

Supports:
- ChromaDB (local development default)
- PostgreSQL + pgvector (production online stack)

Collection / Table:
- Chroma: 'studymate_chunks'
- Postgres: 'chunk_vectors' with HNSW cosine index
"""

from functools import lru_cache
from typing import Optional

from app.core.config import settings
from app.core.logger import logger


COLLECTION_NAME = "studymate_chunks"


# ── ChromaDB Backend (Lazy Loaded) ───────────────────────────────

@lru_cache(maxsize=1)
def get_chroma_client():
    """Get or create the persistent ChromaDB client (lazily imported)."""
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    logger.info(f"Initializing ChromaDB at: {settings.vector_store_dir}")
    client = chromadb.PersistentClient(
        path=settings.vector_store_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client


def get_collection(validate_model: bool = True):
    """Get or create the Chroma chunks collection and validate model consistency."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "embedding_model": settings.embedding_model,
            "hnsw:space": "cosine",
        },
    )
    if validate_model and collection.metadata:
        stored_model = collection.metadata.get("embedding_model")
        if stored_model and stored_model != settings.embedding_model:
            error_msg = (
                f"Embedding model mismatch! Collection uses '{stored_model}', "
                f"but settings configure '{settings.embedding_model}'. "
                f"Refusing to add vectors until scripts/reindex.py is run."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
    return collection


def _add_chunks_chroma(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    collection = get_collection()
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )
    logger.info(f"Added {len(ids)} vectors to ChromaDB")


def _search_chroma(
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    collection = get_collection()
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def _delete_vectors_chroma(document_id: int) -> None:
    collection = get_collection()
    try:
        collection.delete(where={"document_id": document_id})
        logger.info(f"Deleted vectors from ChromaDB for document_id={document_id}")
    except Exception as e:
        logger.warning(f"Chroma delete error for document {document_id}: {e}")


def _delete_vectors_by_user_chroma(user_id: int) -> None:
    collection = get_collection()
    try:
        collection.delete(where={"user_id": user_id})
        logger.info(f"Deleted vectors from ChromaDB for user_id={user_id}")
    except Exception as e:
        logger.warning(f"Could not delete Chroma vectors by user_id {user_id}: {e}")


# ── PostgreSQL + pgvector Backend ─────────────────────────────────

def _check_pgvector_dialect():
    """Ensure pgvector is running against a PostgreSQL database."""
    from app.db.session import engine
    if engine.dialect.name != "postgresql":
        error_msg = (
            f"VECTOR_BACKEND is set to 'pgvector', but database dialect is '{engine.dialect.name}'. "
            "pgvector requires PostgreSQL with the vector extension enabled. "
            "Please configure a valid PostgreSQL DATABASE_URL or set VECTOR_BACKEND=chroma."
        )
        logger.critical(error_msg)
        raise RuntimeError(error_msg)


def _validate_pgvector_model(conn):
    """Refuse vector insertion if the database vectors were generated with a different model."""
    from sqlalchemy import text
    try:
        res = conn.execute(text("SELECT value FROM vector_meta WHERE key = 'embedding_model'")).scalar()
        if res and res != settings.embedding_model:
            error_msg = (
                f"Embedding model mismatch! Database vectors were generated with '{res}', "
                f"but settings configure '{settings.embedding_model}'. "
                f"Refusing to insert vectors until scripts/reindex.py is run."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
    except Exception as e:
        if "relation \"vector_meta\" does not exist" in str(e) or "no such table" in str(e):
            logger.warning("vector_meta table not found; skipping model check.")
        elif isinstance(e, ValueError):
            raise
        else:
            logger.warning(f"Could not verify vector_meta: {e}")


def _build_where_clause(where: dict | None) -> tuple[str, dict]:
    """
    Translate Chroma-style where dictionary into SQL WHERE clause and parameters.
    Supports user_id, document_id ($in and equality), inside $and.
    """
    if not where:
        return "1=1", {}

    sql_clauses = []
    params = {}
    param_idx = 0

    def parse_condition(cond: dict):
        nonlocal param_idx
        for key, val in cond.items():
            if key == "$and":
                if not isinstance(val, list):
                    raise ValueError("$and condition in where filter must be a list")
                for sub in val:
                    parse_condition(sub)
            elif key == "$or":
                raise ValueError("$or condition is not currently supported in pgvector search")
            elif key in ("user_id", "document_id", "filename", "page", "chunk_index"):
                if isinstance(val, dict):
                    if "$in" in val:
                        in_list = val["$in"]
                        if not isinstance(in_list, (list, tuple, set)):
                            raise ValueError(f"$in value for {key} must be a list or set")
                        if not in_list:
                            sql_clauses.append("1=0")
                        else:
                            p_names = []
                            for item in in_list:
                                p_name = f"p_{key}_{param_idx}"
                                params[p_name] = item
                                p_names.append(f":{p_name}")
                                param_idx += 1
                            sql_clauses.append(f"{key} IN ({', '.join(p_names)})")
                    else:
                        raise ValueError(f"Unsupported operator in where filter for {key}: {list(val.keys())}")
                else:
                    p_name = f"p_{key}_{param_idx}"
                    params[p_name] = val
                    sql_clauses.append(f"{key} = :{p_name}")
                    param_idx += 1
            else:
                raise ValueError(f"Unsupported where filter field: {key}")

    parse_condition(where)
    where_sql = " AND ".join(sql_clauses) if sql_clauses else "1=1"
    return where_sql, params


def _add_chunks_pgvector(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """Insert chunk vectors in batches of 500 using ON CONFLICT DO UPDATE for idempotency."""
    _check_pgvector_dialect()
    from app.db.session import engine
    from sqlalchemy import text

    batch_size = 500
    insert_sql = text("""
        INSERT INTO chunk_vectors (id, user_id, document_id, filename, page, chunk_index, content, embedding)
        VALUES (:id, :user_id, :document_id, :filename, :page, :chunk_index, :content, :embedding)
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            document_id = EXCLUDED.document_id,
            filename = EXCLUDED.filename,
            page = EXCLUDED.page,
            chunk_index = EXCLUDED.chunk_index,
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding
    """)

    with engine.begin() as conn:
        _validate_pgvector_model(conn)

        for i in range(0, len(ids), batch_size):
            batch_params = []
            for j in range(i, min(i + batch_size, len(ids))):
                meta = metadatas[j]
                batch_params.append({
                    "id": ids[j],
                    "user_id": int(meta.get("user_id")),
                    "document_id": int(meta.get("document_id")),
                    "filename": meta.get("filename"),
                    "page": meta.get("page"),
                    "chunk_index": meta.get("chunk_index"),
                    "content": documents[j],
                    "embedding": str(embeddings[j]),
                })
            conn.execute(insert_sql, batch_params)

    logger.info(f"Added {len(ids)} vectors to PostgreSQL (pgvector)")


def _search_pgvector(
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    """Perform cosine distance similarity search with HNSW index in PostgreSQL."""
    _check_pgvector_dialect()
    from app.db.session import engine
    from sqlalchemy import text

    where_sql, params = _build_where_clause(where)
    params["q"] = str(query_embedding)
    params["n"] = n_results
    ef_search = settings.hnsw_ef_search or 40

    query_sql = text(f"""
        SELECT id, content, user_id, document_id, filename, page, chunk_index,
               embedding <=> :q AS distance
        FROM chunk_vectors
        WHERE {where_sql}
        ORDER BY embedding <=> :q
        LIMIT :n
    """)

    with engine.begin() as conn:
        try:
            conn.execute(text(f"SET LOCAL hnsw.ef_search = {int(ef_search)}"))
        except Exception:
            pass  # If HNSW parameter is not supported by standard indexes, continue
        rows = conn.execute(query_sql, params).fetchall()

    ids = [row.id for row in rows]
    documents = [row.content for row in rows]
    metadatas = [
        {
            "user_id": row.user_id,
            "document_id": row.document_id,
            "filename": row.filename,
            "page": row.page,
            "chunk_index": row.chunk_index,
        }
        for row in rows
    ]
    distances = [float(row.distance) for row in rows]

    return {
        "ids": [ids],
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }


def _delete_vectors_pgvector(document_id: int) -> None:
    _check_pgvector_dialect()
    from app.db.session import engine
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM chunk_vectors WHERE document_id = :id"), {"id": document_id})
    logger.info(f"Deleted vectors from PostgreSQL (pgvector) for document_id={document_id}")


def _delete_vectors_by_user_pgvector(user_id: int) -> None:
    _check_pgvector_dialect()
    from app.db.session import engine
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM chunk_vectors WHERE user_id = :id"), {"id": user_id})
    logger.info(f"Deleted vectors from PostgreSQL (pgvector) for user_id={user_id}")


# ── Public API (Backend Agnostic) ─────────────────────────────────

def add_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """Add chunk embeddings to the active vector store."""
    backend = settings.vector_backend.lower().strip()
    if backend == "pgvector":
        _add_chunks_pgvector(ids, embeddings, documents, metadatas)
    else:
        _add_chunks_chroma(ids, embeddings, documents, metadatas)


def search(
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    """Search for similar chunks in the active vector store."""
    backend = settings.vector_backend.lower().strip()
    if backend == "pgvector":
        return _search_pgvector(query_embedding, n_results, where)
    return _search_chroma(query_embedding, n_results, where)


def delete_vectors_by_document(document_id: int) -> None:
    """Delete all vectors belonging to a specific document."""
    backend = settings.vector_backend.lower().strip()
    if backend == "pgvector":
        _delete_vectors_pgvector(document_id)
    else:
        _delete_vectors_chroma(document_id)


def delete_vectors_by_user(user_id: int) -> None:
    """Delete all vectors belonging to a user."""
    backend = settings.vector_backend.lower().strip()
    if backend == "pgvector":
        _delete_vectors_by_user_pgvector(user_id)
    else:
        _delete_vectors_by_user_chroma(user_id)
