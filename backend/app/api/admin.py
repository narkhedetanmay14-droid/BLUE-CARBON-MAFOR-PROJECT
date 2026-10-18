from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from app.security.authentication import require_admin
from app.services.json_storage import read_records, write_records, append_record
router=APIRouter(prefix="/admin",tags=["admin"])
def now(): return datetime.now(timezone.utc).isoformat()
class Decision(BaseModel): reason: str = Field(min_length=3,max_length=2000)
@router.get("/projects")
def all_projects(admin=Depends(require_admin)): return read_records("projects")
def decide(project_id, status, body, admin):
    ps=read_records("projects"); p=next((x for x in ps if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    p["status"]=status; p["updated_at"]=now(); write_records("projects",ps)
    rec={"id":__import__("uuid").uuid4().hex,"project_id":project_id,"admin_id":admin["id"],"decision":status,"reason":body.reason,"created_at":now()}
    append_record("verification_records",rec); append_record("audit_logs",{"event":"project_decision",**rec})
    append_record("notifications",{"id":__import__("uuid").uuid4().hex,"user_id":p["owner_id"],"message":f"Project {project_id}: {status}","created_at":now(),"read":False})
    return {"project":p,"verification":rec}
@router.post("/projects/{project_id}/approve")
def approve(project_id:str,body:Decision,admin=Depends(require_admin)): return decide(project_id,"approved",body,admin)
@router.post("/projects/{project_id}/reject")
def reject(project_id:str,body:Decision,admin=Depends(require_admin)): return decide(project_id,"rejected",body,admin)
@router.post("/projects/{project_id}/request-corrections")
def corrections(project_id:str,body:Decision,admin=Depends(require_admin)): return decide(project_id,"corrections_requested",body,admin)
@router.get("/users")
def users(admin=Depends(require_admin)): return [{k:v for k,v in u.items() if k!="password_hash"} for u in read_records("users")]
@router.get("/audit-logs")
def audit(admin=Depends(require_admin)): return read_records("audit_logs")
