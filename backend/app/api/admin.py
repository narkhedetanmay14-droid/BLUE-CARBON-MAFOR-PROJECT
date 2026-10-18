from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from collections import defaultdict
from app.security.authentication import require_admin
from app.services.json_storage import read_records, write_records, append_record
from app.api.projects import project_response, verification_status

router = APIRouter(prefix="/admin", tags=["admin"])


def now():
    return datetime.now(timezone.utc).isoformat()


class ApprovalDecision(BaseModel):
    reason: str = Field(default="", max_length=2000)


class RejectionDecision(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


@router.get("/projects")
def all_projects(admin=Depends(require_admin)):
    return [project_response(project) for project in read_records("projects")]


def decide(project_id, status, body, admin):
    ps = read_records("projects")
    p = next((x for x in ps if x["id"] == project_id), None)
    if not p:
        raise HTTPException(404, "Project not found")
    if status == "approved" and verification_status(p) not in {"pending", "corrections_requested"}:
        raise HTTPException(409, "Only pending projects may be approved")
    if status in {"rejected", "corrections_requested"} and verification_status(p) == "approved":
        raise HTTPException(409, "Approved projects cannot be rejected without a correction workflow")
    p["verification_status"] = status
    p["status"] = "pending_review" if status == "corrections_requested" else status
    p["updated_at"] = now()
    write_records("projects", ps)

    rec = {
        "id": __import__("uuid").uuid4().hex,
        "project_id": project_id,
        "admin_id": admin["id"],
        "decision": status,
        "reason": body.reason,
        "created_at": now(),
    }
    append_record("verification_records", rec)
    append_record("audit_logs", {"event": "project_decision", **rec})
    append_record("notifications", {
        "id": __import__("uuid").uuid4().hex,
        "user_id": p["owner_id"],
        "message": f"Project {project_id}: {status}",
        "created_at": now(),
        "read": False,
    })
    return {"project": project_response(p), "verification": rec}


@router.post("/projects/{project_id}/approve")
def approve(project_id: str, body: ApprovalDecision, admin=Depends(require_admin)):
    return decide(project_id, "approved", body, admin)


@router.post("/projects/{project_id}/reject")
def reject(project_id: str, body: RejectionDecision, admin=Depends(require_admin)):
    return decide(project_id, "rejected", body, admin)


@router.post("/projects/{project_id}/request-corrections")
def corrections(project_id: str, body: RejectionDecision, admin=Depends(require_admin)):
    return decide(project_id, "corrections_requested", body, admin)


@router.get("/users")
def users(admin=Depends(require_admin)):
    users_list = read_records("users")
    projects = read_records("projects")
    out = []
    for u in users_list:
        u_projects = [p for p in projects if p.get("owner_id") == u["id"]]
        approved_count = sum(verification_status(p) == "approved" for p in u_projects)
        item = {k: v for k, v in u.items() if k != "password_hash"}
        item["approved_projects_count"] = approved_count
        item["total_projects_count"] = len(u_projects)
        out.append(item)
    return out


@router.get("/users/{user_id}/profile")
def admin_user_profile(user_id: str, admin=Depends(require_admin)):
    """Admin access to detailed user profile showing approved-project count, relevant projects, and approval timestamps."""
    users_list = read_records("users")
    user = next((u for u in users_list if u["id"] == user_id), None)
    if not user:
        raise HTTPException(404, "User not found")

    projects = read_records("projects")
    user_projects = [p for p in projects if p.get("owner_id") == user_id]
    verif_records = read_records("verification_records")

    approved_projects = []
    for p in user_projects:
        if verification_status(p) == "approved":
            # Retrieve actual approval timestamp from authoritative verification_records
            p_verifs = [v for v in verif_records if v.get("project_id") == p["id"] and v.get("decision") == "approved"]
            approval_time = p_verifs[-1].get("created_at") if p_verifs else p.get("updated_at")

            approved_projects.append({
                "project_id": p["id"],
                "name": p.get("name"),
                "ecosystem_type": p.get("ecosystem_type"),
                "area_hectares": p.get("area_hectares", 0),
                "location": {
                    "country": p.get("country"),
                    "state": p.get("state"),
                    "locality": p.get("locality"),
                    "reference_region": p.get("reference_region"),
                },
                "approval_timestamp": approval_time,
                "current_status": "approved",
            })

    return {
        "user": {k: v for k, v in user.items() if k != "password_hash"},
        "approved_project_count": len(approved_projects),
        "approved_projects": approved_projects,
        "total_approved_area_hectares": round(sum(p.get("area_hectares", 0) for p in approved_projects), 4),
    }


@router.get("/audit-logs")
def audit_logs(
    status: str | None = Query(default=None),
    event: str | None = Query(default=None),
    admin=Depends(require_admin),
):
    """Admin review history for approved, rejected, and under-review projects with actual timestamps."""
    logs = read_records("audit_logs")
    projects = {p["id"]: p for p in read_records("projects")}
    users_map = {u["id"]: u for u in read_records("users")}

    enriched = []
    for item in logs:
        pid = item.get("project_id")
        proj = projects.get(pid) if pid else None
        admin_user = users_map.get(item.get("admin_id"), {})

        decision_status = item.get("decision") or item.get("status") or (
            "pending_review" if item.get("event") == "project_resubmitted" else None
        )

        # Status filtering
        if status and status.lower() not in {"all", ""}:
            if (decision_status or "").lower() != status.lower():
                continue

        # Event filtering
        if event and event.lower() not in {"all", ""}:
            if (item.get("event") or "").lower() != event.lower():
                continue

        enriched.append({
            **item,
            "project_name": proj.get("name") if proj else "Unknown or Deleted Project",
            "status": decision_status,
            "review_timestamp": item.get("created_at"),
            "reviewer_name": admin_user.get("display_name") or admin_user.get("username") or "System",
        })
    return enriched


def credit_usage(project_id: str, transactions: list[dict]) -> tuple[float, bool]:
    """Sum only explicit persisted credit-use ledger events."""
    used = 0.0
    usage_events = {"used", "use", "retired", "retire", "burned", "burn"}
    amount_keys = ("credits_used", "used_quantity", "quantity_used", "quantity", "amount")
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


@router.get("/analysis")
def approved_project_analysis(admin=Depends(require_admin)):
    """Administrative analysis strictly contains only approved projects.

    Includes supported project details, regional holdings, user balances, and project-level totals.
    """
    users_map = {user["id"]: user for user in read_records("users")}
    transactions = read_records("transactions")
    carbon_credits = read_records("carbon_credits")

    rows = []
    regional_counts = defaultdict(lambda: {"project_count": 0, "total_area_hectares": 0.0})

    for project in read_records("projects"):
        if verification_status(project) != "approved":
            continue

        usage, usage_available = credit_usage(project["id"], transactions)
        owner = users_map.get(project.get("owner_id"), {})
        item = project_response(project)

        # Calculate project-specific user credit balance
        proj_credits = [c for c in carbon_credits if c.get("project_id") == project["id"] and c.get("owner_id") == project.get("owner_id")]
        allocated_credits = sum(float(c.get("total_quantity") or c.get("available_quantity") or 0.0) for c in proj_credits)
        remaining_credits = max(0.0, allocated_credits - (usage if usage_available else 0.0))

        # Track regional holdings
        region_key = (
            project.get("reference_region", {}).get("district")
            if project.get("reference_region")
            else (project.get("locality") or project.get("state") or "Other")
        )
        regional_counts[region_key]["project_count"] += 1
        regional_counts[region_key]["total_area_hectares"] = round(
            regional_counts[region_key]["total_area_hectares"] + float(project.get("area_hectares") or 0.0), 4
        )

        rows.append({
            "project": item,
            "project_id": item["id"],
            "project_name": item["name"],
            "ecosystem_type": item.get("ecosystem_type"),
            "area_hectares": item.get("area_hectares"),
            "owner": {
                "id": owner.get("id"),
                "username": owner.get("username"),
                "display_name": owner.get("display_name"),
            },
            "location": {
                "country": item.get("country"),
                "state": item.get("state"),
                "locality": item.get("locality"),
                "reference_region": item.get("reference_region"),
            },
            "regional_holding": region_key,
            "verification_status": item["verification_status"],
            "carbon_credit_usage": usage if usage_available else None,
            "carbon_credit_usage_status": "available" if usage_available else "not_available",
            "user_balance": {
                "allocated": round(allocated_credits, 2),
                "used": round(usage if usage_available else 0.0, 2),
                "remaining": round(remaining_credits, 2),
                "units": "tCO2e",
            },
        })

    return rows


@router.get("/analysis/summary")
def approved_project_summary(admin=Depends(require_admin)):
    """Aggregate totals and regional holdings reconciled across all approved projects."""
    rows = approved_project_analysis(admin=admin)
    total_area = round(sum(r["area_hectares"] or 0 for r in rows), 4)
    total_credits_used = sum(r["carbon_credit_usage"] or 0 for r in rows if r["carbon_credit_usage_status"] == "available")
    total_credits_allocated = sum(r["user_balance"]["allocated"] for r in rows)

    regional_holdings = defaultdict(lambda: {"project_count": 0, "total_area_hectares": 0.0})
    for r in rows:
        reg = r["regional_holding"]
        regional_holdings[reg]["project_count"] += 1
        regional_holdings[reg]["total_area_hectares"] = round(
            regional_holdings[reg]["total_area_hectares"] + (r["area_hectares"] or 0), 4
        )

    return {
        "total_approved_projects": len(rows),
        "total_approved_area_hectares": total_area,
        "total_carbon_credits_allocated": round(total_credits_allocated, 2),
        "total_carbon_credits_used": round(total_credits_used, 2),
        "regional_holdings": dict(regional_holdings),
    }
