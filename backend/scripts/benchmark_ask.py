"""
StudyMate RAG — Ask Performance Benchmark Script

Measures Time to First Token (TTFT) and Total Duration across sequential
(standalone + follow-ups) and concurrent question answering requests.

Usage:
    python scripts/benchmark_ask.py [--base-url http://localhost:8000]
"""

import os
import sys
import time
import json
import argparse
import statistics
import asyncio
from pathlib import Path
import httpx

QUESTIONS = [
    # 1. Standalone question
    "What are the primary topics and concepts introduced in this syllabus or document?",
    # 2. Follow-up 1 (Pronoun / reference)
    "Can you explain the first topic in more detail?",
    # 3. Follow-up 2 (Pronoun / reference)
    "What are the main prerequisites or requirements for it?",
    # 4. Follow-up 3 (Pronoun / reference)
    "Are there any specific scoring rules, marks or weightage mentioned for them?",
    # 5. Follow-up 4 (Pronoun / reference)
    "Can you summarize key conclusions and preparation steps from the above?",
]


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(data) - 1)
    d0 = data[f] * (c - k)
    d1 = data[c] * (k - f)
    return round(d0 + d1, 2)


async def ask_sse_stream(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    chat_id: int,
    question: str,
    doc_ids: list[int],
) -> dict:
    url = f"{base_url}/api/chats/{chat_id}/ask"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "question": question,
        "document_ids": doc_ids,
    }

    t0 = time.perf_counter()
    first_token_time = None
    done_time = None
    timings = {}
    tokens = 0
    full_text = []

    async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as resp:
        if resp.status_code != 200:
            err_body = await resp.aread()
            raise RuntimeError(f"HTTP {resp.status_code}: {err_body.decode(errors='ignore')}")

        buffer = ""
        current_event = None

        async for chunk in resp.aiter_text():
            buffer += chunk
            while "\n\n" in buffer:
                event_block, buffer = buffer.split("\n\n", 1)
                event_name = "message"
                data_str = ""
                for line in event_block.split("\n"):
                    if line.startswith("event: "):
                        event_name = line[7:].strip()
                    elif line.startswith("data: "):
                        data_str = line[6:].strip()

                if event_name == "token" and data_str:
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    try:
                        token_obj = json.loads(data_str)
                        txt = token_obj.get("text", "")
                        tokens += 1
                        full_text.append(txt)
                    except Exception:
                        pass
                elif event_name == "done" and data_str:
                    done_time = time.perf_counter()
                    try:
                        done_obj = json.loads(data_str)
                        timings = done_obj.get("timings", {})
                    except Exception:
                        pass

    t_end = time.perf_counter()
    if done_time is None:
        done_time = t_end
    if first_token_time is None:
        first_token_time = done_time

    ttft_s = first_token_time - t0
    total_s = done_time - t0

    return {
        "question": question[:35] + ("..." if len(question) > 35 else ""),
        "ttft_ms": round(ttft_s * 1000, 2),
        "total_ms": round(total_s * 1000, 2),
        "tokens": tokens,
        "timings": timings,
    }


