import json
from pathlib import Path
from app.services.json_storage import atomic_write
def test_atomic_write(tmp_path):
    path=tmp_path/"records.json"
    atomic_write(path,{"schema_version":1,"records":[{"id":"x"}]})
    assert json.loads(path.read_text())["records"][0]["id"]=="x"
