"""Tests for added endpoints: audit, notifications, settings, reports, auth, profile, users."""

import pytest

# --- Connectivity: all major API areas respond ---

def test_all_main_routes_connected(client):
    """Smoke test: health, dashboard, policy, rules, violations, audit, settings, notifications, auth, profile, users, reports."""
    routes = [
        ("GET", "/health"),
        ("GET", "/dashboard/summary"),
        ("GET", "/policy"),
        ("GET", "/rules"),
        ("GET", "/violations"),
        ("GET", "/audit"),
        ("GET", "/settings"),
        ("GET", "/notifications"),
        ("GET", "/profile/activity"),
        ("GET", "/users"),
        ("GET", "/reports/export/csv"),
    ]
    for method, path in routes:
        if method == "GET":
            r = client.get(path)
        else:
            r = client.post(path, json={})
        # 200 OK, 401 auth required, 503 health unhealthy (e.g. scheduler in test)
        assert r.status_code in (200, 401, 503), f"{method} {path} => {r.status_code}"


# --- Audit ---


def test_audit_list_returns_200(client):
    r = client.get("/audit")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_audit_list_with_params(client):
    r = client.get("/audit?limit=5&entity_type=violation")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_violation_audit_not_found_returns_empty(client):
    r = client.get("/violations/99999/audit")
    assert r.status_code == 200
    assert r.json() == []


# --- Notifications ---


def test_notifications_list_returns_200(client):
    r = client.get("/notifications")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_notifications_mark_read_not_found_returns_404(client):
    r = client.patch("/notifications/99999/read")
    assert r.status_code == 404


# --- Settings ---


def test_settings_get_returns_200(client):
    r = client.get("/settings")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)


def test_settings_patch_returns_200(client):
    r = client.patch(
        "/settings",
        json={"scan_frequency": "hourly", "severity_threshold": 80},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert data.get("scan_frequency") == "hourly"
    assert data.get("severity_threshold") == "80"


# --- Reports export ---


def test_reports_export_csv_returns_200_and_csv(client):
    r = client.get("/reports/export/csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "compliance-report" in r.headers.get("content-disposition", "")


def test_reports_export_pdf_returns_200(client):
    r = client.get("/reports/export/pdf")
    assert r.status_code == 200


# --- Auth (default admin: admin@company.com / Admin@123) ---


def test_auth_login_with_valid_password_returns_token(client):
    r = client.post(
        "/auth/login",
        json={"email": "admin@company.com", "password": "Admin@123", "role": "Admin"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "user" in data
    assert "token" in data
    assert data["user"]["email"] == "admin@company.com"
    assert data["user"]["role"] == "Admin"


def test_auth_login_rejects_unknown_email(client):
    r = client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "any", "role": "Admin"},
    )
    assert r.status_code == 401


def test_auth_login_rejects_wrong_password(client):
    r = client.post(
        "/auth/login",
        json={"email": "admin@company.com", "password": "WrongPassword", "role": "Admin"},
    )
    assert r.status_code == 401


def test_auth_me_without_token_returns_401(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_auth_me_with_token_returns_user(client):
    login_r = client.post(
        "/auth/login",
        json={"email": "admin@company.com", "password": "Admin@123"},
    )
    assert login_r.status_code == 200
    token = login_r.json()["token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "admin@company.com"


def test_auth_2fa_enable_returns_secret(client):
    login_r = client.post(
        "/auth/login",
        json={"email": "admin@company.com", "password": "Admin@123"},
    )
    assert login_r.status_code == 200
    token = login_r.json()["token"]
    r = client.post(
        "/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "secret" in data
    assert "qr_uri" in data


def test_auth_2fa_disable_returns_ok(client):
    login_r = client.post(
        "/auth/login",
        json={"email": "admin@company.com", "password": "Admin@123"},
    )
    assert login_r.status_code == 200
    token = login_r.json()["token"]
    r = client.post(
        "/auth/2fa/disable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json().get("enabled") is False


# --- Profile activity ---


def test_profile_activity_returns_200(client):
    login_r = client.post(
        "/auth/login",
        json={"email": "admin@company.com", "password": "Admin@123"},
    )
    assert login_r.status_code == 200
    token = login_r.json()["token"]
    r = client.get(
        "/profile/activity",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


# --- Users ---


def test_users_list_returns_200(client):
    r = client.get("/users")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_users_create_returns_200(client):
    import uuid
    email = f"newuser-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/users",
        json={
            "email": email,
            "name": "New User",
            "role": "Viewer",
            "department": "Legal",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == email
    assert data["name"] == "New User"
    assert data["role"] == "Viewer"


def test_users_create_duplicate_email_returns_400(client):
    client.post(
        "/users",
        json={"email": "dup@example.com", "name": "First"},
    )
    r = client.post(
        "/users",
        json={"email": "dup@example.com", "name": "Second"},
    )
    assert r.status_code == 400
    assert "already exists" in r.json().get("detail", "").lower()


# --- Policy and rules list (ensure list endpoints work) ---


def test_policy_list_returns_200(client):
    r = client.get("/policy")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_rules_list_returns_200(client):
    r = client.get("/rules")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_violations_list_returns_200(client):
    r = client.get("/violations")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    for item in data:
        assert "suggested_remediation" in item


def test_policy_compare_not_found_returns_404(client):
    """GET /policy/compare with non-existent policy ids returns 404."""
    r = client.get("/policy/compare?old_policy_id=999&new_policy_id=998")
    assert r.status_code == 404
