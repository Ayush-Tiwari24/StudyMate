# StudyMate AI — Performance Measurements & Optimization Log

## Environment Baseline

- **Backend Runtime**: FastAPI Python 3.11, uvicorn single worker, Render Standard (2 GB RAM, 1 CPU, Singapore).
- **Database**: Neon Serverless PostgreSQL with pgvector 0.8.6 (Singapore, `ap-southeast-1.aws.neon.tech`).
- **LLM Provider**: Groq API (`openai/gpt-oss-20b`).
- **Frontend**: Vite 8 + React 19 SPA on Vercel.

---

## Phase 1: Baseline Measurements (Before Fixes)

### 1. Frontend Bundle Baseline

- **Initial JS Bundle**: `dist/assets/index-BzaA5Qra.js` — **582.38 kB** (175.91 kB gzip)
- **CSS Bundle**: `dist/assets/index-pVXbBh7Y.css` — **25.69 kB** (6.30 kB gzip)
- **Code Splitting**: None (All 8 routes loaded eagerly in root monolithic bundle).

---

### 2. Backend Latency Baseline (Local Backend connected to Neon Singapore)

Measured using `backend/scripts/benchmark_ask.py` on Document #3 (`CS_GATE2027_Syllabus.pdf`, 4 chunks):

#### A. Sequential Mode (1 Standalone + 4 Follow-up Questions)

| Metric | Min | Median | P95 |
|---|---|---|---|
| **Time-to-First-Token (TTFT)** | 4052.6 ms | 4250.5 ms | 6614.0 ms |
| **Total Duration** | 5299.3 ms | 6757.2 ms | 14983.3 ms |

**Per-Question Detail:**
| # | Question Type | TTFT | Total Duration | Tokens Generated | Rewrite Latency | Search Latency | Save Latency |
|---|---|---|---|---|---|---|---|
| Q1 | Standalone | 4070.7 ms | 6916.1 ms | 665 | 0.0 ms (skipped) | 637.3 ms | 781.6 ms |
| Q2 | Follow-up 1 | 6041.6 ms | 16999.9 ms | 459 | 762.2 ms | 2695.3 ms | 8215.2 ms |
| Q3 | Follow-up 2 | 4250.5 ms | 6416.9 ms | 437 | 741.2 ms | 784.8 ms | 678.9 ms |
| Q4 | Follow-up 3 | 4052.6 ms | 5299.3 ms | 42 | 869.2 ms | 899.4 ms | 647.5 ms |
| Q5 | Follow-up 4 | 6757.2 ms | 6757.2 ms | 0 | 738.5 ms | 1616.4 ms | 697.3 ms |

**Observations from Baseline Logs:**
1. Every follow-up query spent ~750ms to 870ms on an extra LLM call to rewrite the query.
2. Saving assistant messages and sources incurred up to 8.2s of blocking database time during connection contention.
3. Every single request executed an extra redundant `SELECT 1` in `get_db()`.
4. Synchronous vector search and embedding blocked the event loop.

#### B. 5 Concurrent Questions Mode

- **Result**: **FAILED / TIMED OUT**
- **Error**: `QueuePool limit of size 3 overflow 2 reached, connection timed out, timeout 30.00` followed by `httpx.ReadTimeout`.
- **Root Cause**: Database sessions were kept open across the entire streaming duration in `ask_question`. With `pool_size=3` and `max_overflow=2` (5 total connections), 5 parallel streams completely exhausted the connection pool, locking out subsequent database operations and causing requests to hang and time out after 30–60 seconds.

---

## Phase 2 & 3: Optimizations Implemented

### 1. LLM Latency & Reasoning Configuration (`services/generation/llm.py`, `core/config.py`)
- Configured Groq reasoning parameter `groq_reasoning_effort="low"` to eliminate multi-second thinking pauses before token generation.
- Scaled `llm_max_tokens=1500`, `rewrite_max_tokens=200`, `llm_request_timeout=30.0`, and `llm_max_retries=1`.
- Added unit tests `tests/test_llm_config.py` and `tests/test_reasoning_filter.py`.