async def run_benchmark(base_url: str):
    email = os.environ.get("BENCHMARK_EMAIL", "prtind2005@gmail.com")
    password = os.environ.get("BENCHMARK_PASSWORD", "Password123!")

    print(f"============================================================")
    print(f"StudyMate AI — RAG Performance Benchmark")
    print(f"Target Base URL: {base_url}")
    print(f"Timestamp:       {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"============================================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login
        login_resp = await client.post(
            f"{base_url}/api/auth/login",
            json={"email": email, "password": password},
        )
        if login_resp.status_code != 200:
            print(f"[FAIL] Could not log in: {login_resp.status_code} {login_resp.text}")
            sys.exit(1)

        token = login_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 2. Get ready documents
        docs_resp = await client.get(f"{base_url}/api/documents", headers=auth_headers)
        if docs_resp.status_code != 200:
            print(f"[FAIL] Could not list documents: {docs_resp.status_code}")
            sys.exit(1)

        docs = docs_resp.json().get("documents", [])
        ready_docs = [d for d in docs if d.get("status") == "ready"]
        if not ready_docs:
            print("[FAIL] No ready documents found to benchmark against.")
            sys.exit(1)

        target_doc = ready_docs[0]
        doc_id = target_doc["id"]
        doc_name = target_doc["filename"]
        print(f"Testing with Document #{doc_id} ('{doc_name}', {target_doc.get('chunk_count', 0)} chunks)\n")

        # ---------------------------------------------------------
        # Benchmark 1: Sequential Questions (1 standalone + 4 follow-ups)
        # ---------------------------------------------------------
        print("--- 1. Running Sequential Benchmark (1 standalone + 4 follow-ups) ---")
        chat_create = await client.post(
            f"{base_url}/api/chats",
            headers=auth_headers,
            json={"title": "Benchmark Sequential", "document_ids": [doc_id]},
        )
        chat_id = chat_create.json()["id"]

        sequential_results = []
        for i, q in enumerate(QUESTIONS, start=1):
            print(f"  Q{i}: {q[:55]}...", end="", flush=True)
            res = await ask_sse_stream(client, base_url, token, chat_id, q, [doc_id])
            sequential_results.append(res)
            print(f" -> TTFT: {res['ttft_ms']}ms | Total: {res['total_ms']}ms | Tokens: {res['tokens']}")
            # Small cooldown
            await asyncio.sleep(0.5)

        # ---------------------------------------------------------
        # Benchmark 2: 5 Concurrent Questions
        # ---------------------------------------------------------
        print("\n--- 2. Running Concurrent Benchmark (5 parallel queries) ---")
        concurrent_chats = []
        for i in range(5):
            c = await client.post(
                f"{base_url}/api/chats",
                headers=auth_headers,
                json={"title": f"Benchmark Concurrent {i+1}", "document_ids": [doc_id]},
            )
            concurrent_chats.append(c.json()["id"])

        t_conc_start = time.perf_counter()
        tasks = [
            ask_sse_stream(client, base_url, token, concurrent_chats[i], QUESTIONS[i], [doc_id])
            for i in range(5)
        ]
        concurrent_results = await asyncio.gather(*tasks)
        t_conc_elapsed = (time.perf_counter() - t_conc_start) * 1000
        print(f"  Concurrent batch completed in {round(t_conc_elapsed, 2)}ms")

    # ---------------------------------------------------------
    # Format and Print Benchmark Summary Tables
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY RESULTS")
    print("=" * 60)

    def print_mode_table(mode_name: str, results: list[dict]):
        ttfts = sorted([r["ttft_ms"] for r in results])
        totals = sorted([r["total_ms"] for r in results])

        ttft_min = min(ttfts)
        ttft_med = statistics.median(ttfts)
        ttft_p95 = percentile(ttfts, 95)

        tot_min = min(totals)
        tot_med = statistics.median(totals)
        tot_p95 = percentile(totals, 95)

        print(f"\n### {mode_name}")
        print("| Metric | Min | Median | P95 |")
        print("|---|---|---|---|")
        print(f"| **Time-to-First-Token (TTFT)** | {ttft_min:.1f} ms | {ttft_med:.1f} ms | {ttft_p95:.1f} ms |")
        print(f"| **Total Duration** | {tot_min:.1f} ms | {tot_med:.1f} ms | {tot_p95:.1f} ms |")

        print("\n**Per-Question Detail:**")
        print("| # | Question | TTFT | Total | Tokens | Rewrite | Search | Prompt |")
        print("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(results, start=1):
            t = r.get("timings", {})
            rw = f"{t.get('rewrite_ms', 0):.1f}ms" if "rewrite_ms" in t else "-"
            sc = f"{t.get('search_ms', 0):.1f}ms" if "search_ms" in t else "-"
            pr = f"{t.get('prompt_ms', 0):.1f}ms" if "prompt_ms" in t else "-"
            print(f"| {i} | {r['question']} | {r['ttft_ms']:.1f}ms | {r['total_ms']:.1f}ms | {r['tokens']} | {rw} | {sc} | {pr} |")

    print_mode_table("Sequential (1 Standalone + 4 Follow-ups)", sequential_results)
    print_mode_table("5 Concurrent Questions", concurrent_results)
    print("\n" + "=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StudyMate RAG Benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.base_url.rstrip("/")))
