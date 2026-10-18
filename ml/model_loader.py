from pathlib import Path
def require_model(path):
    p=Path(path)
    if not p.is_file(): raise FileNotFoundError(f"Model weights not found: {p}")
    raise RuntimeError("Model architecture, licence, preprocessing and validation metadata must be configured before loading weights.")
