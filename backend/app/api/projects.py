from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from app.services.json_storage import read_records, write_records, append_record
from app.security.authentication import current_user
router=APIRouter(prefix="/projects", tags=["projects"])
def now(): return datetime.now(timezone.utc).isoformat()

def verification_status(project: dict) -> str:
    """Read legacy records without conflating ML and human decisions."""
    return project.get("verification_status") or ({
        "approved": "approved", "rejected": "rejected",
        "corrections_requested": "corrections_requested",
    }.get(project.get("status"), "pending"))

def project_response(project: dict) -> dict:
    response = dict(project)
    response["verification_status"] = verification_status(project)
    response["ml_status"] = project.get("ml_status", "pending")
    # status remains for compatibility with existing persisted clients.
    response["status"] = project.get("status") or response["verification_status"]
    return response

def _set_reference_metadata(project: dict, reference_id: str | None):
    if not reference_id:
        project["reference_region_id"] = None
        project["reference_region"] = None
        return
    from app.services.reference_regions import reference_properties
    try:
        reference = reference_properties(reference_id)
    except RuntimeError as exc:
        raise HTTPException(503, "Unable to verify the selected reference region") from exc
    if reference is None:
        raise HTTPException(422, "Selected reference region is not a valid CSV-backed region")
    # Persist server-derived, read-only reference metadata rather than trusting
    # a copy supplied by the browser.
    project["reference_region_id"] = reference_id
    project["reference_region"] = reference

class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=3000)
    ecosystem_type: str = Field(pattern="^(mangrove|seagrass|salt_marsh|other)$")
    country: str = Field(min_length=2, max_length=80)
    state: str = Field(default="", max_length=80)
    locality: str = Field(default="", max_length=120)
    start_date: str | None = None
    geojson: dict
    reference_region_id: str | None = Field(default=None, max_length=200)
@router.get("")
def list_projects(user=Depends(current_user)):
    if user["role"] == "admin":
        raise HTTPException(403, "Administrators use the verification and analysis endpoints")
    projects=read_records("projects")
    return [project_response(p) for p in projects if p["owner_id"]==user["id"]]
@router.post("", status_code=201)
def create_project(body: ProjectIn, user=Depends(current_user)):
    if user["role"] == "admin":
        raise HTTPException(403, "Administrators cannot register normal-user projects")
    from app.services.geospatial_service import validate_polygon
    result=validate_polygon(body.geojson)
    if not result["valid"]: raise HTTPException(422, result["error"])
    project={"id":str(uuid.uuid4()),"name":body.name,"description":body.description,"ecosystem_type":body.ecosystem_type,"country":body.country,"state":body.state,"locality":body.locality,"start_date":body.start_date,"owner_id":user["id"],"geojson":body.geojson,"area_hectares":result["area_hectares"],"status":"pending_review","verification_status":"pending","ml_status":"pending","created_at":now(),"updated_at":now()}
    _set_reference_metadata(project, body.reference_region_id)
    append_record("projects",project)
    append_record("regions",{"id":str(uuid.uuid4()),"project_id":project["id"],"geojson":body.geojson,"area_hectares":result["area_hectares"],"created_at":now()})
    return project_response(project)

@router.post("/{project_id}/resubmit")
def resubmit_project(project_id: str, body: ProjectIn, user=Depends(current_user)):
    """Return a rejected/correction request to the administrator review queue."""
    if user["role"] == "admin":
        raise HTTPException(403, "Administrators cannot resubmit a normal-user project")
    projects=read_records("projects"); p=next((x for x in projects if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if p["owner_id"] != user["id"]: raise HTTPException(403,"Not your project")
    if verification_status(p) not in {"rejected", "corrections_requested"}:
        raise HTTPException(409,"Only rejected or correction-requested projects can be resubmitted")
    from app.services.geospatial_service import validate_polygon
    result=validate_polygon(body.geojson)
    if not result["valid"]: raise HTTPException(422, result["error"])
    for key in ["name","description","ecosystem_type","country","state","locality","start_date","geojson"]:
        p[key] = getattr(body, key)
    p["area_hectares"] = result["area_hectares"]
    p["verification_status"] = "pending"
    p["status"] = "pending_review"
    p["updated_at"] = now()
    _set_reference_metadata(p, body.reference_region_id)
    write_records("projects",projects)
    regions = read_records("regions")
    saved_region = next((region for region in regions if region.get("project_id") == project_id), None)
    if saved_region:
        saved_region["geojson"] = body.geojson
        saved_region["area_hectares"] = result["area_hectares"]
        saved_region["updated_at"] = now()
        write_records("regions", regions)
    append_record("audit_logs", {"event":"project_resubmitted","project_id":project_id,"user_id":user["id"],"created_at":now()})
    return project_response(p)

@router.get("/{project_id}")
def get_project(project_id: str, user=Depends(current_user)):
    p=next((x for x in read_records("projects") if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if user["role"]!="admin" and p["owner_id"]!=user["id"]: raise HTTPException(403,"Not your project")
    return project_response(p)
@router.put("/{project_id}")
def update_project(project_id: str, body: dict, user=Depends(current_user)):
    projects=read_records("projects"); p=next((x for x in projects if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if user["role"]!="admin" and p["owner_id"]!=user["id"]: raise HTTPException(403,"Not your project")
    if verification_status(p)=="approved" and user["role"]!="admin": raise HTTPException(409,"Approved projects require an admin correction workflow")
    for key in ["name","description","ecosystem_type","country","state","locality","start_date"]:
        if key in body: p[key]=body[key]
    if "geojson" in body:
        if user["role"] == "admin":
            raise HTTPException(403, "Administrators cannot edit user project boundaries")
        from app.services.geospatial_service import validate_polygon
        result = validate_polygon(body["geojson"])
        if not result["valid"]: raise HTTPException(422, result["error"])
        p["geojson"] = body["geojson"]; p["area_hectares"] = result["area_hectares"]
        regions = read_records("regions")
        saved_region = next((region for region in regions if region.get("project_id") == project_id), None)
        if saved_region:
            saved_region["geojson"] = body["geojson"]
            saved_region["area_hectares"] = result["area_hectares"]
            saved_region["updated_at"] = now()
            write_records("regions", regions)
    if "reference_region_id" in body:
        _set_reference_metadata(p, body["reference_region_id"])
    p["updated_at"]=now(); write_records("projects",projects); return project_response(p)
@router.delete("/{project_id}")
def delete_project(project_id: str, user=Depends(current_user)):
    projects=read_records("projects"); p=next((x for x in projects if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if p["owner_id"]!=user["id"] and user["role"]!="admin": raise HTTPException(403,"Not your project")
    if verification_status(p)=="approved": raise HTTPException(409,"Approved projects cannot be deleted")
    write_records("projects",[x for x in projects if x["id"]!=project_id]); return {"deleted":True}
