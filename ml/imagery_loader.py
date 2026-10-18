from pathlib import Path
class ImageryUnavailable(RuntimeError): pass
def load_georeferenced_imagery(path: str):
    p=Path(path)
    if not p.exists(): raise ImageryUnavailable(f"Imagery file not found: {p}")
    try:
        import rasterio
    except ImportError as exc: raise ImageryUnavailable("Install ml/requirements-ml.txt to read raster imagery") from exc
    with rasterio.open(p) as dataset:
        if dataset.crs is None: raise ImageryUnavailable("Raster has no CRS; georeferencing is required")
        return {"path":str(p),"crs":str(dataset.crs),"bounds":tuple(dataset.bounds),"count":dataset.count,"width":dataset.width,"height":dataset.height}