### 2. Skip Unnecessary Rewrites (`services/generation/rag_chain.py`)
- Implemented heuristic `should_rewrite_question()`: self-contained questions bypass the rewrite LLM entirely; only pronoun/reference follow-ups or broad queries trigger rewrite.
- Wrapped rewrite call with `asyncio.wait_for(..., timeout=4.0)` to fall back directly to original query if rewrite takes too long.
- Added unit tests `tests/test_rewrite_policy.py` (6/6 passing).

### 3. Non-Blocking Event Loop (`services/generation/rag_chain.py`, `services/ingestion/pipeline.py`)
- Wrapped synchronous vector retrieval (`retrieve_chunks`), message history fetching, and reranking in `await asyncio.to_thread(...)` so concurrent requests never stall the event loop.
- Bounded ingestion batch size to 16 and constrained CPU threads with `torch.set_num_threads(2)`.
- Added unit tests `tests/test_nonblocking_ask.py`.

### 4. Zero DB Connection Holding During Streaming (`api/routes/chat.py`, `db/session.py`)
- Initial request session is closed immediately via `db.close()` before `StreamingResponse` begins.
- User message and context pre-fetching are committed in an initial sub-50ms transaction.
- Assistant message and sources are persisted in a single short-lived transaction (`save_db = SessionLocal()`) at the end of token generation.
- Expanded pool capacity in `core/config.py` and `render.yaml`: `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=5`, `DB_POOL_TIMEOUT=10`.
- Added automated concurrency test `tests/test_db_pool_streaming.py` verifying 8 concurrent streams succeed with 0 leaked connections.

### 5. Database N+1 Query Elimination (`api/routes/chat.py`)
- Added `.options(selectinload(Chat.documents))` on `/api/chats` and `/api/chats/{chat_id}`.
- Added `.options(selectinload(Chat.messages).selectinload(Message.sources))` and in-memory document filename pre-fetching in `get_chat` and `export_chat`, replacing dozens of single-row roundtrips with an O(1) in-memory lookup.

### 6. pgvector Search Optimization (`services/vectorstore.py`)
- Cached `_check_pgvector_dialect` with `@lru_cache(maxsize=1)`.
- Replaced `engine.begin()` (which performed unnecessary `BEGIN ... COMMIT` roundtrips on read-only queries) with direct `engine.connect()`.
- Avoided redundant `SET LOCAL hnsw.ef_search = 40` roundtrip when setting is default 40.

### 7. Configurable Neon Keep-Alive & Server Hardening (`main.py`, `Dockerfile`, `render.yaml`)
- Added `NEON_KEEPALIVE_SECONDS=180` background task keeping Neon compute warm.
- Added `UnbufferedGZipMiddleware` compressing JSON payloads > 1000B while bypassing `/ask` and `/file` routes to prevent token buffering or binary compression overhead.
- Added CORS `max_age=86400` caching preflight OPTIONS requests for 24 hours.
- Added Uvicorn production flags `--proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 75`.
- Added periodic `: ping\n\n` heartbeat every 15s in SSE streams.

### 8. Frontend Route Code Splitting & Caching (`frontend/src/App.jsx`, `vite.config.js`)
- Replaced monolithic page imports with `React.lazy()` and `<React.Suspense fallback={<PageLoader />}>`.
- Configured Vite/Rolldown `manualChunks` isolating heavy vendor packages (`vendor-markdown`, `vendor-icons`, `vendor-react`, `vendor-http`).

---

## Phase 4: Post-Optimization Measurements (After Fixes)

### 1. Frontend Bundle Comparison

