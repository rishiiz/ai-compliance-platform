"""Tests for /health endpoint."""

import pytest


def test_health_returns_structured_json(client):
    """GET /health returns status and checks (database, groq, openai, scheduler)."""
    r = client.get("/health")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded", "unhealthy")
    assert "checks" in data
    checks = data["checks"]
    assert "database" in checks
    assert "groq_api_key" in checks
    assert "external_database" in checks
    assert "openai_api_key" in checks
    assert "scheduler" in checks


def test_health_checks_have_status_and_message(client):
    """Each check has status and message."""
    r = client.get("/health")
    assert r.status_code in (200, 503)
    for name, check in r.json()["checks"].items():
        assert "status" in check, f"check {name} missing status"
        assert "message" in check, f"check {name} missing message"


def test_health_database_ok(client):
    """With test env, database check is ok; openai is optional (ok or missing)."""
    r = client.get("/health")
    assert r.status_code in (200, 503)
    data = r.json()
    assert data["checks"]["database"]["status"] == "ok"
    assert data["checks"]["openai_api_key"]["status"] in ("ok", "missing")
    assert data["checks"]["external_database"]["status"] == "unconfigured"
