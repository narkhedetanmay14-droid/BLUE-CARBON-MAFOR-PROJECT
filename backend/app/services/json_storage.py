import json, os, tempfile, threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "database"
_LOCK = threading.RLock()
NAMES = ["users", "projects", "regions", "assessments", "carbon_credits", "marketplace_listings", "transactions", "verification_records", "audit_logs", "notifications", "sessions"]

def ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        path = DATA_DIR / f"{name}.json"
        if not path.exists():
            atomic_write(path, {"schema_version": 1, "records": []})

def atomic_write(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.stem, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

def read_records(name: str) -> list[dict]:
    if name not in NAMES:
        raise ValueError("Unknown storage collection")
    ensure_storage()
    with _LOCK:
        try:
            data = json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("records"), list):
                raise ValueError("Invalid JSON storage schema")
            return data["records"]
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{name}.json is corrupt; restore from backup") from exc

def write_records(name: str, records: list[dict]):
    if name not in NAMES:
        raise ValueError("Unknown storage collection")
    with _LOCK:
        atomic_write(DATA_DIR / f"{name}.json", {"schema_version": 1, "records": records})

def append_record(name: str, record: dict):
    with _LOCK:
        records = read_records(name)
        records.append(record)
        write_records(name, records)
    return record
