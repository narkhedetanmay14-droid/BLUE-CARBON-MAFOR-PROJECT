import getpass, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.json_storage import read_records, write_records
from app.security.password_hashing import hash_password
import uuid
from datetime import datetime, timezone
users=read_records("users")
username=input("Admin username (3+ chars): ").strip()
if len(username)<3: raise SystemExit("Username too short")
if any(u["username"].lower()==username.lower() for u in users): raise SystemExit("Username already exists")
password=getpass.getpass("Admin password (10+ chars): ")
if len(password)<10: raise SystemExit("Password must be at least 10 characters")
confirm=getpass.getpass("Confirm password: ")
if password!=confirm: raise SystemExit("Passwords do not match")
users.append({"id":str(uuid.uuid4()),"username":username,"display_name":"Administrator","role":"admin","password_hash":hash_password(password),"created_at":datetime.now(timezone.utc).isoformat(),"suspended":False})
write_records("users",users)
print("Administrator created.")
