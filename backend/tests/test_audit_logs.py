from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}


def setup_audit_test(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "adm-1", "username": "auditor", "display_name": "Chief Auditor", "role": "admin", "password_hash": hash_password("AdminPass123!"), "suspended": False},
        {"id": "usr-1", "username": "proponent", "display_name": "Project Proponent", "role": "user", "password_hash": hash_password("UserPass123!"), "suspended": False},
    ])
    client = TestClient(app)
    res_a = client.post("/api/auth/login", json={"username": "auditor", "password": "AdminPass123!"})
    res_u = client.post("/api/auth/login", json={"username": "proponent", "password": "UserPass123!"})
    auth_admin = {"Authorization": f"Bearer {res_a.json()['access_token']}"}
    auth_user = {"Authorization": f"Bearer {res_u.json()['access_token']}"}
    return client, auth_admin, auth_user


def test_audit_logs_authorization(monkeypatch, tmp_path):
    client, auth_admin, auth_user = setup_audit_test(monkeypatch, tmp_path)

    # Unauthenticated rejected with 401
    assert client.get("/api/admin/audit-logs").status_code == 401

    # Normal user rejected with 403
    assert client.get("/api/admin/audit-logs", headers=auth_user).status_code == 403

    # Admin accepted with 200
    res = client.get("/api/admin/audit-logs", headers=auth_admin)
    assert res.status_code == 200
    assert res.json() == []


def test_audit_logs_project_decisions_and_filtering(monkeypatch, tmp_path):
    client, auth_admin, auth_user = setup_audit_test(monkeypatch, tmp_path)

    # Create projects
    p1 = client.post("/api/projects", headers=auth_user, json={
        "name": "Audit Site Alpha", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Gosaba", "geojson": POLYGON,
    }).json()
    p2 = client.post("/api/projects", headers=auth_user, json={
        "name": "Audit Site Beta", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Kultali", "geojson": POLYGON,
    }).json()

    # Admin approves p1 and rejects p2
    client.post(f"/api/admin/projects/{p1['id']}/approve", headers=auth_admin, json={"reason": "Approved criteria met"})
    client.post(f"/api/admin/projects/{p2['id']}/reject", headers=auth_admin, json={"reason": "Insufficient field verification"})

    # Fetch all audit logs
    all_res = client.get("/api/admin/audit-logs", headers=auth_admin)
    assert all_res.status_code == 200
    logs = all_res.json()
    assert len(logs) == 2

    # Verify project name, status, and actual timestamp are exposed
    log_p1 = next(l for l in logs if l["project_id"] == p1["id"])
    assert log_p1["project_name"] == "Audit Site Alpha"
    assert log_p1["status"] == "approved"
    assert log_p1["reason"] == "Approved criteria met"
    assert log_p1["review_timestamp"] is not None

    log_p2 = next(l for l in logs if l["project_id"] == p2["id"])
    assert log_p2["project_name"] == "Audit Site Beta"
    assert log_p2["status"] == "rejected"
    assert log_p2["reason"] == "Insufficient field verification"

    # Filter by status: approved
    app_res = client.get("/api/admin/audit-logs?status=approved", headers=auth_admin)
    assert app_res.status_code == 200
    app_logs = app_res.json()
    assert len(app_logs) == 1
    assert app_logs[0]["project_id"] == p1["id"]

    # Filter by status: rejected
    rej_res = client.get("/api/admin/audit-logs?status=rejected", headers=auth_admin)
    assert len(rej_res.json()) == 1
    assert rej_res.json()[0]["project_id"] == p2["id"]

    # Filter with no matching status returns empty list safely
    empty_res = client.get("/api/admin/audit-logs?status=corrections_requested", headers=auth_admin)
    assert empty_res.status_code == 200
    assert empty_res.json() == []


def test_audit_logs_missing_timestamp_and_record_preservation(monkeypatch, tmp_path):
    client, auth_admin, _ = setup_audit_test(monkeypatch, tmp_path)

    # Manually append an older legacy audit log with missing timestamp
    json_storage.append_record("audit_logs", {
        "id": "legacy-log-1",
        "event": "legacy_event",
        "created_at": None,
        "reason": "Legacy migration",
    })

    res = client.get("/api/admin/audit-logs", headers=auth_admin)
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) == 1
    assert logs[0]["id"] == "legacy-log-1"
    assert logs[0]["review_timestamp"] is None
    assert logs[0]["project_name"] == "Unknown or Deleted Project"

    # Verify original record in storage was preserved and not deleted or corrupted
    raw = json_storage.read_records("audit_logs")
    assert any(r["id"] == "legacy-log-1" for r in raw)
