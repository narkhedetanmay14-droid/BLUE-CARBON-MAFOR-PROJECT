from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}


def setup_users_and_projects(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "usr-1", "username": "alice", "display_name": "Alice Green", "role": "user", "password_hash": hash_password("AlicePass123!"), "suspended": False},
        {"id": "usr-2", "username": "bob", "display_name": "Bob Blue", "role": "user", "password_hash": hash_password("BobPass123!"), "suspended": False},
    ])
    client = TestClient(app)
    res_a = client.post("/api/auth/login", json={"username": "alice", "password": "AlicePass123!"})
    res_b = client.post("/api/auth/login", json={"username": "bob", "password": "BobPass123!"})
    auth_a = {"Authorization": f"Bearer {res_a.json()['access_token']}"}
    auth_b = {"Authorization": f"Bearer {res_b.json()['access_token']}"}
    return client, auth_a, auth_b


def test_profile_empty_state_uninvented_numbers(monkeypatch, tmp_path):
    client, auth_a, _ = setup_users_and_projects(monkeypatch, tmp_path)

    # When no projects or credit records exist, must report "not_recorded", not invent numbers
    res = client.get("/api/auth/profile", headers=auth_a)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["username"] == "alice"
    assert data["user"]["display_name"] == "Alice Green"
    assert data["allocations"] == []
    assert data["total_allocated"] == 0.0
    assert data["total_deductions"] == 0.0
    assert data["remaining_balance"] is None
    assert data["balance"] == "Not recorded"
    assert data["ledger_status"] == "not_recorded"
    assert data["units"] == "tCO2e"


def test_profile_project_wise_allocations_and_deductions(monkeypatch, tmp_path):
    client, auth_a, auth_b = setup_users_and_projects(monkeypatch, tmp_path)

    # Alice creates two projects
    p1 = client.post("/api/projects", headers=auth_a, json={
        "name": "Alice Sundarbans Plot 1", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Gosaba", "geojson": POLYGON,
    }).json()
    p2 = client.post("/api/projects", headers=auth_a, json={
        "name": "Alice Sundarbans Plot 2", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Kultali", "geojson": POLYGON,
    }).json()

    # Bob creates a project
    p_bob = client.post("/api/projects", headers=auth_b, json={
        "name": "Bob Mangrove Zone", "description": "", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Basanti", "geojson": POLYGON,
    }).json()

    # Authoritative carbon credit ledger
    json_storage.write_records("carbon_credits", [
        # Alice p1: 150 tCO2e
        {"id": "c1", "project_id": p1["id"], "owner_id": "usr-1", "total_quantity": 150.0, "available_quantity": 150.0, "verification_status": "verified"},
        # Alice p2: 200 tCO2e
        {"id": "c2", "project_id": p2["id"], "owner_id": "usr-1", "total_quantity": 200.0, "available_quantity": 200.0, "verification_status": "verified"},
        # Bob p_bob: 500 tCO2e
        {"id": "c3", "project_id": p_bob["id"], "owner_id": "usr-2", "total_quantity": 500.0, "available_quantity": 500.0, "verification_status": "verified"},
    ])

    # Transactions / deductions for Alice
    json_storage.write_records("transactions", [
        # Alice retired 30 tCO2e from p1
        {"id": "t1", "project_id": p1["id"], "seller_id": "usr-1", "event": "retired", "quantity": 30.0},
        # Alice used 20 tCO2e from p1
        {"id": "t2", "project_id": p1["id"], "seller_id": "usr-1", "event": "used", "quantity": 20.0},
        # Alice reserved 50 tCO2e from p2
        {"id": "t3", "project_id": p2["id"], "seller_id": "usr-1", "event": "reserved", "quantity": 50.0},
        # Bob retired 100 tCO2e
        {"id": "t4", "project_id": p_bob["id"], "seller_id": "usr-2", "event": "retired", "quantity": 100.0},
    ])

    # Check Alice's profile
    res_a = client.get("/api/auth/profile", headers=auth_a)
    assert res_a.status_code == 200
    data_a = res_a.json()

    assert data_a["units"] == "tCO2e"
    assert data_a["total_allocated"] == 350.0
    assert data_a["total_deductions"] == 100.0
    assert data_a["remaining_balance"] == 250.0
    assert data_a["balance"] == 250.0

    allocs = {a["project_id"]: a for a in data_a["allocations"]}
    assert p1["id"] in allocs
    assert allocs[p1["id"]]["allocated"] == 150.0
    assert allocs[p1["id"]]["consumed"] == 50.0  # 30 + 20
    assert allocs[p1["id"]]["remaining"] == 100.0

    assert p2["id"] in allocs
    assert allocs[p2["id"]]["allocated"] == 200.0
    assert allocs[p2["id"]]["consumed"] == 50.0
    assert allocs[p2["id"]]["remaining"] == 150.0

    # Cross-user isolation: Alice CANNOT see Bob's project or balance
    assert p_bob["id"] not in allocs

    # Check Bob's profile
    res_b = client.get("/api/auth/profile", headers=auth_b)
    data_b = res_b.json()
    assert data_b["total_allocated"] == 500.0
    assert data_b["total_deductions"] == 100.0
    assert data_b["remaining_balance"] == 400.0
    assert len(data_b["allocations"]) == 1
    assert data_b["allocations"][0]["project_id"] == p_bob["id"]
