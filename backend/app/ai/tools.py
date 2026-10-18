"""Care Navigator tools: real data, scoped to one patient.

patient_id is never exposed to the model: the agent injects it server-side, so the model cannot
read or book for another patient. Booking is NOT a tool: the agent can only propose times; the
patient books with a tap (POST /care-requests/{id}/book).
Declarations use FunctionDeclaration(parameters_json_schema=...).
"""
from datetime import date
from typing import Any, Callable
from uuid import UUID

from google.genai import types

from app import care, store
from app.ai import guidelines, memory


def today() -> date:
    return date.today()


def get_trends(patient_id: str, days: int = 7) -> list[dict]:
    """Daily points, oldest first: mood, pain, incision pain, sleep, headache, BP, mood check score."""
    days = max(1, min(int(days), 21))
    return [{k: (str(v) if k == "day" else v) for k, v in p.items()} for p in store.trends(UUID(patient_id), days)]


def search_guidelines(query: str) -> dict:
    """Trusted guidance with citations (Google Search limited to trusted health sites)."""
    return guidelines.ask(query)


def get_risk_tiers(patient_id: str) -> dict:
    from app.agents import watch

    r = watch.run(UUID(patient_id), persist=False)
    return {"overall": r["overall"], "tiers": r["tiers"]}


def recall_memory(patient_id: str, query: str) -> list[str]:
    return memory.recall(patient_id, query)


def find_nearby_care(patient_id: str, kind: str = "visit") -> list[dict]:
    """Nearest maternity care (kind = visit | emergency). Needs the patient's location."""
    prof = store.get_profile(UUID(patient_id)) or {}
    if prof.get("home_lat") is None:
        return [{"note": "No location saved. Ask them to add their ZIP code on the Care page."}]
    places = care.nearby(prof["home_lat"], prof["home_lon"], prof.get("postal_code"))
    pick = [care.nearest_er(places)] if kind == "emergency" else care.best_for_visit(places)
    return [{k: p[k] for k in ("name", "kind_label", "address", "phone", "distance_km")} for p in pick if p]


def get_open_care_request(patient_id: str) -> dict:
    """The visit the Watch/Booking agents proposed (times and places), if any."""
    r = store.open_care_request(UUID(patient_id))
    if not r:
        return {"open": False}
    return {"open": True, "tier": r["tier"], "reasons": r["reasons"], "slots": r["slots"],
            "places": [f["name"] for f in r["facilities"]], "how_to_book": "The patient taps a time on the Care page."}


TOOLS: dict[str, Callable[..., Any]] = {
    f.__name__: f for f in (get_trends, search_guidelines, get_risk_tiers, recall_memory, find_nearby_care,
                            get_open_care_request)
}
NEEDS_PATIENT = {"get_trends", "get_risk_tiers", "recall_memory", "find_nearby_care", "get_open_care_request"}


def _decl(name: str, description: str, properties: dict, required: list[str]) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=name, description=description,
        parameters_json_schema={"type": "object", "properties": properties, "required": required},
    )


DECLARATIONS = [
    _decl("get_trends", "Daily check-in and vitals trends for the current patient.",
          {"days": {"type": "integer", "description": "How many recent days, 1-21"}}, ["days"]),
    _decl("search_guidelines", "Search trusted postpartum guidance (CDC, NIH, WHO, ACOG...). Returns an answer with citations.",
          {"query": {"type": "string"}}, ["query"]),
    _decl("get_risk_tiers", "Current risk tier per category, with reasons and the REQUIRED next_step.", {}, []),
    _decl("recall_memory", "Recall what the patient said in past conversations.",
          {"query": {"type": "string"}}, ["query"]),
    _decl("find_nearby_care", "Nearest maternity care to the patient.",
          {"kind": {"type": "string", "enum": ["visit", "emergency"]}}, []),
    _decl("get_open_care_request", "The visit the care team agents already proposed (times, places), if any.", {}, []),
]
GEMINI_TOOL = types.Tool(function_declarations=DECLARATIONS)


def call_tool(name: str, args: dict, patient_id: str) -> Any:
    fn = TOOLS[name]
    args = dict(args or {})
    args.pop("patient_id", None)  # never trust a model-supplied patient id
    if name in NEEDS_PATIENT:
        args["patient_id"] = patient_id
    return fn(**args)
