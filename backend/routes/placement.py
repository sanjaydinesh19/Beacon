import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent / "data"
COMPANIES_FILE = DATA_DIR / "companies.json"
TRACKER_FILE = DATA_DIR / "tracker.json"


def _load_companies() -> dict:
    return json.loads(COMPANIES_FILE.read_text())


def _load_tracker() -> dict:
    return json.loads(TRACKER_FILE.read_text())


def _save_tracker(data: dict):
    TRACKER_FILE.write_text(json.dumps(data, indent=2))


# ── Companies ────────────────────────────────────────────────────────────────

@router.get("/companies")
def get_companies(tier: str = "", domain: str = "", q: str = ""):
    data = _load_companies()
    companies = data["companies"]

    if tier:
        tiers = [t.strip() for t in tier.split(",") if t.strip()]
        companies = [c for c in companies if c.get("tier") in tiers]
    if domain:
        companies = [c for c in companies if domain.lower() in [d.lower() for d in c.get("domain", [])]]
    if q:
        ql = q.lower()
        companies = [c for c in companies if ql in c["name"].lower() or any(ql in r.lower() for r in c.get("roles", []))]

    return {"companies": companies, "total": len(companies)}


# ── Tracker ──────────────────────────────────────────────────────────────────

VALID_STATUSES = {"watchlist", "researching", "preparing", "ready", "applied", "interviewed", "offered", "rejected"}


class TrackerUpdate(BaseModel):
    status: str
    notes: str = ""
    links: list[str] = []


@router.get("/tracker")
def get_tracker():
    return _load_tracker()


@router.put("/tracker/{company_id}")
def update_tracker(company_id: str, body: TrackerUpdate):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")

    data = _load_companies()
    ids = {c["id"] for c in data["companies"]}
    if company_id not in ids:
        raise HTTPException(status_code=404, detail="Company not found")

    tracker = _load_tracker()
    if company_id not in tracker["companies"]:
        tracker["companies"][company_id] = {"addedAt": datetime.now(timezone.utc).date().isoformat()}

    tracker["companies"][company_id].update({
        "status": body.status,
        "notes": body.notes,
        "links": body.links,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })
    _save_tracker(tracker)
    return tracker["companies"][company_id]


@router.delete("/tracker/{company_id}")
def remove_tracker(company_id: str):
    tracker = _load_tracker()
    if company_id not in tracker["companies"]:
        raise HTTPException(status_code=404, detail="Not in tracker")
    del tracker["companies"][company_id]
    _save_tracker(tracker)
    return {"ok": True}


# ── Manual triggers ───────────────────────────────────────────────────────────

@router.post("/backup/trigger")
async def trigger_backup():
    from scheduler import auto_backup
    await auto_backup()
    return {"ok": True, "job": "backup_tracker"}


@router.post("/lc/trigger")
async def trigger_lc():
    from scheduler import generate_daily_lc
    await generate_daily_lc()
    return {"ok": True, "job": "lc_daily"}
