from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[88.60, 22.10], [88.61, 22.10], [88.61, 22.11], [88.60, 22.11], [88.60, 22.10]]],
}


def setup_marketplace_test(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "seller-1", "username": "seller", "display_name": "Seller", "role": "user", "password_hash": hash_password("Password123!"), "suspended": False},
        {"id": "buyer-1", "username": "buyer", "display_name": "Buyer", "role": "user", "password_hash": hash_password("Password123!"), "suspended": False},
        {"id": "admin-1", "username": "admin_user", "display_name": "Admin", "role": "admin", "password_hash": hash_password("Password123!"), "suspended": False},
    ])
    client = TestClient(app)
    res_s = client.post("/api/auth/login", json={"username": "seller", "password": "Password123!"})
    res_b = client.post("/api/auth/login", json={"username": "buyer", "password": "Password123!"})
    res_a = client.post("/api/auth/login", json={"username": "admin_user", "password": "Password123!"})

    auth_seller = {"Authorization": f"Bearer {res_s.json()['access_token']}"}
    auth_buyer = {"Authorization": f"Bearer {res_b.json()['access_token']}"}
    auth_admin = {"Authorization": f"Bearer {res_a.json()['access_token']}"}

    return client, auth_seller, auth_buyer, auth_admin


def test_marketplace_unapproved_project_cannot_have_available_credits(monkeypatch, tmp_path):
    client, auth_seller, auth_buyer, _ = setup_marketplace_test(monkeypatch, tmp_path)

    # Unauthenticated request rejected
    assert client.get("/api/marketplace/projects").status_code == 401

    # Create pending project
    proj_res = client.post("/api/projects", headers=auth_seller, json={
        "name": "Pending Mangrove", "description": "Unapproved project", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Gosaba", "geojson": POLYGON,
    })
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # In database, simulate an unauthorized credit record attached to this unapproved project
    json_storage.write_records("carbon_credits", [
        {"id": "c-unapproved", "project_id": proj_id, "owner_id": "seller-1", "total_quantity": 500.0, "available_quantity": 500.0, "verification_status": "verified", "eligibility_status": "eligible"}
    ])

    # Marketplace endpoint must NOT represent credits as available because project is unapproved
    res = client.get("/api/marketplace/projects", headers=auth_buyer)
    assert res.status_code == 200
    item = next(p for p in res.json() if p["project_id"] == proj_id)
    assert item["verification_status"] == "pending"
    assert item["available_credits"] == 0.0
    assert item["availability_status"] == "no_credits_available"

    # Attempting to create listing for unapproved project must be rejected (409)
    listing_res = client.post("/api/marketplace/listings", headers=auth_seller, json={
        "credit_id": "c-unapproved", "quantity": 100.0, "price_per_credit": 25.0
    })
    assert listing_res.status_code == 409
    assert "unapproved" in listing_res.text.lower()


def test_marketplace_listing_duplicate_and_purchase_prevention(monkeypatch, tmp_path):
    client, auth_seller, auth_buyer, auth_admin = setup_marketplace_test(monkeypatch, tmp_path)

    # Create project and approve it
    proj_res = client.post("/api/projects", headers=auth_seller, json={
        "name": "Approved Mangrove", "description": "Legit project", "ecosystem_type": "mangrove",
        "country": "India", "state": "West Bengal", "locality": "Gosaba", "geojson": POLYGON,
    })
    proj_id = proj_res.json()["id"]
    client.post(f"/api/admin/projects/{proj_id}/approve", headers=auth_admin, json={"reason": "Verified"})

    # Legitimate verified credit batch
    json_storage.write_records("carbon_credits", [
        {"id": "c-legit", "project_id": proj_id, "owner_id": "seller-1", "total_quantity": 100.0, "available_quantity": 100.0, "verification_status": "verified", "eligibility_status": "eligible"}
    ])

    # Marketplace shows available credits
    res = client.get("/api/marketplace/projects", headers=auth_buyer)
    item = next(p for p in res.json() if p["project_id"] == proj_id)
    assert item["available_credits"] == 100.0
    assert item["availability_status"] == "available"

    # Create listing
    list_res = client.post("/api/marketplace/listings", headers=auth_seller, json={
        "credit_id": "c-legit", "quantity": 50.0, "price_per_credit": 30.0
    })
    assert list_res.status_code == 201
    listing_id = list_res.json()["id"]

    # Duplicate listing for the same credit batch is rejected (409)
    dup_res = client.post("/api/marketplace/listings", headers=auth_seller, json={
        "credit_id": "c-legit", "quantity": 50.0, "price_per_credit": 30.0
    })
    assert dup_res.status_code == 409
    assert "active listing already exists" in dup_res.text

    # Seller cannot purchase own listing
    self_buy = client.post(f"/api/marketplace/listings/{listing_id}/purchase", headers=auth_seller, json={"quantity": 10})
    assert self_buy.status_code == 409
    assert "own listing" in self_buy.text

    # Buyer purchase attempt triggers safe non-implemented / disabled response preventing unsupported transfer
    buy_res = client.post(f"/api/marketplace/listings/{listing_id}/purchase", headers=auth_buyer, json={"quantity": 10})
    assert buy_res.status_code == 501
    assert "not enabled" in buy_res.text
