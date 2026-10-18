from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from app.security.authentication import current_user, require_admin
from app.services.json_storage import read_records, write_records, append_record
router=APIRouter(tags=["marketplace"])
def now(): return datetime.now(timezone.utc).isoformat()
@router.get("/credits")
def credits(user=Depends(current_user)):
    return [c for c in read_records("carbon_credits") if user["role"]=="admin" or c.get("owner_id")==user["id"]]
class IssueIn(BaseModel):
    project_id:str
    quantity:float=Field(gt=0)
    methodology:str=Field(min_length=3,max_length=500)
    evidence_reference:str=Field(min_length=3,max_length=500)
@router.post("/credits/issue")
def issue(body:IssueIn,admin=Depends(require_admin)):
    project=next((p for p in read_records("projects") if p["id"]==body.project_id),None)
    if not project or project["status"]!="approved": raise HTTPException(409,"Project must be approved before credit review")
    assessments=[a for a in read_records("assessments") if a["project_id"]==body.project_id and a["status"]=="completed"]
    if not assessments: raise HTTPException(409,"No completed, validated assessment exists; credits were not issued")
    raise HTTPException(409,"Issuance is disabled until an applicable external crediting methodology and eligibility review are configured")
@router.get("/marketplace/listings")
def listings(user=Depends(current_user)): return [x for x in read_records("marketplace_listings") if x.get("status")=="active"]
class ListingIn(BaseModel):
    credit_id:str
    quantity:float=Field(gt=0)
    price_per_credit:float=Field(gt=0)
@router.post("/marketplace/listings",status_code=201)
def create_listing(body:ListingIn,user=Depends(current_user)):
    credit=next((c for c in read_records("carbon_credits") if c["id"]==body.credit_id),None)
    if not credit or credit.get("owner_id")!=user["id"]: raise HTTPException(404,"Eligible credit batch not found")
    if credit.get("eligibility_status")!="eligible" or credit.get("verification_status")!="verified": raise HTTPException(409,"Credit batch is not eligible for sale")
    if body.quantity>credit.get("available_quantity",0): raise HTTPException(409,"Insufficient available credits")
    listing={"id":str(uuid.uuid4()),"seller_id":user["id"],"credit_id":body.credit_id,"quantity":body.quantity,"remaining_quantity":body.quantity,"price_per_credit":body.price_per_credit,"status":"active","created_at":now()}
    append_record("marketplace_listings",listing); return listing
@router.post("/marketplace/listings/{listing_id}/purchase")
def purchase(listing_id:str, body:dict, user=Depends(current_user)):
    raise HTTPException(501,"Purchase transfers are not enabled until a durable transaction journal and payment confirmation flow are configured.")
@router.post("/marketplace/listings/{listing_id}/cancel")
def cancel(listing_id:str,user=Depends(current_user)):
    listings=read_records("marketplace_listings"); listing=next((x for x in listings if x["id"]==listing_id),None)
    if not listing: raise HTTPException(404,"Listing not found")
    if listing["seller_id"]!=user["id"] and user["role"]!="admin": raise HTTPException(403,"Not listing owner")
    listing["status"]="cancelled"; write_records("marketplace_listings",listings); return listing
@router.get("/transactions")
def transactions(user=Depends(current_user)): return [t for t in read_records("transactions") if user["role"]=="admin" or user["id"] in (t.get("buyer_id"),t.get("seller_id"))]
