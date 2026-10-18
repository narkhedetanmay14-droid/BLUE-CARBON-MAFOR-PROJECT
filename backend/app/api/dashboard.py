from fastapi import APIRouter, Depends
from app.security.authentication import current_user, require_admin
from app.services.json_storage import read_records
from app.api.projects import verification_status
router=APIRouter(prefix="/dashboard",tags=["dashboard"])
@router.get("/user")
def user_dashboard(user=Depends(current_user)):
    ps=[p for p in read_records("projects") if p["owner_id"]==user["id"]]
    ass=[a for a in read_records("assessments") if any(p["id"]==a["project_id"] for p in ps)]
    return {"user":user,"total_projects":len(ps),"pending_projects":sum(verification_status(p)=="pending" for p in ps),"approved_projects":sum(verification_status(p)=="approved" for p in ps),"rejected_projects":sum(verification_status(p)=="rejected" for p in ps),"corrections_requested_projects":sum(verification_status(p)=="corrections_requested" for p in ps),"total_area_hectares":round(sum(p.get("area_hectares",0) for p in ps),4),"latest_assessments":ass[-5:],"credits":sum(c.get("available_quantity",0) for c in read_records("carbon_credits") if c.get("owner_id")==user["id"]),"notifications":[n for n in read_records("notifications") if n.get("user_id")==user["id"]][-10:]}
@router.get("/admin")
def admin_dashboard(admin=Depends(require_admin)):
    ps=read_records("projects")
    return {"users":len(read_records("users")),"projects":len(ps),"pending_reviews":sum(verification_status(p)=="pending" for p in ps),"approved_projects":sum(verification_status(p)=="approved" for p in ps),"rejected_projects":sum(verification_status(p)=="rejected" for p in ps),"total_area_hectares":round(sum(p.get("area_hectares",0) for p in ps),4),"assessments":len(read_records("assessments")),"listings":len([x for x in read_records("marketplace_listings") if x.get("status")=="active"])}
