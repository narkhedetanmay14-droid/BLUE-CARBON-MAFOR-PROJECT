from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import uuid
from app.security.authentication import current_user
from app.services.json_storage import read_records, append_record
router=APIRouter(tags=["analysis"])
@router.post("/projects/{project_id}/analyze")
def analyze(project_id:str,user=Depends(current_user)):
    p=next((x for x in read_records("projects") if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if user["role"]!="admin" and p["owner_id"]!=user["id"]: raise HTTPException(403,"Not your project")
    record={"id":str(uuid.uuid4()),"project_id":project_id,"status":"analysis_unavailable","tree_count":None,"canopy_area_hectares":None,"carbon_stock_tco2e":None,"annual_sequestration_tco2e_per_year":None,"data_source":None,"imagery_date":None,"model_name":None,"model_version":None,"uncertainty":None,"methodology":"No compatible georeferenced imagery and validated licensed model configured.","limitations":["No scientific measurements generated.","Configure imagery source and validated model before estimating trees or carbon."],"created_at":datetime.now(timezone.utc).isoformat()}
    append_record("assessments",record)
    return record
@router.get("/projects/{project_id}/assessments")
def assessments(project_id:str,user=Depends(current_user)):
    p=next((x for x in read_records("projects") if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if user["role"]!="admin" and p["owner_id"]!=user["id"]: raise HTTPException(403,"Not your project")
    return [a for a in read_records("assessments") if a["project_id"]==project_id]
