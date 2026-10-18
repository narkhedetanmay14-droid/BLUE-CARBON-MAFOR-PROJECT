from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from app.services.json_storage import read_records, write_records, append_record
from app.security.authentication import current_user
router=APIRouter(prefix="/projects", tags=["projects"])
def now(): return datetime.now(timezone.utc).isoformat()
class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=3000)
    ecosystem_type: str = Field(pattern="^(mangrove|seagrass|salt_marsh|other)$")
    country: str = Field(min_length=2, max_length=80)
    state: str = Field(default="", max_length=80)
    locality: str = Field(default="", max_length=120)
    start_date: str | None = None
    geojson: dict
@router.get("")
def list_projects(user=Depends(current_user)):
    projects=read_records("projects")
    return projects if user["role"]=="admin" else [p for p in projects if p["owner_id"]==user["id"]]
@router.post("", status_code=201)
def create_project(body: ProjectIn, user=Depends(current_user)):
    from app.services.geospatial_service import validate_polygon
    result=validate_polygon(body.geojson)
    if not result["valid"]: raise HTTPException(422, result["error"])
    project={"id":str(uuid.uuid4()),"name":body.name,"description":body.description,"ecosystem_type":body.ecosystem_type,"country":body.country,"state":body.state,"locality":body.locality,"start_date":body.start_date,"owner_id":user["id"],"geojson":body.geojson,"area_hectares":result["area_hectares"],"status":"pending_review","created_at":now(),"updated_at":now()}
    append_record("projects",project)
    append_record("regions",{"id":str(uuid.uuid4()),"project_id":project["id"],"geojson":body.geojson,"area_hectares":result["area_hectares"],"created_at":now()})
    return project
@router.get("/{project_id}")
def get_project(project_id: str, user=Depends(current_user)):
    p=next((x for x in read_records("projects") if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if user["role"]!="admin" and p["owner_id"]!=user["id"]: raise HTTPException(403,"Not your project")
    return p
@router.put("/{project_id}")
def update_project(project_id: str, body: dict, user=Depends(current_user)):
    projects=read_records("projects"); p=next((x for x in projects if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if user["role"]!="admin" and p["owner_id"]!=user["id"]: raise HTTPException(403,"Not your project")
    if p["status"]=="approved" and user["role"]!="admin": raise HTTPException(409,"Approved projects require an admin correction workflow")
    for key in ["name","description","ecosystem_type","country","state","locality","start_date"]:
        if key in body: p[key]=body[key]
    p["updated_at"]=now(); write_records("projects",projects); return p
@router.delete("/{project_id}")
def delete_project(project_id: str, user=Depends(current_user)):
    projects=read_records("projects"); p=next((x for x in projects if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if p["owner_id"]!=user["id"] and user["role"]!="admin": raise HTTPException(403,"Not your project")
    if p["status"]=="approved": raise HTTPException(409,"Approved projects cannot be deleted")
    write_records("projects",[x for x in projects if x["id"]!=project_id]); return {"deleted":True}
