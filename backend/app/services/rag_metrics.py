"""
RAG Ask metrics: per-request retrieval time, LLM time, total latency, tokens sent.
Stores last N requests in memory; optional structured logging.
"""

import logging
import threading
import time
from collections import deque
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_buffer: deque[dict] = deque(maxlen=100)
_lock = threading.Lock()


def record(
    retrieval_time_ms: float,
    llm_time_ms: float,
    total_latency_ms: float,
    tokens_sent: int,
    tokens_returned: int | None = None,
    embedding_time_ms: float | None = None,
) -> None:
    """Record one RAG Ask request metrics."""
    if not getattr(settings, "RAG_METRICS_ENABLED", True):
        return
    size = getattr(settings, "RAG_METRICS_BUFFER_SIZE", 100)
    with _lock:
        global _buffer
        if len(_buffer) >= size and _buffer.maxlen == size:
            pass
        else:
            _buffer = deque(_buffer, maxlen=size)
        entry = {
            "retrieval_time_ms": retrieval_time_ms,
            "llm_time_ms": llm_time_ms,
            "total_latency_ms": total_latency_ms,
            "tokens_sent": tokens_sent,
            "tokens_returned": tokens_returned,
            "embedding_time_ms": embedding_time_ms,
        }
        _buffer.append(entry)
    logger.info(
        "rag_ask_metrics retrieval_ms=%.2f llm_ms=%.2f total_ms=%.2f tokens_sent=%s",
        retrieval_time_ms,
        llm_time_ms,
        total_latency_ms,
        tokens_sent,
        extra={"rag_metrics": entry},
    )


def get_recent() -> list[dict]:
    """Return recent metrics entries (snapshot)."""
    with _lock:
        return list(_buffer)


def get_aggregates() -> dict[str, Any]:
    """Return aggregates over recent entries: count, avg/p95 latency, avg tokens_sent."""
    with _lock:
        entries = list(_buffer)
    if not entries:
        return {"count": 0}
    n = len(entries)
    total_latencies = [e["total_latency_ms"] for e in entries]
    retrieval_latencies = [e["retrieval_time_ms"] for e in entries]
    llm_latencies = [e["llm_time_ms"] for e in entries]
    tokens_sent_list = [e["tokens_sent"] for e in entries]
    total_latencies.sort()
    p95_idx = max(0, int(n * 0.95) - 1)
    return {
        "count": n,
        "avg_total_latency_ms": sum(total_latencies) / n,
        "p95_total_latency_ms": total_latencies[p95_idx],
        "avg_retrieval_ms": sum(retrieval_latencies) / n,
        "avg_llm_ms": sum(llm_latencies) / n,
        "avg_tokens_sent": sum(tokens_sent_list) / n,
    }
