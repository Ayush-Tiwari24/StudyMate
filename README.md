# 📚 StudyMate AI — Academic Question Answering System

> Upload your study PDFs. Ask questions. Get cited answers.

StudyMate AI is a production-hardened web application where students upload study materials (textbooks, lecture notes, research papers) and chat with them using Retrieval-Augmented Generation. Every answer is **grounded in the uploaded documents** with **page-level citations** and full user data isolation.

---

## 🏛️ System Architecture

StudyMate AI supports dual operating modes:
1. **Local Development**: Runs out of the box with zero external cloud dependencies using SQLite, ChromaDB, and local file storage.
2. **Online Cloud Stack**: Completely stateless production deployment with **Neon serverless Postgres as the sole data store** (zero data stored on the application server disk):
   - **Frontend**: [Vercel](https://vercel.com) (React + Vite static SPA).
   - **Backend**: [Render](https://render.com) (FastAPI Docker web service on Standard 2 GB RAM plan in Singapore).
   - **Unified Data Store**: [Neon Serverless Postgres](https://neon.tech) in `ap-southeast-1` (Singapore):
     - Relational data (users, refresh tokens, chats, messages, sources, feedback, settings).
     - Vector embeddings via `pgvector` (`chunk_vectors` table with HNSW cosine index).
     - Uploaded PDF files via `stored_files` table (`bytea` / LargeBinary, streaming in chunks).
   - **LLM**: [Groq Cloud](https://groq.com) (`openai/gpt-oss-120b` primary with `openai/gpt-oss-20b` fallback).

For architectural diagrams and database entity relationships, see:
- [docs/architecture.md](docs/architecture.md) — Architecture diagrams and request data flows.
- [docs/er_diagram.md](docs/er_diagram.md) — Relational schema, cascade rules, and indexes.
- [docs/data-locations.md](docs/data-locations.md) — Storage inventory, multiplier breakdown (~1.4x), and quota limits.

---

## 🚀 Step-by-Step Online Cloud Deployment

### Step 1: Provision Neon Postgres (Region: `ap-southeast-1` Singapore)

> **Why Singapore Pairing?** Both Neon (`ap-southeast-1`) and Render (`singapore`) are co-located in Singapore. This minimizes database round-trip latency, which is critical because every RAG query executes multiple database operations (user verification, vector similarity search, chunk retrieval, message logging, and PDF streaming).

1. Create a free account and project on [Neon](https://console.neon.tech).
   - **Name**: `studymate-prod`
   - **Region**: Select `Asia Pacific (Singapore) - ap-southeast-1`.
   - **Postgres Version**: 16 or 17 (recommended).
2. **Get Connection Strings from Neon Dashboard**:
   - Neon provides two connection strings:
     - **Pooled connection string (Port 5432 with `-pooler` in host)**: Used by the running FastAPI application for `DATABASE_URL`. This uses PgBouncer in transaction mode to efficiently manage connections.
     - **Direct connection string (Port 5432 without `-pooler`)**: Used for Alembic migrations and database backups (`MIGRATION_DATABASE_URL`).
   - Format:
     ```env
     # Pooled connection (for running app)
     DATABASE_URL=postgresql+psycopg2://<user>:<password>@ep-example-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

     # Direct connection (for migrations & backup scripts)
     MIGRATION_DATABASE_URL=postgresql+psycopg2://<user>:<password>@ep-example.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
     ```
3. **Run Migrations to Neon**:
   - From your local terminal or during Render deployment:
     ```bash
     cd backend
     MIGRATION_DATABASE_URL="postgresql+psycopg2://<user>:<password>@ep-example.ap-southeast-1.aws.neon.tech/neondb?sslmode=require" alembic upgrade head
     ```
   - This automatically enables the `pgvector` extension and creates all tables: `users`, `refresh_tokens`, `documents`, `chunks`, `chunk_vectors`, `chats`, `messages`, `sources`, `feedback`, `user_settings`, and `stored_files`.

---

### Step 2: Deploy Backend to Render (Region: `singapore`, Plan: `Standard`)

> **Why Singapore & Standard?** Render has a native Singapore region matching Neon Singapore. The **Standard plan (2 GB RAM)** provides sufficient headroom for PyTorch and SentenceTransformer embedding models without OOM risk. Render bills per second, so you can suspend the instance after evaluations or demos to minimize cost.

1. Connect your GitHub repository to [Render](https://dashboard.render.com).
2. Click **New +** -> **Blueprint**, and select your repository. Render automatically reads [render.yaml](render.yaml).
3. Alternatively, create a **Web Service** manually:
   - **Runtime**: `Docker`
   - **Docker Context**: `./backend`
   - **DockerfilePath**: `./backend/Dockerfile`
   - **Instance Type**: `Standard (2 GB RAM, 1 CPU)`
   - **Region**: `Singapore`
   - **Health Check Path**: `/api/health/ready`
4. Set the following environment variables in the Render Dashboard:
   ```env
   ENVIRONMENT=production
   DATABASE_URL=postgresql+psycopg2://<user>:<password>@ep-example-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   MIGRATION_DATABASE_URL=postgresql+psycopg2://<user>:<password>@ep-example.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   RUN_MIGRATIONS_ON_START=true
   AUTO_CREATE_TABLES=false
   VECTOR_BACKEND=pgvector
   STORAGE_BACKEND=db
   MAX_UPLOAD_MB=10
   USER_STORAGE_QUOTA_MB=50
   GLOBAL_STORAGE_CAP_MB=400
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=openai/gpt-oss-120b
   GROQ_FALLBACK_MODEL=openai/gpt-oss-20b
   TORCH_NUM_THREADS=2
   PREWARM_MODEL=true
   FRONTEND_ORIGIN=https://studymate.vercel.app
   FRONTEND_ORIGIN_REGEX=^https:\/\/studymate-.*\.vercel\.app$
   ```
5. Deploy the service. The startup command will automatically run `alembic upgrade head` and launch uvicorn.

---

### Step 3: Deploy Frontend to Vercel

1. Import your GitHub repository into [Vercel](https://vercel.com).
2. Configure project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add Environment Variables:
   - `VITE_API_URL`: Your Render backend URL (e.g., `https://studymate-api.onrender.com`)
   - `VITE_USE_MOCK`: `false`
4. Click **Deploy**. Vercel uses `frontend/vercel.json` to handle SPA routing and immutable caching.

---

### Step 4: Post-Deployment Smoke Test Checklist

Once deployed, verify full end-to-end functionality:

- [ ] **Health & Readiness**:
  - `GET https://<render-url>/api/health` returns `{"status": "healthy", "database": "ok", "vector_backend": "pgvector", "storage_backend": "db"}`.
  - `GET https://<render-url>/api/health/ready` returns `{"status": "ready"}`.
- [ ] **User Registration**: Register a new student account at `https://<vercel-url>/register`.
- [ ] **Storage Display**:
  - Verify storage usage widget displays on Dashboard and Settings ("0 MB of 50 MB used").
- [ ] **PDF Upload & Ingestion**:
  - Upload a course PDF (up to 10 MB).
  - Verify database: check that rows exist in `stored_files` (`bytea`), `documents`, `chunks`, and `chunk_vectors`.
  - Status updates to `ready` (100%).
  - Storage progress updates accurately.
- [ ] **Academic Chat & Citations**:
  - Ask a question specific to the uploaded material.
  - Verify SSE answer streams smoothly.
  - Verify cited sources `[1]`, `[2]` appear in the citation drawer with page numbers and PDF snippet views.
- [ ] **Storage Quota Enforcement**:
  - Verify that at 80% usage, warning styling triggers.
  - Verify that if user quota (50 MB) or global cap (400 MB) is reached, uploads are blocked with clear feedback.
- [ ] **Account Cleanup**: Delete the test user and verify that all documents, vectors, and database files in `stored_files` are cascade-deleted.

---

## 💻 Local Development

Run locally with SQLite, ChromaDB, and local file storage:

```bash
# 1. Setup backend
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux / macOS

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In another terminal, start the frontend:
```bash
cd frontend
npm install
npm run dev
```

- Web UI: `http://localhost:5173`
- API Docs: `http://localhost:8000/docs`

---

## 🗄️ Database Migrations & Vector Utilities

### Running Migrations
```bash
cd backend
alembic upgrade head      # Apply all pending migrations
alembic downgrade -1      # Roll back last migration
```

### Migrating Existing Local SQLite & Files to Neon Postgres
If migrating an existing local development deployment to Neon:
```bash
cd backend
# Dry run first to verify counts and PDF detection
python scripts/migrate_local_to_neon.py --neon-url "postgresql+psycopg2://<user>:<password>@ep-example.ap-southeast-1.aws.neon.tech/neondb?sslmode=require" --dry-run

# Run migration (copies users, chats, documents, chunks, vectors, and streams PDFs into stored_files)
python scripts/migrate_local_to_neon.py --neon-url "postgresql+psycopg2://<user>:<password>@ep-example.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
```

### Backing Up Neon Database
```bash
cd backend
python scripts/backup_neon.py --neon-url "postgresql+psycopg2://<user>:<password>@ep-example.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
```

### Reindexing Vectors from Relational Data
```bash
cd backend
python scripts/reindex.py
```

---

## 🧪 Testing

Run the automated test suite (76+ tests covering security, rate limiting, Neon retry, database storage streaming, quotas, pgvector, and cascades):

```bash
cd backend
pytest -v
```

---

## 💰 Cost Control Tips (Render & Neon)

- **Render Suspends**: Render bills per second for Standard instances. If you are conducting a demo or university evaluation, keep the service active. When not in use, click **Suspend** in the Render dashboard to pause billing.
- **Neon Free Tier**: Free tier includes 0.5 GB (512 MB) shared storage. With our configured `GLOBAL_STORAGE_CAP_MB=400` soft cap and `USER_STORAGE_QUOTA_MB=50` user quota, the system will pause new uploads before exceeding the 500 MB ceiling, preventing Neon from suspending the project.
- **Groq Free & Tier 1**: Groq provides fast, free LPU inferences for `openai/gpt-oss-120b` and `openai/gpt-oss-20b`.

---

## 📝 License

Distributed under the MIT License. Built for academic study, research, and collaborative learning.