| Asset Chunk | Baseline Size (Before) | Optimized Size (After) | Reduction |
|---|---|---|---|
| **Main JS Entry (`index.js`)** | **582.38 kB** (175.91 kB gz) | **14.37 kB** (4.76 kB gz) | **-97.5%** |
| `vendor-react.js` | Embedded in root | 250.01 kB (79.32 kB gz) | Lazy-cached |
| `vendor-markdown.js` | Embedded in root | 154.43 kB (46.23 kB gz) | Lazy-loaded on demand |
| `vendor-http.js` | Embedded in root | 49.95 kB (18.75 kB gz) | Separated |
| `vendor-icons.js` | Embedded in root | 18.58 kB (7.14 kB gz) | Separated |
| `Chat.js` Page | Embedded in root | 41.83 kB (11.50 kB gz) | Route chunk |
| `Settings.js` Page | Embedded in root | 12.37 kB (3.45 kB gz) | Route chunk |
| `Library.js` Page | Embedded in root | 9.56 kB (3.05 kB gz) | Route chunk |
| `Notes.js` Page | Embedded in root | 7.92 kB (2.61 kB gz) | Route chunk |
| `Dashboard.js` Page | Embedded in root | 6.24 kB (1.71 kB gz) | Route chunk |
| `History.js` Page | Embedded in root | 6.32 kB (2.16 kB gz) | Route chunk |
| `Register.js` Page | Embedded in root | 4.11 kB (1.27 kB gz) | Route chunk |
| `Login.js` Page | Embedded in root | 3.50 kB (1.33 kB gz) | Route chunk |

---

### 2. Backend Latency Comparison

Measured using `backend/scripts/benchmark_ask.py` on Document #3 (`CS_GATE2027_Syllabus.pdf`):

#### A. Sequential Q&A (1 Standalone + 4 Follow-ups)

| Metric | Baseline (Before) | Optimized (After) | Improvement |
|---|---|---|---|
| **Min TTFT** | 4052.6 ms | **2445.3 ms** | **-39.7%** (Reached <2.5s target) |
| **Median TTFT** | 4250.5 ms | **3100.9 ms** | **-27.0%** |
| **P95 TTFT** | 6614.0 ms | **5987.6 ms** | **-9.5%** |
| **Min Total Duration** | 5299.3 ms | **4826.6 ms** | **-8.9%** |
| **Median Total Duration** | 6757.2 ms | **6068.0 ms** | **-10.2%** |
| **P95 Total Duration** | 14983.3 ms | **9153.5 ms** | **-38.9%** |

**Per-Question Breakdown (After):**
| # | Question Type | TTFT | Total Duration | Tokens | Rewrite Latency | Search Latency |
|---|---|---|---|---|---|---|
| Q1 | Standalone | 6590.3 ms | 9713.6 ms | 714 | 0.0 ms (bypassed) | 417.2 ms |
| Q2 | Follow-up 1 | **2445.3 ms** | 6068.0 ms | 849 | 0.0 ms (bypassed) | 443.1 ms |
| Q3 | Follow-up 2 | 3577.0 ms | 4826.6 ms | 159 | 932.9 ms | 453.3 ms |
| Q4 | Follow-up 3 | 2948.6 ms | 5515.4 ms | 524 | 526.7 ms | 418.9 ms |
| Q5 | Follow-up 4 | 3100.9 ms | 6913.0 ms | 1047 | 293.3 ms | 412.9 ms |

#### B. 5 Concurrent Questions Mode

| Metric | Baseline (Before) | Optimized (After) | Status |
|---|---|---|---|
| **Success Rate** | **0% (FAILED)** | **100% (5/5 Succeeded)** | **RESOLVED** |
| **Pool Timeout Errors** | QueuePool timed out after 30s | **0 errors, 0 leaked connections** | **PERFECT** |
| **Min TTFT** | Failed (Timeout) | 7810.2 ms | All completed |
| **Median TTFT** | Failed (Timeout) | 12148.4 ms | All completed |
| **P95 TTFT** | Failed (Timeout) | 16830.9 ms | All completed |
| **Batch Completion Time** | Timed out (>60s) | 20.31 s total for 5 parallel streams | All completed |

---

## Verification Test Suites

1. **Backend Test Suite**: 87 passed, 2 skipped (Postgres-only integration skipped in SQLite test env), 0 failures.
   - `tests/test_db_pool_streaming.py`: 8 concurrent streams with slow LLM passed cleanly, zero pool leaks.
   - `tests/test_rewrite_policy.py`: 6/6 tests passing for rewrite policy and async timeout fallback.
   - `tests/test_nonblocking_ask.py`: Health checks remain sub-50ms while retrieval executes.
   - `tests/test_health.py`: Readiness probe verified in dev/test with DB check and in production with instant 200 OK.
2. **Frontend Test Suite**: 5 test files passed, 19/19 tests passing.
3. **Frontend Build**: `vite build` completed in 2.30s with zero errors and clean bundle splitting.
