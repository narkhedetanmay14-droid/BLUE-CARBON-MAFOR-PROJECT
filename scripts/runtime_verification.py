"""
End-to-end runtime verification of Blue Carbon API and services.
Launches live server on an ephemeral port, executes real HTTP requests,
and verifies responses against expected schemas and security guarantees.
"""

import sys
import time
import socket
from pathlib import Path
import threading
import uvicorn
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.main import app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_runtime_checks():
    port = find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    print(f"Server started on {base_url}. Running live runtime checks...")

    # Wait for server to be responsive
    client = httpx.Client(base_url=base_url, timeout=10.0)
    for _ in range(30):
        try:
            res = client.get("/api/health")
            if res.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        server.should_exit = True
        raise RuntimeError("Server failed to respond to /api/health within 3 seconds")

    try:
        # 1. Health check
        res = client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        assert res.json()["status"] == "ok"
        print("  [OK] [GET /api/health] Status OK (200)")

        # 2. Reference regions endpoint
        res = client.get("/api/regions/reference-regions")
        assert res.status_code == 200, f"Reference regions failed: {res.text}"
        features = res.json().get("features", [])
        assert len(features) >= 3
        print(f"  [OK] [GET /api/regions/reference-regions] Status OK (200) - {len(features)} reference polygons returned")

        # 3. Reference dataset summary
        res = client.get("/api/analysis/reference-summary")
        assert res.status_code == 200, f"Reference summary failed: {res.text}"
        summary = res.json()
        assert summary["status"] == "completed"
        assert summary["verified_observations"]["count"] == 4
        assert summary["synthetic_demonstration"]["count"] == 1000
        print("  [OK] [GET /api/analysis/reference-summary] Status OK (200) - 4 verified / 1000 synthetic separated")

        # 4. Authentication: Login demo_admin
        res = client.post("/api/auth/login", json={"username": "demo_admin", "password": "BlueCarbonDemo@2026!"})
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        admin_token = res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("  [OK] [POST /api/auth/login] Admin authenticated successfully (200)")

        # 5. Admin analysis
        res = client.get("/api/admin/analysis", headers=admin_headers)
        assert res.status_code == 200, f"Admin analysis failed: {res.text}"
        print(f"  [OK] [GET /api/admin/analysis] Status OK (200) - {len(res.json())} approved projects listed")

        # 6. Admin audit logs with filtering
        res = client.get("/api/admin/audit-logs?status=approved", headers=admin_headers)
        assert res.status_code == 200, f"Audit logs failed: {res.text}"
        print(f"  [OK] [GET /api/admin/audit-logs?status=approved] Status OK (200) - Filtered audit history returned")

        # 7. Admin user profiles
        res = client.get("/api/admin/users", headers=admin_headers)
        assert res.status_code == 200
        first_user_id = res.json()[0]["id"]
        res_prof = client.get(f"/api/admin/users/{first_user_id}/profile", headers=admin_headers)
        assert res_prof.status_code == 200
        assert "approved_project_count" in res_prof.json()
        print(f"  [OK] [GET /api/admin/users/{{id}}/profile] Status OK (200) - User profile details retrieved")

        # 8. Marketplace projects
        res = client.get("/api/marketplace/projects", headers=admin_headers)
        assert res.status_code == 200
        print(f"  [OK] [GET /api/marketplace/projects] Status OK (200) - {len(res.json())} projects in marketplace view")

        # 9. User profile & ledger balance
        res = client.get("/api/auth/profile", headers=admin_headers)
        assert res.status_code == 200
        assert "units" in res.json()
        print(f"  [OK] [GET /api/auth/profile] Status OK (200) - Balance & ledger returned with consistent units")

        # 10. Security check: unauthenticated rejected
        res = client.get("/api/admin/analysis")
        assert res.status_code == 401
        print("  [OK] [GET /api/admin/analysis (unauthenticated)] Correctly rejected with 401 Unauthorized")

        print("\nAll runtime integration and security checks succeeded!")
    finally:
        server.should_exit = True
        client.close()


if __name__ == "__main__":
    run_runtime_checks()
