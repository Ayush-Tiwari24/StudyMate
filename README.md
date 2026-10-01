# 📚 StudyMate RAG — Academic Question Answering System

> Upload your study PDFs. Ask questions. Get cited answers.

StudyMate RAG is a production-hardened web application where students upload study materials (textbooks, lecture notes, research papers) and chat with them using Retrieval-Augmented Generation. Every answer is **grounded in the uploaded documents** with **page-level citations** and full user data isolation.

---

## ✨ Features

- 📄 **PDF Ingestion & OCR Fallback** — PyMuPDF high-speed parsing with automated RapidOCR fallback for scanned pages.
- 💬 **Grounded Chat with Documents** — Conversational Q&A grounded strictly in uploaded course material.
- 📖 **Page-Level Citations** — Clickable citations `[1] [2]` with source text snippets, page numbers, and inspection views.
- 🔄 **Query Rewriting & MMR Search** — Multi-turn conversation resolution and Maximal Marginal Relevance to eliminate redundant passages.
- ⚡ **Real-Time Streaming** — Server-Sent Events (SSE) streaming with low-latency token delivery and per-request LLM caching.
- 🔐 **Multi-Tenant Security** — Complete database, vector, and file isolation per user; JWT refresh token rotation with single-use revocation.
- ⚙️ **Customizable Preferences** — Real-time configuration of top-k retrieval depth, reading themes (Light, Night, System), font sizing, and LLM providers (Groq, OpenAI, Ollama).
- 📦 **Multi-Tier Storage** — Decoupled storage backends (Local Disk or AWS S3/MinIO) and vector stores (ChromaDB or pgvector).

---

## 🏛️ Storage Architecture (Three Tiers)

StudyMate AI employs a 3-tier storage architecture separating relational data, high-dimensional vectors, and raw document objects:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        StudyMate Storage Tiers                         │
├─────────────────────┬───────────────────────┬──────────────────────────┤
│ 1. Relational Tier  │ 2. Vector Store Tier  │ 3. Object / File Storage │
│ (PostgreSQL/SQLite) │ (ChromaDB / pgvector) │ (AWS S3 / Local Disk)    │
├─────────────────────┼───────────────────────┼──────────────────────────┤
│ - Users & Settings  │ - 384-dim Embeddings  │ - Raw uploaded PDFs      │
│ - Document metadata │ - Cosine HNSW Index   │ - User-scoped keys:      │
│ - Chunks text & idx │ - Strict metadata     │   {user_id}/{hash}_{pdf} │
│ - Chats & Messages  │   filtering:          │                          │
│ - Message Sources   │   user_id & doc_id    │                          │
│ - Refresh Tokens    │                       │                          │
│ - User Feedback     │                       │                          │
└─────────────────────┴───────────────────────┴──────────────────────────┘
```

See [docs/er_diagram.md](docs/er_diagram.md) for the complete Entity Relationship diagram and model lifecycle specifications.

---

## 🚀 Quick Start

### 1. Local Development with SQLite (Zero Config)

The project runs out-of-the-box with SQLite and local disk storage:

```bash
# Clone and enter directory
cd BookWorm.ai

# Copy environment template
cp .env.example .env

# Backend setup
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux / macOS

pip install -r requirements.txt

# Run migrations (or let auto_create_tables handle dev)
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000
```

In a separate terminal, launch the frontend:

```bash
cd frontend
npm install
npm run dev
```

- Web UI: http://localhost:5173
- Swagger API Docs: http://localhost:8000/docs

---

### 2. Production Setup with PostgreSQL & Docker Compose

Deploy the complete stack (PostgreSQL 16, FastAPI backend with pre-cached embeddings, and Nginx-powered frontend):

```bash
# 1. Configure production environment
cp .env.example .env
# Edit .env: Set a secure JWT_SECRET and add your GROQ_API_KEY or OPENAI_API_KEY

# 2. Start services in background
docker-compose up -d --build

# 3. Check logs
docker-compose logs -f backend
```

- Frontend & API Reverse Proxy: http://localhost (port 80)
- Backend Direct: http://localhost:8000
- PostgreSQL: `localhost:5432` (`studymate`)

---

## 🗄️ Database Migrations (Alembic)

Alembic manages schema evolution. Run all migration commands inside the `backend/` directory:

```bash
cd backend

# Create a new automatic schema migration from models
alembic revision --autogenerate -m "add new column or table"

# Apply pending migrations to the latest revision
alembic upgrade head

# Roll back the previous migration step
alembic downgrade -1

# Roll back all migrations to clean base
alembic downgrade base

# Verify database schema is in sync with models
alembic check
```

---

## 🛠️ Operational Runbooks

### 1. Vector Store Reindexing (`scripts/reindex.py`)
If you switch embedding models or need to re-populate the vector database from relational SQL truth:

```bash
cd backend
python scripts/reindex.py
```
*Queries all chunks from the SQL database, re-computes embeddings, and rebuilds the Chroma collection.*

### 2. Orphan Cleanup (`scripts/cleanup_orphans.py`)
Purges files from disk/S3 that have no corresponding row in `documents`, and removes vectors from Chroma that have no corresponding row in `chunks`:

```bash
cd backend
python scripts/cleanup_orphans.py
```

### 3. Backup Strategy
- **Relational Metadata**:
  ```bash
  docker exec -t studymate-postgres pg_dump -U postgres studymate > backup_$(date +%F).sql
  ```
- **Raw PDFs**: Mirror the S3 bucket (`aws s3 sync s3://bucket ./backup/pdfs`) or snapshot the `app_data` named Docker volume.
- **ChromaDB**: Snapshot the `/app/data/vector_store` directory or recover at any time by running `scripts/reindex.py`.

---

## 🛡️ Production Deployment Checklist

Before taking the application live, ensure:

- [ ] **`JWT_SECRET`**: Set to a cryptographically secure random string (minimum 32 characters, e.g., `python -c "import secrets; print(secrets.token_urlsafe(32))"`). The application will fail startup in production (`DEBUG=false`) if the default placeholder is detected.
- [ ] **`DATABASE_URL`**: Pointed to a PostgreSQL cluster (`postgresql+psycopg2://user:pass@host:5432/dbname`).
- [ ] **`AUTO_CREATE_TABLES`**: Set to `false` in production.
- [ ] **Migrations**: Execute `alembic upgrade head` before serving user traffic.
- [ ] **Embedding Pre-download**: Verify the Docker image was built with embedding models pre-cached so cold-start requests do not time out.
- [ ] **CORS `FRONTEND_ORIGIN`**: Configured to your production domain (e.g. `https://studymate.yourdomain.com`).
- [ ] **Storage Backend**: Use `STORAGE_BACKEND=s3` with AWS S3 / MinIO / Cloudflare R2 for multi-node deployments.
- [ ] **Nginx Reverse Proxy**: Verify `proxy_buffering off;` and `proxy_read_timeout 300s;` are configured on the `/api/` location block to support SSE streaming.

---

## 🧪 Running the Test Suite

Execute the comprehensive test suite covering foreign keys, cascades, migrations, JWT rotation, user isolation, and multi-store deletion:

```bash
cd backend
pytest tests/ -v
```

All 42 test cases execute against isolated SQLite test databases and persistent Chroma test collections.

---

## 📝 License

Distributed under the MIT License. Built for academic research and collaborative study.
