from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from app.security.authentication import require_admin
from app.services.json_storage import read_records, write_records, append_record
from app.api.projects import project_response, verification_status
router=APIRouter(prefix="/admin",tags=["admin"])
def now(): return datetime.now(timezone.utc).isoformat()
class ApprovalDecision(BaseModel):
    reason: str = Field(default="", max_length=2000)
class RejectionDecision(BaseModel):
    reason: str = Field(min_length=3,max_length=2000)
@router.get("/projects")
def all_projects(admin=Depends(require_admin)):
    return [project_response(project) for project in read_records("projects")]
def decide(project_id, status, body, admin):
    ps=read_records("projects"); p=next((x for x in ps if x["id"]==project_id),None)
    if not p: raise HTTPException(404,"Project not found")
    if status == "approved" and verification_status(p) not in {"pending", "corrections_requested"}:
        raise HTTPException(409, "Only pending projects may be approved")
    if status in {"rejected", "corrections_requested"} and verification_status(p) == "approved":
        raise HTTPException(409, "Approved projects cannot be rejected without a correction workflow")
    p["verification_status"]=status
    p["status"]="pending_review" if status == "corrections_requested" else status
    p["updated_at"]=now(); write_records("projects",ps)
    rec={"id":__import__("uuid").uuid4().hex,"project_id":project_id,"admin_id":admin["id"],"decision":status,"reason":body.reason,"created_at":now()}
    append_record("verification_records",rec); append_record("audit_logs",{"event":"project_decision",**rec})
    append_record("notifications",{"id":__import__("uuid").uuid4().hex,"user_id":p["owner_id"],"message":f"Project {project_id}: {status}","created_at":now(),"read":False})
    return {"project":project_response(p),"verification":rec}
@router.post("/projects/{project_id}/approve")
def approve(project_id:str,body:ApprovalDecision,admin=Depends(require_admin)): return decide(project_id,"approved",body,admin)
@router.post("/projects/{project_id}/reject")
def reject(project_id:str,body:RejectionDecision,admin=Depends(require_admin)): return decide(project_id,"rejected",body,admin)
@router.post("/projects/{project_id}/request-corrections")
def corrections(project_id:str,body:RejectionDecision,admin=Depends(require_admin)): return decide(project_id,"corrections_requested",body,admin)
@router.get("/users")
def users(admin=Depends(require_admin)): return [{k:v for k,v in u.items() if k!="password_hash"} for u in read_records("users")]
@router.get("/audit-logs")
def audit(admin=Depends(require_admin)): return read_records("audit_logs")

@router.get("/analysis")
def approved_project_analysis(admin=Depends(require_admin)):
    """Administrative analysis contains no pending or rejected submissions."""
    users = {user["id"]: user for user in read_records("users")}
    transactions = read_records("transactions")
    rows = []
    for project in read_records("projects"):
        if verification_status(project) != "approved":
            continue
        usage, usage_available = credit_usage(project["id"], transactions)
        owner = users.get(project.get("owner_id"), {})
        item = project_response(project)
        rows.append({
            "project": item,
            "project_id": item["id"],
            "project_name": item["name"],
            "owner": {"id": owner.get("id"), "username": owner.get("username"), "display_name": owner.get("display_name")},
            "location": {"country": item.get("country"), "state": item.get("state"), "locality": item.get("locality"), "reference_region": item.get("reference_region")},
            "verification_status": item["verification_status"],
            "carbon_credit_usage": usage if usage_available else None,
            "carbon_credit_usage_status": "available" if usage_available else "not_available",
        })
    return rows

def credit_usage(project_id: str, transactions: list[dict]) -> tuple[float, bool]:
    """Sum only explicit persisted credit-use ledger events.

    Issued/available credit balances are deliberately excluded.  A readable
    ledger with no matching usage event establishes zero; a malformed matching
    event is reported as unavailable instead of being guessed.
    """
    used = 0.0
    usage_events = {"used", "use", "retired", "retire", "burned", "burn"}
    amount_keys = ("credits_used", "used_quantity", "quantity_used", "quantity")
    for transaction in transactions:
        if transaction.get("project_id") != project_id:
            continue
        event = str(transaction.get("event") or transaction.get("type") or transaction.get("action") or "").casefold()
        if event not in usage_events:
            continue
        raw_amount = next((transaction[key] for key in amount_keys if key in transaction), None)
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            return 0.0, False
        if amount < 0:
            return 0.0, False
        used += amount
    return used, True
