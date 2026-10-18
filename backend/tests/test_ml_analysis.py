from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password
from ml.dataset_analysis import analyze_reference_dataset

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}


def test_reference_dataset_statistical_analysis():
    summary = analyze_reference_dataset()
    assert summary["status"] == "completed"
    assert "scientific_integrity_notice" in summary

    # Check verified observations
    verified = summary["verified_observations"]
    assert verified["count"] == 4
    districts = {d["district"] for d in verified["records"]}
    assert "South 24 Parganas" in districts
    assert "North 24 Parganas" in districts
    assert "Purba Medinipur" in districts
    assert "West Bengal total" in districts

    # Check synthetic demonstration
    synthetic = summary["synthetic_demonstration"]
    assert synthetic["count"] == 1000
    assert synthetic["cover_km2_stats"]["mean"] > 0
    assert synthetic["carbon_stock_tonnes_stats"]["mean"] > 0
    assert synthetic["tree_count_stats"]["mean"] > 0

    # ML readiness must truthfully report lack of ground truth / rasters
    assert summary["ml_readiness"]["predictive_model_deployable"] is False


def test_analysis_endpoint_honest_insufficient_data(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "user-a", "username": "analyst", "display_name": "Analyst", "role": "user", "password_hash": hash_password("Password123!"), "suspended": False},
        {"id": "user-b", "username": "stranger", "display_name": "Stranger", "role": "user", "password_hash": hash_password("Password123!"), "suspended": False},
    ])
    client = TestClient(app)
    res_a = client.post("/api/auth/login", json={"username": "analyst", "password": "Password123!"})
    auth_a = {"Authorization": f"Bearer {res_a.json()['access_token']}"}
    res_b = client.post("/api/auth/login", json={"username": "stranger", "password": "Password123!"})
    auth_b = {"Authorization": f"Bearer {res_b.json()['access_token']}"}

    # Create project
    proj_res = client.post("/api/projects", headers=auth_a, json={
        "name": "Honest Project", "description": "Testing honest ML", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Sundarbans", "geojson": POLYGON,
    })
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # Stranger cannot analyze project
    assert client.post(f"/api/projects/{proj_id}/analyze", headers=auth_b).status_code == 403

    # Project owner triggers analysis
    analysis_res = client.post(f"/api/projects/{proj_id}/analyze", headers=auth_a)
    assert analysis_res.status_code == 200
    rec = analysis_res.json()

    # Must NOT invent predictions
    assert rec["status"] == "insufficient_data"
    assert rec["tree_count"] is None
    assert rec["carbon_stock_tco2e"] is None
    assert rec["annual_sequestration_tco2e_per_year"] is None
    assert len(rec["limitations"]) > 0

    # Project record verification status must remain untouched
    updated_proj = client.get(f"/api/projects/{proj_id}", headers=auth_a).json()
    assert updated_proj["verification_status"] == "pending"
    assert updated_proj["ml_status"] == "insufficient_data"
