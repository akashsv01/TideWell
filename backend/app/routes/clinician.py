"""GET /clinician/patients: patients sorted Red > Amber > Watch > Green."""
from collections import defaultdict

from fastapi import APIRouter, Query

from app import db, demo_data, store
from app.schemas_data import ClinicianPatient

router = APIRouter()
_RANK = {"red": 3, "amber": 2, "watch": 1, "green": 0}


def _roll_up(rows: list[dict]) -> list[ClinicianPatient]:
    by_patient: dict = defaultdict(list)
    for r in rows:
        by_patient[r["patient_id"]].append(r)
    out = []
    for pid, rs in by_patient.items():
        overall = max((r["tier"] for r in rs), key=lambda t: _RANK.get(t, 0))
        reasons = [f"{r['category']}: {x}" for r in rs if r["tier"] != "green" for x in (r["reasons"] or [])]
        out.append(ClinicianPatient(
            patient_id=pid, name=rs[0]["name"], overall_tier=overall, reasons=reasons,
            categories={r["category"]: r["tier"] for r in rs}, synthetic=bool(rs[0].get("is_synthetic")),
        ))
    out.sort(key=lambda p: (-_RANK[p.overall_tier], p.name or ""))
    return out


@router.get("/clinician/patients", response_model=list[ClinicianPatient])
def patients(limit: int = Query(200, ge=1, le=1000)) -> list[ClinicianPatient]:
    if db.enabled():
        rows = store.latest_risk_rows()
    else:
        rows = [{"patient_id": demo_data.MAYA_ID, "name": "Maya", "is_synthetic": False, **r}
                for r in demo_data.risk_assessments()]
    return _roll_up(rows)[:limit]
