"""Lightweight tests for RAG optimization (no Chroma/DB required)."""

import pytest


def test_sanitize_query():
    from app.services.rag_service import sanitize_query
    assert sanitize_query("  hello  ") == "hello"
    assert len(sanitize_query("x" * 1000, max_length=100)) <= 100


def test_count_tokens():
    from app.services.rag_service import count_tokens
    n = count_tokens("Hello world")
    assert isinstance(n, int) and n >= 0


def test_prepare_text_for_rag():
    from app.services.rag_service import prepare_text_for_rag
    t = prepare_text_for_rag("  Page 1\n\nSome text.  Page 2  ")
    assert isinstance(t, str)
    assert "Some text" in t or "text" in t


def test_trim_chunks_to_token_budget():
    from app.services.rag_service import trim_chunks_to_token_budget
    chunks = [{"text": "short"}, {"text": "also short"}]
    sys_p = "System"
    pre = "Prefix "
    suf = " Suffix"
    out = trim_chunks_to_token_budget(chunks, sys_p, pre, suf, max_context_tokens=500)
    assert isinstance(out, str)
    assert "short" in out


def test_rag_cache_key():
    from app.services.rag_cache import _cache_key
    k1 = _cache_key("resp", "q", 1)
    k2 = _cache_key("resp", "q", 1)
    assert k1 == k2
    assert len(k1) == 64


def test_rag_metrics_aggregates_empty():
    from app.services.rag_metrics import get_aggregates
    agg = get_aggregates()
    assert isinstance(agg, dict)
    assert "count" in agg
