from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from app.security.authentication import current_user, require_admin
from app.services.json_storage import read_records, write_records, append_record
from app.api.projects import verification_status

router = APIRouter(tags=["marketplace"])


def now():
    return datetime.now(timezone.utc).isoformat()


@router.get("/credits")
def credits(user=Depends(current_user)):
    return [c for c in read_records("carbon_credits") if user["role"] == "admin" or c.get("owner_id") == user["id"]]


@router.get("/marketplace/projects")
def marketplace_projects(user=Depends(current_user)):
    """Return projects with authoritative credit availability, region, and approval status."""
    projects = read_records("projects")
    carbon_credits = read_records("carbon_credits")
    listings = [x for x in read_records("marketplace_listings") if x.get("status") == "active"]

    results = []
    for p in projects:
        status = verification_status(p)
        proj_credits = [c for c in carbon_credits if c.get("project_id") == p["id"]]

        # Authoritative rule: only approved projects with verified credits can represent credits as available
        if status == "approved":
            available_credits = sum(
                float(c.get("available_quantity", 0))
                for c in proj_credits
                if c.get("verification_status") == "verified" and c.get("eligibility_status") == "eligible"
            )
            total_issued = sum(float(c.get("total_quantity", 0)) for c in proj_credits)
        else:
            available_credits = 0.0
            total_issued = 0.0

        proj_listings = [l for l in listings if any(c.get("id") == l.get("credit_id") for c in proj_credits)]
        region_name = p.get("reference_region", {}).get("district") if p.get("reference_region") else (p.get("locality") or p.get("state") or p.get("country"))

        results.append({
            "project_id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "ecosystem_type": p.get("ecosystem_type", "mangrove"),
            "country": p.get("country"),
            "state": p.get("state"),
            "locality": p.get("locality"),
            "region": region_name,
            "area_hectares": p.get("area_hectares", 0),
            "verification_status": status,
            "available_credits": round(available_credits, 2),
            "total_issued_credits": round(total_issued, 2),
            "availability_status": "available" if (status == "approved" and available_credits > 0) else "no_credits_available",
            "active_listings_count": len(proj_listings),
        })
    return results


class IssueIn(BaseModel):
    project_id: str
    quantity: float = Field(gt=0)
    methodology: str = Field(min_length=3, max_length=500)
    evidence_reference: str = Field(min_length=3, max_length=500)


@router.post("/credits/issue")
def issue(body: IssueIn, admin=Depends(require_admin)):
    project = next((p for p in read_records("projects") if p["id"] == body.project_id), None)
    if not project or verification_status(project) != "approved":
        raise HTTPException(409, "Project must be approved before credit review")
    assessments = [a for a in read_records("assessments") if a["project_id"] == body.project_id and a["status"] == "completed"]
    if not assessments:
        raise HTTPException(409, "No completed, validated assessment exists; credits were not issued")
    raise HTTPException(409, "Issuance is disabled until an applicable external crediting methodology and eligibility review are configured")


@router.get("/marketplace/listings")
def listings(user=Depends(current_user)):
    raw_listings = [x for x in read_records("marketplace_listings") if x.get("status") == "active"]
    projects = {p["id"]: p for p in read_records("projects")}
    credits = {c["id"]: c for c in read_records("carbon_credits")}

    enriched = []
    for item in raw_listings:
        credit = credits.get(item.get("credit_id"), {})
        project = projects.get(credit.get("project_id"), {})
        # Only show listing if project is approved
        if verification_status(project) != "approved":
            continue
        enriched.append({
            **item,
            "project_name": project.get("name", "Unknown Project"),
            "project_id": project.get("id"),
            "region": project.get("locality") or project.get("state"),
            "verification_status": verification_status(project),
        })
    return enriched


class ListingIn(BaseModel):
    credit_id: str
    quantity: float = Field(gt=0)
    price_per_credit: float = Field(gt=0)


@router.post("/marketplace/listings", status_code=201)
def create_listing(body: ListingIn, user=Depends(current_user)):
    credit = next((c for c in read_records("carbon_credits") if c["id"] == body.credit_id), None)
    if not credit or credit.get("owner_id") != user["id"]:
        raise HTTPException(404, "Eligible credit batch not found")

    projects = read_records("projects")
    project = next((p for p in projects if p["id"] == credit.get("project_id")), None)
    if not project or verification_status(project) != "approved":
        raise HTTPException(409, "Credits from unapproved projects cannot be listed")

    if credit.get("eligibility_status") != "eligible" or credit.get("verification_status") != "verified":
        raise HTTPException(409, "Credit batch is not eligible for sale")

    if body.quantity > credit.get("available_quantity", 0):
        raise HTTPException(409, "Insufficient available credits")

    # Prevent duplicate active listings for the exact same batch
    active_listings = [l for l in read_records("marketplace_listings") if l.get("status") == "active" and l.get("credit_id") == body.credit_id]
    if active_listings:
        raise HTTPException(409, "An active listing already exists for this credit batch")

    listing = {
        "id": str(uuid.uuid4()),
        "seller_id": user["id"],
        "credit_id": body.credit_id,
        "quantity": body.quantity,
        "remaining_quantity": body.quantity,
        "price_per_credit": body.price_per_credit,
        "status": "active",
        "created_at": now(),
    }
    append_record("marketplace_listings", listing)
    return listing


@router.post("/marketplace/listings/{listing_id}/purchase")
def purchase(listing_id: str, body: dict, user=Depends(current_user)):
    listings = read_records("marketplace_listings")
    listing = next((x for x in listings if x["id"] == listing_id), None)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing.get("status") != "active":
        raise HTTPException(409, "Listing is no longer active")
    if listing.get("seller_id") == user["id"]:
        raise HTTPException(409, "Cannot purchase own listing")

    credits = read_records("carbon_credits")
    credit = next((c for c in credits if c["id"] == listing.get("credit_id")), None)
    if not credit or credit.get("verification_status") != "verified":
        raise HTTPException(409, "Underlying carbon credits are not verified for purchase")

    projects = read_records("projects")
    project = next((p for p in projects if p["id"] == credit.get("project_id")), None)
    if not project or verification_status(project) != "approved":
        raise HTTPException(409, "Cannot purchase credits from an unapproved project")

    raise HTTPException(501, "Purchase transfers are not enabled until a durable transaction journal and payment confirmation flow are configured.")


@router.post("/marketplace/listings/{listing_id}/cancel")
def cancel(listing_id: str, user=Depends(current_user)):
    listings = read_records("marketplace_listings")
    listing = next((x for x in listings if x["id"] == listing_id), None)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not listing owner")
    listing["status"] = "cancelled"
    write_records("marketplace_listings", listings)
    return listing


@router.get("/transactions")
def transactions(user=Depends(current_user)):
    return [t for t in read_records("transactions") if user["role"] == "admin" or user["id"] in (t.get("buyer_id"), t.get("seller_id"))]
