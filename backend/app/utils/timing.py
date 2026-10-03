"""
StudyMate RAG — Lightweight Timing & Performance Measurement Utility

Provides AskTimer context manager and helpers to track granular stage latencies
without capturing or logging user prompts, document texts, or sensitive payloads.
"""

import time
from contextlib import contextmanager


class AskTimer:
    """Tracks latency breakdown across RAG pipeline stages."""

    def __init__(self):
        self.start_time = time.perf_counter()
        self.timings = {}
        self.token_count = 0
        self.first_token_time = None

    @contextmanager
    def measure(self, stage: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            t1 = time.perf_counter()
            self.timings[f"{stage}_ms"] = round((t1 - t0) * 1000, 2)

    def record_first_token(self):
        if self.first_token_time is None:
            self.first_token_time = time.perf_counter()
            self.timings["first_token_ms"] = round((self.first_token_time - self.start_time) * 1000, 2)

    def record_token(self):
        self.token_count += 1

    def finish(self) -> dict:
        now = time.perf_counter()
        self.timings["total_ms"] = round((now - self.start_time) * 1000, 2)
        if self.first_token_time is not None:
            self.timings["stream_ms"] = round((now - self.first_token_time) * 1000, 2)
        else:
            self.timings["first_token_ms"] = self.timings["total_ms"]
            self.timings["stream_ms"] = 0.0
        self.timings["tokens"] = self.token_count
        return self.timings

    def format_log(self, chat_id: int, user_id: int, model: str) -> str:
        """Structured log string without sensitive text."""
        parts = [
            f"ask_timing",
            f"chat={chat_id}",
            f"user={user_id}",
            f"model={model}",
            f"total_ms={self.timings.get('total_ms', 0)}",
            f"first_token_ms={self.timings.get('first_token_ms', 0)}",
            f"stream_ms={self.timings.get('stream_ms', 0)}",
            f"tokens={self.timings.get('tokens', 0)}",
        ]
        for k, v in self.timings.items():
            if k not in ("total_ms", "first_token_ms", "stream_ms", "tokens"):
                parts.append(f"{k}={v}")
        return " ".join(parts)
