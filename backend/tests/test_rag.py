"""Tests for RAG service and index loading. Verifies backend RAG paths run without error."""

import pytest


def test_health_includes_groq_and_rag_checks(client):
    """Health check includes groq_api_key (and openai optional)."""
    r = client.get("/health")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "checks" in data
    assert "groq_api_key" in data["checks"]
    assert "openai_api_key" in data["checks"]


def test_rag_status_returns_structure():
    """RAG get_rag_status() returns dict with available and reason (no crash)."""
    from app.services.rag_service import get_rag_status

    status = get_rag_status()
    assert isinstance(status, dict)
    assert "available" in status
    assert "reason" in status
    assert isinstance(status["available"], bool)
    assert isinstance(status["reason"], str)


def test_rag_indexed_count_returns_int():
    """RAG get_indexed_count() returns an int (0 or more)."""
    from app.services.rag_service import get_indexed_count

    count = get_indexed_count()
    assert isinstance(count, int)
    assert count >= 0


def test_rag_retrieve_returns_list():
    """RAG retrieve() with a query returns a list (empty or with chunks)."""
    from app.services.rag_service import retrieve

    result = retrieve("test query", top_k=2)
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, dict)
        assert "text" in item


def test_rag_sanitize_query():
    """RAG sanitize_query() cleans and truncates."""
    from app.services.rag_service import sanitize_query

    assert sanitize_query("  hello  ") == "hello"
    assert len(sanitize_query("x" * 1000, max_length=100)) <= 100
