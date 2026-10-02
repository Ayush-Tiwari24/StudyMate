# 📚 StudyMate AI — Academic Question Answering System

> Upload your study PDFs. Ask questions. Get cited answers.

StudyMate AI is a production-hardened web application where students upload study materials (textbooks, lecture notes, research papers) and chat with them using Retrieval-Augmented Generation. Every answer is **grounded in the uploaded documents** with **page-level citations** and full user data isolation.

---

## 🏛️ System Architecture

StudyMate AI supports dual operating modes:
1. **Local Development**: Runs out of the box with zero external cloud dependencies using SQLite, ChromaDB, and local file storage.
2. **Online Cloud Stack**: Completely stateless production deployment with **zero data stored on the application server disk**:
   - **Frontend**: [Vercel](https://vercel.com) (React + Vite static SPA).
   - **Backend**: [Render](https://render.com) (FastAPI Docker web service on Standard 2 GB RAM plan in Singapore).
   - **Relational Database**: [Supabase PostgreSQL](https://supabase.com) in `ap-south-1` (Mumbai) via transaction pooler.
   - **Vector Database**: Supabase `pgvector` (`chunk_vectors` table with HNSW cosine index).
   - **PDF Storage**: Supabase Storage via S3-compatible API (`studymate-pdfs` private bucket).
   - **LLM**: [Groq Cloud](https://groq.com) (`openai/gpt-oss-120b` primary with `openai/gpt-oss-20b` fallback).

For architectural diagrams and database entity relationships, see:
- [docs/architecture.md](docs/architecture.md) — Architecture diagrams and request data flows.
- [docs/er_diagram.md](docs/er_diagram.md) — Relational schema, cascade rules, and indexes.

---

## 🚀 Step-by-Step Online Cloud Deployment

### Step 1: Provision Supabase (Region: `ap-south-1` Mumbai)

> **Why Mumbai?** Mumbai gives the lowest latency for Indian users and Jaipur development. Both relational queries and PDF downloads benefit directly from this proximity.

1. Create a new project on [Supabase](https://supabase.com).
   - **Name**: `studymate-prod`
   - **Region**: Select `ap-south-1` (Mumbai, India).
   - **Database Password**: Generate and securely store a strong password.
2. **Enable `pgvector`**:
   - Navigate to **Database** -> **Extensions**.
   - Search for `vector` and enable it (Alembic migration `0002_pgvector.py` will also execute `CREATE EXTENSION IF NOT EXISTS vector;`).
3. **Configure Storage Bucket**:
   - Navigate to **Storage** -> **New Bucket**.
   - **Bucket Name**: `studymate-pdfs`
   - **Access**: Set to **Private** (authenticated downloads go through the backend).
4. **Generate S3 Credentials**:
   - Navigate to **Project Settings** -> **Storage** -> **S3 Credentials**.
   - Click **Generate New Credentials**. Copy the **Access Key ID** and **Secret Access Key**.
   - The S3 endpoint URL is: `https://<project-ref>.supabase.co/storage/v1/s3`
5. **Get Database Connection Strings**:
   - Navigate to **Project Settings** -> **Database** -> **Connection string**:
   - **Transaction Pooler (Port 6543)** (for `DATABASE_URL`):
     `postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require`
   - **Direct / Session Connection (Port 5432)** (for `MIGRATION_DATABASE_URL`):
     `postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require`

---

### Step 2: Deploy Backend to Render (Region: `singapore`, Plan: `Standard`)

> **Why Singapore & Standard?** Render has no Mumbai region, so Singapore is the closest available region to Supabase Mumbai. The **Standard plan (2 GB RAM)** provides sufficient headroom for PyTorch and SentenceTransformer embedding models without OOM risk. Render bills per second, so you can suspend the instance after evaluations or demos to minimize cost.

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
   DATABASE_URL=postgresql+psycopg2://postgres.<ref>:<pass>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require
   MIGRATION_DATABASE_URL=postgresql+psycopg2://postgres.<ref>:<pass>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
   RUN_MIGRATIONS_ON_START=true
   AUTO_CREATE_TABLES=false
   VECTOR_BACKEND=pgvector
   STORAGE_BACKEND=s3
   S3_BUCKET=studymate-pdfs
   S3_ENDPOINT_URL=https://<ref>.supabase.co/storage/v1/s3
   S3_ACCESS_KEY=<Supabase S3 Access Key>
   S3_SECRET_KEY=<Supabase S3 Secret Key>
   S3_REGION=ap-south-1
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
3. Add Environment Variable:
   - `VITE_API_URL`: Your Render backend URL (e.g., `https://studymate-api.onrender.com`)
   - `VITE_USE_MOCK`: `false`
4. Click **Deploy**. Vercel uses `frontend/vercel.json` to handle SPA routing and immutable caching.

---

### Step 4: Post-Deployment Smoke Test Checklist

Once deployed, verify full end-to-end functionality:

- [ ] **Health & Readiness**:
  - `GET https://<render-url>/api/health` returns `{"status": "healthy", "database": "ok", "vector_backend": "pgvector", "storage_backend": "s3"}`.
  - `GET https://<render-url>/api/health/ready` returns `{"status": "ready"}`.
- [ ] **User Registration**: Register a new student account at `https://<vercel-url>/register`.
- [ ] **PDF Upload & Ingestion**:
  - Upload a course PDF.
  - Check the Supabase Storage dashboard: verify the PDF file is present in `studymate-pdfs`.
  - Check Supabase Database: verify rows exist in `documents`, `chunks`, and `chunk_vectors`.
  - Status updates to `ready` (100%).
- [ ] **Academic Chat & Citations**:
  - Ask a question specific to the uploaded material.
  - Verify SSE answer streams smoothly.
  - Verify that only cited sources `[1]`, `[2]` appear in the citation drawer.
  - Click a citation: verify snippet, page number, and PDF preview work.
- [ ] **Account Cleanup**: Delete the test user and verify that all documents, vectors, and S3 files are automatically purged.

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

### Migrating Existing ChromaDB Vectors to pgvector
If migrating an existing local development deployment to Supabase pgvector:
```bash
cd backend
# Dry run first to verify counts
python scripts/migrate_chroma_to_pgvector.py --dry-run

# Run migration
python scripts/migrate_chroma_to_pgvector.py
```

### Reindexing Vectors from Relational Data
```bash
cd backend
python scripts/reindex.py
```

---

## 🧪 Testing

Run the automated test suite (58+ tests covering security, rate limiting, S3 storage, pgvector, and cascades):

```bash
cd backend
pytest -v
```

---

## 💰 Cost Control Tips (Render & Supabase)

- **Render Suspends**: Render bills per second for Standard instances. If you are conducting a demo or university evaluation, keep the service active. When not in use, click **Suspend** in the Render dashboard to pause billing.
- **Supabase Free Tier**: Free tier includes 500 MB database storage and 1 GB file storage, which holds roughly 100 textbooks and their vector embeddings.
- **Groq Free & Tier 1**: Groq provides fast, free LPU inferences for `openai/gpt-oss-120b` and `openai/gpt-oss-20b`.

---

## 📝 License

Distributed under the MIT License. Built for academic study, research, and collaborative learning.
