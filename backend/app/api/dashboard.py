from fastapi import APIRouter, Depends
from app.security.authentication import current_user, require_admin
from app.services.json_storage import read_records
from app.api.projects import verification_status

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def calculate_user_allocations_and_balance(user_id: str) -> dict:
    projects = [p for p in read_records("projects") if p.get("owner_id") == user_id]
    all_credits = [c for c in read_records("carbon_credits") if c.get("owner_id") == user_id]
    all_transactions = read_records("transactions")

    deduction_events = {"used", "use", "retired", "retire", "burned", "burn", "transferred", "transfer", "reserved", "reservation"}
    amount_keys = ("credits_used", "used_quantity", "quantity_used", "quantity", "amount")

    allocations = []
    total_allocated = 0.0
    total_deductions = 0.0
    total_remaining = 0.0

    project_map = {p["id"]: p for p in projects}
    for c in all_credits:
        pid = c.get("project_id")
        if pid and pid not in project_map:
            p_rec = next((p for p in read_records("projects") if p["id"] == pid), None)
            if p_rec:
                project_map[pid] = p_rec

    for pid, p in project_map.items():
        proj_credits = [c for c in all_credits if c.get("project_id") == pid]
        proj_allocated = 0.0
        for c in proj_credits:
            try:
                qty = float(c.get("total_quantity") or c.get("available_quantity") or 0.0)
                if qty > 0:
                    proj_allocated += qty
            except (ValueError, TypeError):
                continue

        proj_deductions = 0.0
        for t in all_transactions:
            if t.get("project_id") == pid and t.get("seller_id") == user_id:
                event = str(t.get("event") or t.get("type") or t.get("action") or "").casefold()
                if event in deduction_events:
                    raw_amt = next((t[k] for k in amount_keys if k in t), 0.0)
                    try:
                        amt = float(raw_amt)
                        if amt > 0:
                            proj_deductions += amt
                    except (ValueError, TypeError):
                        continue

        # Prevent negative balances
        proj_remaining = max(0.0, round(proj_allocated - proj_deductions, 4))
        total_allocated += proj_allocated
        total_deductions += proj_deductions
        total_remaining += proj_remaining

        allocations.append({
            "project_id": pid,
            "project_name": p.get("name", "Unnamed Project"),
            "verification_status": verification_status(p),
            "allocated": round(proj_allocated, 4),
            "consumed": round(proj_deductions, 4),
            "remaining": proj_remaining,
            "units": "tCO2e",
        })

    has_records = len(all_credits) > 0
    return {
        "allocations": allocations,
        "total_allocated": round(total_allocated, 4),
        "total_deductions": round(total_deductions, 4),
        "remaining_balance": round(total_remaining, 4) if has_records else None,
        "balance": round(total_remaining, 4) if has_records else "Not recorded",
        "units": "tCO2e",
        "ledger_status": "authoritative_records_present" if has_records else "not_recorded",
        "has_authoritative_records": has_records,
    }


@router.get("/user")
def user_dashboard(user=Depends(current_user)):
    ps = [p for p in read_records("projects") if p["owner_id"] == user["id"]]
    ass = [a for a in read_records("assessments") if any(p["id"] == a["project_id"] for p in ps)]
    balance_info = calculate_user_allocations_and_balance(user["id"])

    return {
        "user": user,
        "total_projects": len(ps),
        "pending_projects": sum(verification_status(p) == "pending" for p in ps),
        "approved_projects": sum(verification_status(p) == "approved" for p in ps),
        "rejected_projects": sum(verification_status(p) == "rejected" for p in ps),
        "corrections_requested_projects": sum(verification_status(p) == "corrections_requested" for p in ps),
        "total_area_hectares": round(sum(p.get("area_hectares", 0) for p in ps), 4),
        "latest_assessments": ass[-5:],
        "credits": balance_info["remaining_balance"],
        "available_credits": balance_info["remaining_balance"],
        "balance": balance_info["balance"],
        "allocations": balance_info["allocations"],
        "total_allocated": balance_info["total_allocated"],
        "total_deductions": balance_info["total_deductions"],
        "ledger_status": balance_info["ledger_status"],
        "units": balance_info["units"],
        "notifications": [n for n in read_records("notifications") if n.get("user_id") == user["id"]][-10:],
    }


@router.get("/admin")
def admin_dashboard(admin=Depends(require_admin)):
    ps = read_records("projects")
    return {
        "users": len(read_records("users")),
        "projects": len(ps),
        "pending_reviews": sum(verification_status(p) == "pending" for p in ps),
        "approved_projects": sum(verification_status(p) == "approved" for p in ps),
        "rejected_projects": sum(verification_status(p) == "rejected" for p in ps),
        "total_area_hectares": round(sum(p.get("area_hectares", 0) for p in ps), 4),
        "assessments": len(read_records("assessments")),
        "listings": len([x for x in read_records("marketplace_listings") if x.get("status") == "active"]),
    }
