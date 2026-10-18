import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/"database"
for path in sorted(root.glob("*.json")):
    data=json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data.get("records"),list), f"Invalid records in {path.name}"
    print(f"OK {path.name}: {len(data['records'])} records")
