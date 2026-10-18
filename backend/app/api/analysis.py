from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import uuid
from app.security.authentication import current_user
from app.services.json_storage import read_records, append_record, write_records
from ml.dataset_analysis import analyze_reference_dataset

router = APIRouter(tags=["analysis"])


@router.get("/analysis/reference-summary")
def reference_summary():
    """Reproducible statistical breakdown of reference mangrove data, demarcating verified vs synthetic data."""
    return analyze_reference_dataset()


@router.post("/projects/{project_id}/analyze")
def analyze(project_id: str, user=Depends(current_user)):
    """Scientifically honest assessment endpoint that refuses to fabricate predictions without valid inputs."""
    p = next((x for x in read_records("projects") if x["id"] == project_id), None)
    if not p:
        raise HTTPException(404, "Project not found")
    if user["role"] != "admin" and p["owner_id"] != user["id"]:
        raise HTTPException(403, "Not your project")

    record = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "status": "insufficient_data",
        "tree_count": None,
        "canopy_area_hectares": None,
        "carbon_stock_tco2e": None,
        "annual_sequestration_tco2e_per_year": None,
        "data_source": None,
        "imagery_date": None,
        "model_name": None,
        "model_version": None,
        "uncertainty": None,
        "methodology": "No compatible georeferenced imagery and validated licensed model configured.",
        "limitations": [
            "No scientific measurements generated: satellite raster imagery and ground-truth calibrations are absent.",
            "District-level reference statistics cannot be substituted for polygon-level biomass measurements.",
            "To prevent inaccurate claims, carbon estimates are not fabricated."
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    append_record("assessments", record)

    # Update project's ML status without altering human administrative verification
    projects = read_records("projects")
    for project in projects:
        if project["id"] == project_id:
            project["ml_status"] = "insufficient_data"
            project["ml_error"] = record["methodology"]
            project["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_records("projects", projects)
            break

    return record


@router.get("/projects/{project_id}/assessments")
def assessments(project_id: str, user=Depends(current_user)):
    p = next((x for x in read_records("projects") if x["id"] == project_id), None)
    if not p:
        raise HTTPException(404, "Project not found")
    if user["role"] != "admin" and p["owner_id"] != user["id"]:
        raise HTTPException(403, "Not your project")
    return [a for a in read_records("assessments") if a["project_id"] == project_id]
