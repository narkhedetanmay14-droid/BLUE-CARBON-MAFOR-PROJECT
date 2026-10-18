from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}


def setup_admin_analysis_data(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "usr-admin", "username": "chief_admin", "display_name": "Chief Admin", "role": "admin", "password_hash": hash_password("AdminPass123!"), "suspended": False},
        {"id": "usr-norm", "username": "normal_dev", "display_name": "Normal Dev", "role": "user", "password_hash": hash_password("UserPass123!"), "suspended": False},
    ])
    client = TestClient(app)
    res_a = client.post("/api/auth/login", json={"username": "chief_admin", "password": "AdminPass123!"})
    res_u = client.post("/api/auth/login", json={"username": "normal_dev", "password": "UserPass123!"})

    auth_admin = {"Authorization": f"Bearer {res_a.json()['access_token']}"}
    auth_user = {"Authorization": f"Bearer {res_u.json()['access_token']}"}
    return client, auth_admin, auth_user


def test_admin_analysis_status_filtering_and_totals(monkeypatch, tmp_path):
    client, auth_admin, auth_user = setup_admin_analysis_data(monkeypatch, tmp_path)

    # Normal user cannot access admin analysis (403)
    assert client.get("/api/admin/analysis", headers=auth_user).status_code == 403
    assert client.get("/api/admin/analysis/summary", headers=auth_user).status_code == 403

    # Create 3 projects: 1 approved, 1 rejected, 1 pending
    p_app = client.post("/api/projects", headers=auth_user, json={
        "name": "Approved Sundarbans Site", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Gosaba", "geojson": POLYGON,
    }).json()
    p_rej = client.post("/api/projects", headers=auth_user, json={
        "name": "Rejected Site", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Basanti", "geojson": POLYGON,
    }).json()
    p_pen = client.post("/api/projects", headers=auth_user, json={
        "name": "Pending Site", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Kultali", "geojson": POLYGON,
    }).json()

    # Admin approves p_app and rejects p_rej
    client.post(f"/api/admin/projects/{p_app['id']}/approve", headers=auth_admin, json={"reason": "Valid"})
    client.post(f"/api/admin/projects/{p_rej['id']}/reject", headers=auth_admin, json={"reason": "Invalid boundary"})

    # Set up credit ledger and usage for approved project
    json_storage.write_records("carbon_credits", [
        {"id": "cc-1", "project_id": p_app["id"], "owner_id": "usr-norm", "total_quantity": 250.0, "available_quantity": 200.0, "verification_status": "verified"}
    ])
    json_storage.write_records("transactions", [
        {"id": "tx-1", "project_id": p_app["id"], "seller_id": "usr-norm", "event": "retired", "quantity": 50.0}
    ])

    # Fetch admin analysis
    res = client.get("/api/admin/analysis", headers=auth_admin)
    assert res.status_code == 200
    rows = res.json()

    # STRICT FILTERING: Only approved project is in the list
    assert len(rows) == 1
    item = rows[0]
    assert item["project_id"] == p_app["id"]
    assert item["project_name"] == "Approved Sundarbans Site"
    assert item["verification_status"] == "approved"
    assert item["carbon_credit_usage"] == 50.0
    assert item["carbon_credit_usage_status"] == "available"
    assert item["user_balance"]["allocated"] == 250.0
    assert item["user_balance"]["used"] == 50.0
    assert item["user_balance"]["remaining"] == 200.0
    assert item["regional_holding"] == "Gosaba"

    # Reconciled summary
    summary_res = client.get("/api/admin/analysis/summary", headers=auth_admin)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_approved_projects"] == 1
    assert summary["total_carbon_credits_allocated"] == 250.0
    assert summary["total_carbon_credits_used"] == 50.0
    assert "Gosaba" in summary["regional_holdings"]
    assert summary["regional_holdings"]["Gosaba"]["project_count"] == 1
