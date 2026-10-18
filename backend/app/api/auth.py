from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone
import uuid, hashlib, secrets
from app.services.json_storage import read_records, write_records, append_record
from app.security.password_hashing import hash_password, verify_password
from app.security.authentication import issue_token, current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


def now():
    return datetime.now(timezone.utc).isoformat()


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterIn):
    users = read_records("users")
    if any(u["username"].lower() == body.username.lower() for u in users):
        raise HTTPException(409, "Username already exists")
    # Public registration strictly hardcodes role to 'user'
    user = {
        "id": str(uuid.uuid4()),
        "username": body.username,
        "display_name": body.display_name,
        "role": "user",
        "password_hash": hash_password(body.password),
        "created_at": now(),
        "suspended": False,
    }
    users.append(user)
    write_records("users", users)
    return {k: v for k, v in user.items() if k != "password_hash"}


@router.post("/login")
def login(body: LoginIn):
    user = next((u for u in read_records("users") if u["username"].lower() == body.username.lower()), None)
    if not user or not verify_password(user.get("password_hash", ""), body.password):
        raise HTTPException(401, "Invalid username or password")
    if user.get("suspended"):
        raise HTTPException(403, "Account suspended")
    return {
        "access_token": issue_token(user["id"]),
        "token_type": "bearer",
        "user": {k: v for k, v in user.items() if k != "password_hash"},
    }


@router.get("/me")
def me(user=Depends(current_user)):
    return user


@router.get("/profile")
def profile(user=Depends(current_user)):
    from app.api.dashboard import calculate_user_allocations_and_balance
    balance_info = calculate_user_allocations_and_balance(user["id"])
    return {
        "user": user,
        **balance_info,
    }


@router.post("/logout")
def logout(authorization: str | None = Header(default=None), user=Depends(current_user)):
    if authorization:
        from app.services.json_storage import DATA_DIR, atomic_write
        import json
        path = DATA_DIR / "sessions.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "records": []}
        digest = hashlib.sha256(authorization.split(" ", 1)[1].strip().encode()).hexdigest()
        data["records"] = [s for s in data["records"] if not secrets.compare_digest(s.get("token_hash", ""), digest)]
        atomic_write(path, data)
    return {"status": "logged_out"}
