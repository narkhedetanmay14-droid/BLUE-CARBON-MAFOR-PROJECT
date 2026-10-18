import os, secrets, hashlib
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException
from app.services.json_storage import read_records, write_records

TOKEN_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "12"))
def now_iso():
    return datetime.now(timezone.utc).isoformat()
def issue_token(user_id: str) -> str:
    token = secrets.token_urlsafe(36)
    digest = hashlib.sha256(token.encode()).hexdigest()
    sessions = read_records("sessions") if "sessions" in __import__("app.services.json_storage", fromlist=["NAMES"]).NAMES else []
    sessions = [s for s in sessions if s.get("expires_at", "") > now_iso()]
    sessions.append({"token_hash": digest, "user_id": user_id, "expires_at": (datetime.now(timezone.utc)+timedelta(hours=TOKEN_TTL_HOURS)).isoformat()})
    # Sessions are stored in audit-safe users collection? Keep sessions collection explicit.
    from app.services.json_storage import DATA_DIR, atomic_write
    atomic_write(DATA_DIR / "sessions.json", {"schema_version": 1, "records": sessions})
    return token
def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    digest = hashlib.sha256(token.encode()).hexdigest()
    from app.services.json_storage import DATA_DIR
    import json
    path = DATA_DIR / "sessions.json"
    sessions = json.loads(path.read_text(encoding="utf-8")).get("records", []) if path.exists() else []
    session = next((s for s in sessions if secrets.compare_digest(s.get("token_hash", ""), digest) and s.get("expires_at", "") > now_iso()), None)
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    user = next((u for u in read_records("users") if u["id"] == session["user_id"] and not u.get("suspended")), None)
    if not user:
        raise HTTPException(401, "User unavailable")
    return {k:v for k,v in user.items() if k != "password_hash"}
def require_admin(user=__import__("fastapi").Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Administrator access required")
    return user
