from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}

def setup_user(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "u-1", "username": "field_worker", "display_name": "Field Worker", "role": "user", "password_hash": hash_password("Secret12345!"), "suspended": False},
    ])
    client = TestClient(app)
    res = client.post("/api/auth/login", json={"username": "field_worker", "password": "Secret12345!"})
    assert res.status_code == 200
    return client, {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_reference_regions_endpoint():
    client = TestClient(app)
    res = client.get("/api/regions/reference-regions")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 3
    feature_ids = [f["id"] for f in data["features"]]
    assert "india-west-bengal-south-24-parganas" in feature_ids


def test_validate_polygon_authenticated_and_unauthenticated(monkeypatch, tmp_path):
    client, headers = setup_user(monkeypatch, tmp_path)

    # Unauthenticated rejected with 401
    res_unauth = client.post("/api/regions/validate", json={"geojson": POLYGON})
    assert res_unauth.status_code == 401

    # Authenticated valid polygon
    res_valid = client.post("/api/regions/validate", headers=headers, json={"geojson": POLYGON})
    assert res_valid.status_code == 200
    assert res_valid.json()["valid"] is True
    assert res_valid.json()["area_hectares"] > 0

    # Invalid geometry rejected
    bad_poly = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0]]]}
    res_invalid = client.post("/api/regions/validate", headers=headers, json={"geojson": bad_poly})
    assert res_invalid.status_code == 200
    assert res_invalid.json()["valid"] is False


def test_project_region_selection_and_persistence(monkeypatch, tmp_path):
    client, headers = setup_user(monkeypatch, tmp_path)

    # Valid project creation with reference region selection
    payload = {
        "name": "Sundarbans Conservation Zone",
        "description": "Restoration of saline mangrove strip",
        "ecosystem_type": "mangrove",
        "country": "India",
        "state": "West Bengal",
        "locality": "Gosaba",
        "geojson": POLYGON,
        "reference_region_id": "india-west-bengal-south-24-parganas",
    }
    create_res = client.post("/api/projects", headers=headers, json=payload)
    assert create_res.status_code == 201
    proj = create_res.json()
    assert proj["reference_region_id"] == "india-west-bengal-south-24-parganas"
    assert proj["reference_region"]["district"] == "South 24 Parganas"

    # Verify persistence: retrieve project
    get_res = client.get(f"/api/projects/{proj['id']}", headers=headers)
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["reference_region_id"] == "india-west-bengal-south-24-parganas"
    assert persisted["geojson"] == POLYGON

    # Verify region was persisted in regions collection
    regions_list = json_storage.read_records("regions")
    saved_reg = next((r for r in regions_list if r["project_id"] == proj["id"]), None)
    assert saved_reg is not None
    assert saved_reg["area_hectares"] > 0

    # Test GET /api/regions/{region_id}
    reg_res = client.get(f"/api/regions/{saved_reg['id']}", headers=headers)
    assert reg_res.status_code == 200
    assert reg_res.json()["id"] == saved_reg["id"]


def test_invalid_reference_region_rejected(monkeypatch, tmp_path):
    client, headers = setup_user(monkeypatch, tmp_path)

    # Invalid reference region ID rejected with 422
    payload = {
        "name": "Bogus Region Project",
        "description": "Using non-existent reference region",
        "ecosystem_type": "mangrove",
        "country": "India",
        "geojson": POLYGON,
        "reference_region_id": "non-existent-fake-region-id-9999",
    }
    res = client.post("/api/projects", headers=headers, json=payload)
    assert res.status_code == 422
    assert "not a valid CSV-backed region" in res.text


def test_missing_region_endpoints_error_handling(monkeypatch, tmp_path):
    client, headers = setup_user(monkeypatch, tmp_path)

    # Missing region in GET /api/regions/{id}
    res = client.get("/api/regions/non-existent-id-12345", headers=headers)
    assert res.status_code == 404

    # Missing region in GET /api/regions/{id}/overlaps
    res_overlaps = client.get("/api/regions/non-existent-id-12345/overlaps", headers=headers)
    assert res_overlaps.status_code == 404
