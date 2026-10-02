# 🏛️ StudyMate AI — Target Online Architecture

This document describes the production cloud architecture for StudyMate AI. The system is designed to be fully online and stateless, meaning **zero critical data is stored on the application server's local disk**. All relational data, vector embeddings, and PDF files live in **Neon Serverless Postgres**.

---

## 🌐 Architecture Overview

```mermaid
graph TD
    Client["Student Browser"]
    Vercel["Vercel SPA (React + Vite)<br/>Static Global CDN"]
    Render["Render Web Service (FastAPI / Docker)<br/>Plan: Standard (2 GB RAM)<br/>Region: Singapore"]
    NeonDB[("Neon Serverless Postgres (Unified Data Store)<br/>Region: ap-southeast-1 (Singapore)<br/>- Relational Data: users, chats, messages, citations<br/>- Vectors: chunk_vectors (pgvector HNSW)<br/>- Uploaded PDFs: stored_files (bytea)")]
    Groq["Groq Cloud LPU<br/>- Primary: openai/gpt-oss-120b<br/>- Fallback: openai/gpt-oss-20b"]

    Client -->|"HTTPS / Assets"| Vercel
    Client -->|"REST & SSE Stream<br/>(VITE_API_URL)"| Render
    Render -->|"Pooled Queries & Vectors<br/>(-pooler Host / Transaction Mode)"| NeonDB
    Render -->|"Alembic Migrations & Backups<br/>(Direct Port 5432)"| NeonDB
    Render -->|"Query Rewrite & Answer<br/>(Filtered Reasoning)"| Groq
```

---

## 📦 Stack Components & Service Roles

| Layer | Service / Technology | Plan / Specs | Region | Purpose & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | Vercel | Free / Hobby | Global Edge | Static Vite build. Client makes direct CORS requests to the Render backend via `VITE_API_URL`. SPA routing configured in `vercel.json`. |
| **Backend** | Render Web Service | Standard (2 GB RAM, 1 CPU) | Singapore | Stateless Docker container running FastAPI and PyTorch CPU. Singapore region selected for low-latency co-location with Neon Singapore. |
| **Relational Data** | Neon Postgres | Serverless Free / Launch | `ap-southeast-1` (Singapore) | Relational database (`users`, `chats`, `messages`, `sources`, `feedback`). Uses PgBouncer transaction pooler for application queries. |
| **Vector Database** | Neon `pgvector` | Native Extension | `ap-southeast-1` (Singapore) | Replaces ChromaDB in production. `chunk_vectors` table indexed with HNSW cosine distance (`ef_construction=64, m=16`). |
| **PDF Storage** | Neon `stored_files` | PostgreSQL `bytea` | `ap-southeast-1` (Singapore) | Uploaded PDFs stored directly in database as binary blobs. Eliminates external S3/Supabase storage dependencies. Chunked SQL streaming (`open_stream`). |
| **LLM Inference** | Groq Cloud | Production API | Global | Primary: `openai/gpt-oss-120b`. Fallback: `openai/gpt-oss-20b`. Reasoning tokens (`<think>`) stripped before client streaming. |
| **Local Dev** | Local Disk + SQLite + Chroma | Local Host | Local | Default fallback when cloud variables are omitted, preserving zero-configuration local development. |

---

## ⚡ Data Flow Pipelines

### 1. Document Ingestion Pipeline
```mermaid
sequenceDiagram
    autonumber
    actor User as Student
    participant API as Render (FastAPI)
    participant Neon as Neon Postgres (stored_files & relational)
    participant Vec as Neon pgvector (chunk_vectors)

    User->>API: POST /api/documents/upload (PDF multipart)
    API->>API: Validate file size (<= 10MB), user quota (<= 50MB), global cap (<= 400MB)
    API->>API: Compute SHA-256 hash & check duplicate
    API->>Neon: INSERT INTO stored_files (key, user_id, data=bytea)
    API->>Neon: INSERT INTO documents (status="uploaded")
    API-->>User: 202 Accepted (document_id)

    Note over API: Background Task (Concurrency Semaphore: 1)
    API->>Neon: Stream PDF bytes from stored_files into temp file
    API->>API: PyMuPDF page extraction & optional OCR
    API->>API: Clean & Chunk pages (Recursive character chunking)
    API->>API: Generate 384d Embeddings (all-MiniLM-L6-v2)
    API->>Vec: INSERT INTO chunk_vectors (id, embedding, metadata)
    API->>Neon: INSERT INTO chunks, UPDATE documents (status="ready", progress=100)
```

### 2. Retrieval-Augmented Generation (RAG) Query Pipeline
```mermaid
sequenceDiagram
    autonumber
    actor User as Student
    participant API as Render (FastAPI)
    participant Neon as Neon Postgres
    participant Vec as Neon pgvector
    participant Groq as Groq LPU

    User->>API: POST /api/chat/message (SSE stream)
    API->>Groq: Generate standalone query from conversation history
    API->>API: Embed standalone query into 384d vector
    API->>Vec: Cosine distance search with HNSW (SET LOCAL hnsw.ef_search = 40)
    Vec-->>API: Top-K passages with page & chunk metadata
    API->>Groq: Prompt with retrieved context passages
    Groq-->>API: Stream answer tokens (stripping reasoning tags)
    API-->>User: SSE token stream (event: token, event: citations, event: done)
    API->>Neon: Record user query, assistant response, and message sources
```
