from fastapi.testclient import TestClient

from app.main import app
from app.security.password_hashing import hash_password
from app.services import json_storage
from app.api import regions


POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}


def isolate_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "user-1", "username": "member", "display_name": "Member", "role": "user", "password_hash": hash_password("correct-password"), "suspended": False},
        {"id": "admin-1", "username": "reviewer", "display_name": "Reviewer", "role": "admin", "password_hash": hash_password("correct-password"), "suspended": False},
    ])


def login(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": "correct-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_project(client, headers, name="Mangrove restoration"):
    response = client.post("/api/projects", headers=headers, json={
        "name": name, "description": "A valid controlled test submission", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Sundarbans", "geojson": POLYGON,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_project_lifecycle_roles_and_approved_analysis(monkeypatch, tmp_path):
    isolate_storage(monkeypatch, tmp_path)
    client = TestClient(app)
    user_headers, admin_headers = login(client, "member"), login(client, "reviewer")
    project = create_project(client, user_headers)

    mine = client.get("/api/projects", headers=user_headers)
    assert mine.status_code == 200 and [item["id"] for item in mine.json()] == [project["id"]]
    assert mine.json()[0]["verification_status"] == "pending"
    assert mine.json()[0]["ml_status"] == "pending"
    assert client.get("/api/projects", headers=admin_headers).status_code == 403
    assert client.get("/api/admin/analysis", headers=user_headers).status_code == 403

    approval = client.post(f"/api/admin/projects/{project['id']}/approve", headers=admin_headers, json={})
    assert approval.status_code == 200, approval.text
    assert approval.json()["project"]["verification_status"] == "approved"
    analysis = client.get("/api/admin/analysis", headers=admin_headers)
    assert analysis.status_code == 200
    assert [item["project_id"] for item in analysis.json()] == [project["id"]]
    assert analysis.json()[0]["carbon_credit_usage"] == 0
    assert analysis.json()[0]["carbon_credit_usage_status"] == "available"
    assert len(client.get("/api/admin/audit-logs", headers=admin_headers).json()) == 1


def test_rejection_requires_reason_and_owner_can_resubmit(monkeypatch, tmp_path):
    isolate_storage(monkeypatch, tmp_path)
    client = TestClient(app)
    user_headers, admin_headers = login(client, "member"), login(client, "reviewer")
    project = create_project(client, user_headers, "Correction project")
    assert client.post(f"/api/admin/projects/{project['id']}/reject", headers=admin_headers, json={"reason": "x"}).status_code == 422
    rejected = client.post(f"/api/admin/projects/{project['id']}/reject", headers=admin_headers, json={"reason": "Boundary evidence is incomplete"})
    assert rejected.status_code == 200
    assert rejected.json()["project"]["verification_status"] == "rejected"
    payload = {"name": "Corrected project", "description": "Updated evidence", "ecosystem_type": "mangrove", "country": "India", "state": "West Bengal", "locality": "Sundarbans", "geojson": POLYGON}
    resubmitted = client.post(f"/api/projects/{project['id']}/resubmit", headers=user_headers, json=payload)
    assert resubmitted.status_code == 200, resubmitted.text
    assert resubmitted.json()["verification_status"] == "pending"
    assert resubmitted.json()["status"] == "pending_review"


def test_reference_regions_only_expose_matched_csv_features(monkeypatch):
    collection = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": "india-west-bengal-north-24-parganas", "geometry": POLYGON, "properties": {"reference_id": "india-west-bengal-north-24-parganas", "district": "North 24 Parganas", "total_mangrove_cover_km2": "26.63"}}], "metadata": {"matched_region_count": 1}}
    monkeypatch.setattr(regions, "reference_feature_collection", lambda: collection)
    response = TestClient(app).get("/api/regions/reference-regions")
    assert response.status_code == 200
    assert response.json()["features"][0]["properties"]["district"] == "North 24 Parganas"
