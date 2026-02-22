"""Tests for API routes (dashboard, scan, database, violations, policy)."""

import pytest


# --- Dashboard ---


def test_dashboard_summary_returns_200_and_keys(client):
    """GET /dashboard/summary returns 200 and expected keys."""
    r = client.get("/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_policies" in data
    assert "total_rules" in data
    assert "total_violations" in data
    assert "pending_violations" in data
    assert "high_severity" in data
    assert "recent_violations" in data
    assert "last_scan_timestamp" in data
    assert "last_scan_status" in data


def test_dashboard_summary_empty_state(client):
    """Dashboard with no data returns zeros and empty recent_violations."""
    r = client.get("/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_policies"] == 0
    assert data["total_rules"] == 0
    assert data["total_violations"] == 0
    assert data["recent_violations"] == []


# --- Scan ---


def test_scan_run_no_rules_returns_200(client):
    """POST /scan/run with no rules returns 200 and message."""
    r = client.post("/scan/run")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "No rules" in data["message"] or data.get("rules_checked") == 0
    assert data.get("rules_checked") == 0
    assert data.get("total_violations") == 0
    assert "by_rule" in data


# --- Database connect ---


def test_database_connect_validation_missing_fields(client):
    """POST /database/connect with missing fields returns 422."""
    r = client.post("/database/connect", json={})
    assert r.status_code == 422


def test_database_connect_validation_invalid_body(client):
    """POST /database/connect with wrong types returns 422."""
    r = client.post(
        "/database/connect",
        json={"host": "localhost", "username": "u", "password": "p"},
    )
    assert r.status_code == 422  # missing db_name


# --- Violations ---


def test_violations_patch_not_found(client):
    """PATCH /violations/999999 returns 404."""
    r = client.patch(
        "/violations/999999",
        json={"status": "approved"},
    )
    assert r.status_code == 404
    assert "not found" in r.json().get("detail", "").lower()


def test_violations_patch_invalid_status(client):
    """PATCH /violations/1 with invalid status returns 400."""
    r = client.patch(
        "/violations/1",
        json={"status": "invalid"},
    )
    assert r.status_code in (400, 404)  # 404 if no violation 1, 400 if validation first


# --- Policy upload ---


def test_policy_upload_no_file_returns_422(client):
    """POST /policy/upload without file returns 422."""
    r = client.post("/policy/upload")
    assert r.status_code == 422


def test_policy_upload_not_pdf_returns_400(client):
    """POST /policy/upload with non-PDF file returns 400."""
    r = client.post(
        "/policy/upload",
        files={"file": ("policy.txt", b"not a pdf", "text/plain")},
    )
    assert r.status_code == 400
    assert "PDF" in r.json().get("detail", "")
