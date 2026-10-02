# 🏛️ StudyMate AI — Target Online Architecture

This document describes the production cloud architecture for StudyMate AI. The system is designed to be fully online and stateless, meaning **zero critical data is stored on the application server's local disk**.

---

## 🌐 Architecture Overview

```mermaid
graph TD
    Client["Student Browser"]
    Vercel["Vercel SPA (React + Vite)<br/>Static Global CDN"]
    Render["Render Web Service (FastAPI / Docker)<br/>Plan: Standard (2 GB RAM)<br/>Region: Singapore"]
    SupabaseDB[("Supabase PostgreSQL + pgvector<br/>Region: ap-south-1 (Mumbai)<br/>- Users, Documents, Chunks, Chats<br/>- chunk_vectors (HNSW Index)")]
    SupabaseS3["Supabase Storage (S3 API)<br/>Region: ap-south-1 (Mumbai)<br/>- Raw Study PDFs"]
    Groq["Groq Cloud LPU<br/>- Primary: openai/gpt-oss-120b<br/>- Fallback: openai/gpt-oss-20b"]

    Client -->|"HTTPS / Assets"| Vercel
    Client -->|"REST & SSE Stream<br/>(VITE_API_URL)"| Render
    Render -->|"SQL Queries & Vectors<br/>Port 6543 / Pooler"| SupabaseDB
    Render -->|"Alembic Migrations<br/>Port 5432 / Direct"| SupabaseDB
    Render -->|"Uploads & PDF Streams<br/>(s3v4 Path-Style)"| SupabaseS3
    Render -->|"Query Rewrite & Answer<br/>(Filtered Reasoning)"| Groq
```

---

## 📦 Stack Components & Service Roles

| Layer | Service / Technology | Plan / Specs | Region | Purpose & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | Vercel | Free / Hobby | Global Edge | Static Vite build. Client makes direct CORS requests to the Render backend via `VITE_API_URL`. SPA routing configured in `vercel.json`. |
| **Backend** | Render Web Service | Standard (2 GB RAM, 1 CPU) | Singapore | Stateless Docker container running FastAPI and PyTorch CPU. Singapore region selected for lowest latency to Supabase Mumbai. |
| **Relational Data** | Supabase PostgreSQL | Free / Pro | `ap-south-1` (Mumbai) | Relational database (users, chats, messages, citations, feedback). Uses transaction pooler (port 6543) for app queries. |
| **Vector Database** | Supabase `pgvector` | Native Extension | `ap-south-1` (Mumbai) | Replaces ChromaDB in production. `chunk_vectors` table indexed with HNSW cosine distance (`ef_construction=64, m=16`). |
| **PDF Storage** | Supabase Storage | S3-Compatible API | `ap-south-1` (Mumbai) | Private storage bucket (`studymate-pdfs`). Accessed via `S3Storage` driver using S3v4 signatures and path-style addressing. |
| **LLM Inference** | Groq Cloud | Production API | Global | Primary: `openai/gpt-oss-120b`. Fallback: `openai/gpt-oss-20b`. Reasoning tokens (`<think>`) stripped before client streaming. |
| **Local Dev** | Local Disk + SQLite + Chroma | Local Host | Local | Default fallback if cloud variables are not provided, preserving zero-configuration local development. |

---

## ⚡ Data Flow Pipelines

### 1. Document Ingestion Pipeline
```mermaid
sequenceDiagram
    autonumber
    actor User as Student
    participant API as Render (FastAPI)
    participant S3 as Supabase Storage (S3)
    participant DB as Supabase DB
    participant Vec as pgvector (chunk_vectors)

    User->>API: POST /api/documents/upload (PDF multipart)
    API->>API: Compute SHA-256 hash & check duplicate
    API->>S3: PutObject (user_id/hash_filename.pdf)
    API->>DB: INSERT INTO documents (status="uploaded")
    API-->>User: 202 Accepted (document_id)

    Note over API: Background Task (Concurrency Semaphore: 1)
    API->>S3: GetObject (stream bytes)
    API->>API: PyMuPDF load_pdf + OCR fallback
    API->>API: Clean text & chunk pages
    API->>API: SentenceTransformer embed_documents (384-dim)
    API->>DB: Bulk INSERT INTO chunks
    API->>Vec: Bulk INSERT INTO chunk_vectors (ON CONFLICT DO UPDATE)
    API->>DB: UPDATE documents SET status="ready", progress=100
```

### 2. Academic RAG Query & Streaming Pipeline
```mermaid
sequenceDiagram
    autonumber
    actor User as Student
    participant API as Render (FastAPI)
    participant Vec as Supabase pgvector
    participant Groq as Groq LPU
    participant DB as Supabase DB

    User->>API: POST /api/chats/{id}/ask (SSE Stream)
    API-->>User: : ready\n\n (Keep-alive flush)
    API->>DB: INSERT INTO messages (role="user")
    opt Multi-turn or Broad Query
        API->>Groq: Query Rewrite (clean_rewritten_query)
        Groq-->>API: Standalone academic search query
    end
    API->>Vec: Cosine Search (embedding <=> query_vec, WHERE user_id/doc_id)
    Vec-->>API: Top-K Chunks + metadata
    API->>Groq: astream(ANSWER_SYSTEM_PROMPT + context)
    loop Token Streaming
        Groq-->>API: Reasoning & answer chunks
        API->>API: ReasoningFilter (drops <think> tags)
        API-->>User: event: token (Clean answer text)
    end
    API->>API: Match [1], [2] citations with retrieved chunks
    API-->>User: event: sources (Cited sources only)
    API->>DB: INSERT INTO messages (role="assistant") + message_sources
    API-->>User: event: done (message_id, latency_ms)
```

---

## 🛡️ Resilience & Stateless Guarantees

1. **Zero Application Server State**: No user documents, vectors, or sqlite databases remain on Render's ephemeral disk. Containers can restart or auto-scale at any time without data loss.
2. **Memory Safety on 2 GB RAM**:
   - PyTorch installed via CPU-only wheels (`--index-url https://download.pytorch.org/whl/cpu`).
   - `TORCH_NUM_THREADS=2` restricts multithreading overhead.
   - Global ingestion concurrency semaphore (`threading.Semaphore(1)`) prevents concurrent memory spikes during PDF processing.
3. **Database Connection Pooling**:
   - Application queries connect via Supabase Transaction Pooler (`pool_size=5, max_overflow=5, pool_recycle=300`).
   - Migrations (`alembic upgrade head`) execute via `MIGRATION_DATABASE_URL` (direct port 5432 or session pooler) to avoid transaction pooling DDL errors.
4. **SSE Keep-Alive & Disconnect Detection**:
   - Streams emit `: ready\n\n` immediately to flush intermediate reverse proxies.
   - Periodic disconnect checks (`request.is_disconnected()`) abort unneeded LLM tokens when the user navigates away.
