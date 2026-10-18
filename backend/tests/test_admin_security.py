import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import json_storage
from app.security.password_hashing import hash_password
from scripts.create_admin import create_admin_user


def setup_security_test(monkeypatch, tmp_path):
    monkeypatch.setattr(json_storage, "DATA_DIR", tmp_path)
    json_storage.ensure_storage()
    json_storage.write_records("users", [
        {"id": "existing-user", "username": "existing_user", "display_name": "Existing", "role": "user", "password_hash": hash_password("ValidPassword123!"), "suspended": False},
        {"id": "existing-admin", "username": "real_admin", "display_name": "Real Admin", "role": "admin", "password_hash": hash_password("AdminPassword123!"), "suspended": False},
    ])
    return TestClient(app)


def test_public_registration_cannot_escalate_to_admin(monkeypatch, tmp_path):
    client = setup_security_test(monkeypatch, tmp_path)

    # 1. Attacker sends 'role: admin' in registration payload.
    # Because extra='forbid' is set on RegisterIn, it is rejected with 422 Unprocessable Entity
    attack_res = client.post("/api/auth/register", json={
        "username": "attacker_one",
        "password": "Password123!",
        "display_name": "Attacker",
        "role": "admin",
    })
    # If rejected with 422:
    assert attack_res.status_code in {422, 201}
    if attack_res.status_code == 201:
        assert attack_res.json()["role"] == "user"

    # Verify directly in storage that no admin user was created
    users = json_storage.read_records("users")
    attacker = next((u for u in users if u["username"] == "attacker_one"), None)
    if attacker:
        assert attacker["role"] == "user"


def test_admin_endpoints_require_admin_role(monkeypatch, tmp_path):
    client = setup_security_test(monkeypatch, tmp_path)

    # Login as normal user
    res_user = client.post("/api/auth/login", json={"username": "existing_user", "password": "ValidPassword123!"})
    user_headers = {"Authorization": f"Bearer {res_user.json()['access_token']}"}

    # Attempt to access admin endpoints
    assert client.get("/api/admin/projects", headers=user_headers).status_code == 403
    assert client.get("/api/admin/analysis", headers=user_headers).status_code == 403
    assert client.get("/api/admin/audit-logs", headers=user_headers).status_code == 403
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    assert client.get("/api/admin/users/existing-user/profile", headers=user_headers).status_code == 403
    assert client.post("/api/credits/issue", headers=user_headers, json={"project_id": "x", "quantity": 10, "methodology": "m", "evidence_reference": "e"}).status_code == 403

    # Unauthenticated requests to admin endpoints return 401
    assert client.get("/api/admin/projects").status_code == 401
    assert client.get("/api/admin/analysis").status_code == 401
    assert client.get("/api/admin/audit-logs").status_code == 401
    assert client.get("/api/admin/users").status_code == 401


def test_create_admin_script_validation_and_account_protection(monkeypatch, tmp_path):
    client = setup_security_test(monkeypatch, tmp_path)

    # 1. Short username rejected
    with pytest.raises(ValueError, match="at least 3 characters"):
        create_admin_user("ab", "Password12345!")

    # 2. Short password rejected
    with pytest.raises(ValueError, match="at least 10 characters"):
        create_admin_user("new_admin", "short")

    # 3. Existing account cannot be overwritten or elevated
    with pytest.raises(ValueError, match="already exists"):
        create_admin_user("existing_user", "NewAdminPassword123!")

    # Verify existing normal user was NOT elevated to admin
    users = json_storage.read_records("users")
    user = next(u for u in users if u["username"] == "existing_user")
    assert user["role"] == "user"

    # 4. Valid admin creation succeeds
    new_admin = create_admin_user("legit_local_admin", "SecureAdminPass@2026", "Local Security Officer")
    assert new_admin["role"] == "admin"
    assert new_admin["username"] == "legit_local_admin"

    # Newly created admin can log in and access admin endpoints
    login_res = client.post("/api/auth/login", json={"username": "legit_local_admin", "password": "SecureAdminPass@2026"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/admin/projects", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/audit-logs", headers=admin_headers).status_code == 200
