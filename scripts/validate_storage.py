import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1] / "database"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.json_storage import NAMES

for name in NAMES:
    path = root / f"{name}.json"
    if not path.exists():
        print(f"MISSING {name}.json")
        continue
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data.get("records"), list), f"Invalid records in {path.name}"
    print(f"OK {path.name}: {len(data['records'])} records")

# Also verify cache if present
cache_path = root / "reference_regions_cache.json"
if cache_path.exists():
    cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache_data.get("type") == "FeatureCollection"
    print(f"OK reference_regions_cache.json: FeatureCollection with {len(cache_data.get('features', []))} features")
