# StudyMate AI — Data Locations & Storage Architecture

This document details where every piece of application data lives in both **Local Development** and **Production (Neon Serverless Postgres)** environments, including storage sizing formulas, quotas, and database safety caps.

---

## 1. Data Store Comparison

| Data Category | Local Development | Production (Unified Neon) |
|---|---|---|
| **Users & Preferences** | SQLite (`./data/app.db`) | Neon Postgres `users` table |
| **Authentication & Refresh Tokens** | SQLite (`./data/app.db`) | Neon Postgres `refresh_tokens` table |
| **Chats & Conversation History** | SQLite (`./data/app.db`) | Neon Postgres `chats`, `messages` |
| **Citations & Message Sources** | SQLite (`./data/app.db`) | Neon Postgres `sources` table |
| **User Feedback** | SQLite (`./data/app.db`) | Neon Postgres `feedback` table |
| **Document Metadata & Chunks** | SQLite (`./data/app.db`) | Neon Postgres `documents`, `chunks` |
| **Vector Embeddings & HNSW Index** | ChromaDB (`./data/vector_store`) | Neon Postgres `chunk_vectors` (`pgvector`) |
| **Uploaded PDF Files** | Local Disk (`./data/raw_pdfs/`) | Neon Postgres `stored_files` table (`bytea`) |

---

## 2. Storage Sizing & Multiplier Analysis

When a user uploads a PDF file into StudyMate, the database stores more than just the raw bytes:

1. **Raw PDF Blob (`stored_files.data`)**: Exactly 1.0x the file size.
2. **Extracted Text Chunks (`chunks.content`)**: Chunks of ~900 characters with 150-char overlap equate to ~0.12–0.15x the raw file size in UTF-8 text.
3. **Vectors (`chunk_vectors.embedding`)**: Each chunk generates a 384-dimensional vector (`vector(384)`). In PostgreSQL, 384 float4 values consume ~1.536 KB per chunk. For an average 10 MB lecture slide PDF with ~200 chunks, vector data consumes ~300–400 KB (~0.04x).
4. **HNSW Index Overhead**: The HNSW graph structure with `m=16, ef_construction=64` adds ~0.10x–0.15x index overhead on disk.
5. **Relational Metadata & Indexes**: Primary keys, foreign keys, timestamps, and B-tree indexes add ~0.05x.

### Total Multiplier: **~1.35x to 1.45x**
Every 10 MB of uploaded PDF consumes approximately **13.5 MB to 14.5 MB** of Neon disk storage.

---

## 3. Storage Limits & Protection Mechanisms

Neon's Free Tier includes **0.5 GB (512 MB)** of storage shared across the entire database project. Exceeding this limit causes Neon to suspend the database, resulting in total application downtime. StudyMate implements a multi-tier defense:

### A. Per-File Limit (`MAX_UPLOAD_MB = 10`)
- **Default**: 10 MB
- **Rationale**: High-yield lecture notes, problem sets, and textbook chapters easily fit within 10 MB while preventing oversized scanned books from overwhelming memory or storage.
- **Error**: `HTTP 413 — File exceeds maximum size of 10 MB.`

### B. Per-User Quota (`USER_STORAGE_QUOTA_MB = 50`)
- **Default**: 50 MB
- **Configured via**: `USER_STORAGE_QUOTA_MB` env var
- **Rationale**: Allows an individual student to store 5–10 chapters of course notes.
- **UI Display**: Shown on both Dashboard and Settings page as `"12 MB of 50 MB used"` with an accessible visual progress bar.
- **Warning Threshold**: Turns into an amber warning when usage reaches **>= 80%**.
- **Block Threshold**: Blocks uploads when usage reaches **100%**.
- **Error**: `HTTP 413 — You've used all your storage. Delete a document to add more.`

### C. Global Database Soft Cap (`GLOBAL_STORAGE_CAP_MB = 400`)
- **Default**: 400 MB
- **Configured via**: `GLOBAL_STORAGE_CAP_MB` env var
- **Mechanism**: Evaluated prior to accepting any new upload using `pg_database_size(current_database())` on PostgreSQL.
- **Safety Buffer**: Leaves **~112 MB** of safe headroom for WAL, indexes, chat messages, and citation logs.
- **Error**: `HTTP 413 — Uploads are paused because storage is full.`

---

## 4. Connection Pooling Architecture

Neon serverless Postgres automatically scales compute to zero after ~5 minutes of inactivity.

- **FastAPI Web Service (`DATABASE_URL`)**:
  - Connects via Neon's pooled endpoint (`-pooler` hostname, PgBouncer in transaction mode).
  - Pool size is kept small (`db_pool_size=3, max_overflow=2, pool_recycle=240`) to conserve connection slots.
  - Automatic retry logic (3 attempts with exponential backoff: 0.5s, 1s, 2s) seamlessly handles the 1–3s cold-start wakeup window when Neon compute spins up.
  - Vector search sets `hnsw.ef_search` inside transaction blocks (`with engine.begin():`) to ensure parameter isolation in PgBouncer.
- **Alembic Migrations & Backups (`MIGRATION_DATABASE_URL`)**:
  - Connects directly to Neon's non-pooled endpoint (direct port 5432, without `-pooler`).
  - Required for advisory locks, schema DDL, and `pg_dump` operations.
