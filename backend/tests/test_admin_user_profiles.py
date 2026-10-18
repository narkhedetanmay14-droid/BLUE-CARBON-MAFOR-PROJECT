from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}


def setup_user_profiles_test(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "adm-id", "username": "admin_auditor", "display_name": "Admin Auditor", "role": "admin", "password_hash": hash_password("AdminPass123!"), "suspended": False},
        {"id": "usr-1", "username": "member_one", "display_name": "Member One", "role": "user", "password_hash": hash_password("MemberPass123!"), "suspended": False},
        {"id": "usr-2", "username": "member_two", "display_name": "Member Two", "role": "user", "password_hash": hash_password("MemberPass123!"), "suspended": False},
    ])
    client = TestClient(app)
    res_a = client.post("/api/auth/login", json={"username": "admin_auditor", "password": "AdminPass123!"})
    res_1 = client.post("/api/auth/login", json={"username": "member_one", "password": "MemberPass123!"})
    res_2 = client.post("/api/auth/login", json={"username": "member_two", "password": "MemberPass123!"})

    auth_admin = {"Authorization": f"Bearer {res_a.json()['access_token']}"}
    auth_m1 = {"Authorization": f"Bearer {res_1.json()['access_token']}"}
    auth_m2 = {"Authorization": f"Bearer {res_2.json()['access_token']}"}
    return client, auth_admin, auth_m1, auth_m2


def test_user_profiles_authorization_isolation(monkeypatch, tmp_path):
    client, auth_admin, auth_m1, auth_m2 = setup_user_profiles_test(monkeypatch, tmp_path)

    # Ordinary user cannot access admin users list or other user's profile
    assert client.get("/api/admin/users", headers=auth_m1).status_code == 403
    assert client.get("/api/admin/users/usr-2/profile", headers=auth_m1).status_code == 403

    # Unauthenticated access rejected
    assert client.get("/api/admin/users/usr-2/profile").status_code == 401

    # Admin CAN access
    res = client.get("/api/admin/users/usr-1/profile", headers=auth_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["username"] == "member_one"
    assert "password_hash" not in data["user"]


def test_user_profile_approved_projects_and_status_transitions(monkeypatch, tmp_path):
    client, auth_admin, auth_m1, auth_m2 = setup_user_profiles_test(monkeypatch, tmp_path)

    # Member 1 creates 2 projects
    p1 = client.post("/api/projects", headers=auth_m1, json={
        "name": "Member 1 Mangrove Restoration", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Gosaba", "geojson": POLYGON,
    }).json()
    p2 = client.post("/api/projects", headers=auth_m1, json={
        "name": "Member 1 Second Project", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Canning", "geojson": POLYGON,
    }).json()

    # Member 2 creates 0 approved projects (only 1 rejected project)
    p3 = client.post("/api/projects", headers=auth_m2, json={
        "name": "Member 2 Rejected Site", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Basanti", "geojson": POLYGON,
    }).json()

    # Admin approves p1, rejects p2, rejects p3
    client.post(f"/api/admin/projects/{p1['id']}/approve", headers=auth_admin, json={"reason": "Approved criteria"})
    client.post(f"/api/admin/projects/{p2['id']}/reject", headers=auth_admin, json={"reason": "Boundary issue"})
    client.post(f"/api/admin/projects/{p3['id']}/reject", headers=auth_admin, json={"reason": "Evidence insufficient"})

    # Check Member 1 profile
    res_m1 = client.get("/api/admin/users/usr-1/profile", headers=auth_admin)
    assert res_m1.status_code == 200
    prof_1 = res_m1.json()

    # Only p1 is in approved projects
    assert prof_1["approved_project_count"] == 1
    assert len(prof_1["approved_projects"]) == 1
    approved_item = prof_1["approved_projects"][0]
    assert approved_item["project_id"] == p1["id"]
    assert approved_item["name"] == "Member 1 Mangrove Restoration"
    assert approved_item["approval_timestamp"] is not None

    # Check Member 2 profile (0 approved projects)
    res_m2 = client.get("/api/admin/users/usr-2/profile", headers=auth_admin)
    assert res_m2.status_code == 200
    prof_2 = res_m2.json()
    assert prof_2["approved_project_count"] == 0
    assert prof_2["approved_projects"] == []
    assert prof_2["total_approved_area_hectares"] == 0.0

    # Non-existent user returns 404
    assert client.get("/api/admin/users/fake-user-id/profile", headers=auth_admin).status_code == 404
