from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.security.authentication import current_user
from app.services.geospatial_service import validate_polygon
from app.services.json_storage import read_records
from app.services.reference_regions import reference_feature_collection, reference_records
router=APIRouter(prefix="/regions",tags=["regions"])
class RegionIn(BaseModel): geojson: dict
@router.post("/validate")
def validate(body:RegionIn,user=Depends(current_user)): return validate_polygon(body.geojson)
@router.get("/reference-data")
def reference_data():
    return reference_records()

@router.get("/reference-regions")
def reference_regions():
    """GeoJSON polygons only for reliably matched CSV reference rows."""
    from fastapi import HTTPException
    try:
        return reference_feature_collection()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

@router.get("/{region_id}")
def get_region(region_id: str, user=Depends(current_user)):
    from fastapi import HTTPException
    region = next((r for r in read_records("regions") if r["id"] == region_id), None)
    if not region:
        raise HTTPException(404, "Region not found")
    return region

@router.get("/{region_id}/overlaps")
def overlaps(region_id: str, user=Depends(current_user)):
    from fastapi import HTTPException
    region = next((r for r in read_records("regions") if r["id"] == region_id), None)
    if not region:
        raise HTTPException(404, "Region not found")
    # Bounding-box overlap is a warning only; it is not a precise polygon intersection.
    def bbox(g):
        geom = g.get("geometry", g)
        pts = geom.get("coordinates", [[]])[0]
        return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else None
    a = bbox(region["geojson"])
    found = []
    for r in read_records("regions"):
        if r["id"] == region_id or not a:
            continue
        b = bbox(r["geojson"])
        if b and a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
            found.append({"region_id": r["id"], "project_id": r.get("project_id"), "warning_type": "bounding_box_overlap"})
    return {"overlaps": found, "note": "Bounding-box overlap is only a warning, not proof of polygon intersection."}
