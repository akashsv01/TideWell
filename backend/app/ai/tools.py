"""Care Navigator tools. PHASE 1: FAKE DATA for patient "maya" only, shaped like app/schemas.py.
Phase 3 swaps each body for the real thing (Tiger SQL, pgvector RAG, risk engine, Backboard, clinic).

patient_id is never exposed to the model: the agent injects it server-side, so the model cannot
read or book for a different patient. Declarations use FunctionDeclaration(parameters_json_schema=...).
"""
from datetime import date, datetime, timedelta
from typing import Any, Callable

from google.genai import types

from app.schemas import CategoryTier, TrendPoint

TODAY = date(2026, 10, 17)


def get_trends(patient_id: str, days: int = 7) -> list[dict]:
    """Daily points, oldest first. Maya: BP rising 132/84 -> 144/92 over the last 4 readings,
    sleep ~3.8 h, headaches on 3 of the last 7 days."""
    days = max(1, min(int(days), 21))
    bp = {3: (132, 84), 2: (136, 88), 1: (141, 90), 0: (144, 92)}
    headache_days = {0, 2, 4}
    points = []
    for ago in range(days - 1, -1, -1):
        sys_, dia = bp.get(ago, (126, 80))
        p = TrendPoint(
            day=TODAY - timedelta(days=ago), mood=5 if ago < 4 else 6, pain=3,
            sleep_hrs=[3.5, 4.0, 3.8, 3.6, 4.1, 3.9, 3.7][ago % 7], bp_sys=sys_, bp_dia=dia,
        ).model_dump(mode="json")
        p["headache"] = ago in headache_days
        points.append(p)
    return points


def search_guidelines(query: str, k: int = 3) -> list[dict]:
    """Top-k guideline chunks: {source, url, section, content} (same keys as clinical_assets/guidelines.json
    and the guideline_chunks table). Phase 3: pgvector cosine search over guideline_chunks."""
    chunks = [
        {
            "source": "CDC Hear Her",
            "url": "https://www.cdc.gov/hearher/maternal-warning-signs/index.html",
            "section": "Urgent maternal warning signs",
            "content": "A headache that won't go away or gets worse over time, and changes in vision, can be warning "
                    "signs up to a year after delivery. Get medical care right away if you have these.",
        },
        {
            "source": "CDC",
            "url": "https://www.cdc.gov/maternal-infant-health/postpartum/index.html",
            "section": "High blood pressure after pregnancy",
            "content": "High blood pressure can develop or get worse after birth. Regular blood pressure checks after "
                    "delivery help catch it early; talk with your provider if readings are rising.",
        },
        {
            "source": "NIH",
            "url": "https://www.nichd.nih.gov/health/topics/postpartum",
            "section": "Sleep and mood after birth",
            "content": "Very little sleep can affect mood after birth. Ongoing low mood, worry, or trouble sleeping even "
                    "when the baby sleeps are worth raising with a health care provider.",
        },
    ]
    return chunks[: max(1, min(int(k), len(chunks)))]


def get_risk_tiers(patient_id: str) -> list[dict]:
    tiers = [
        CategoryTier(category="high_blood_pressure", tier="amber",
                     reasons=["BP rose 4 readings in a row (132/84 to 144/92)", "headaches 3 of last 7 days",
                              "history of gestational hypertension"],
                     next_step="Offer a blood pressure check visit within 1-3 days"),
        CategoryTier(category="depression_anxiety", tier="watch",
                     reasons=["EPDS rose from 7 to 11", "average sleep 3.8 hours", "history of depression"],
                     next_step="Repeat mood screen in 3 days and share support resources"),
        CategoryTier(category="post_cesarean", tier="green", reasons=["incision pain stable at 3"],
                     next_step="Routine daily check-in"),
    ]
    return [t.model_dump() for t in tiers]


def recall_memory(patient_id: str, query: str) -> list[str]:
    """Phase 3: memory.recall(patient_id, query) (Backboard search_memories)."""
    return [
        "Maya had a C-section at 38 weeks on 2026-09-29.",
        "She mentioned a headache on Tuesday and again on Thursday.",
        "She is breastfeeding and says nights are the hardest.",
        "Her support person is her sister, Priya.",
    ]


def get_slots(urgency: str = "amber") -> list[dict]:
    """Open times at the default clinic (in person): {"slot": ISO datetime, "label": spoken form}.
    The label stops the model from guessing weekdays from an ISO string."""
    from app import booking

    urgency = urgency if urgency in ("watch", "amber", "routine") else "amber"
    out = []
    for t in booking.open_slots(booking.DEFAULT_PROVIDER_ID, "in_person", urgency)[:3]:
        label = t.strftime("%A %B %d at %I %p").replace(" 0", " ")
        out.append({"slot": t.isoformat(), "label": label})
    return out


def book_appointment(patient_id: str, slot: str, reason: str) -> dict:
    """Books at the default clinic, in person. Returns the same keys as before plus the clinic."""
    from uuid import UUID

    from app import booking

    try:
        v = booking.book(UUID(patient_id), None, datetime.fromisoformat(slot), "in_person", reason, "amber")
    except (booking.BookingError, ValueError) as e:
        return {"status": "failed", "error": getattr(e, "message", str(e))}
    return {"appointment_id": str(v["appointment_id"]), "status": "booked", "slot": slot, "reason": reason,
            "clinic": v["provider"]["clinic"], "provider": v["provider"]["name"]}


# --- Registry + Gemini declarations -------------------------------------------------
TOOLS: dict[str, Callable[..., Any]] = {
    f.__name__: f for f in (get_trends, search_guidelines, get_risk_tiers, recall_memory, get_slots, book_appointment)
}
NEEDS_PATIENT = {"get_trends", "get_risk_tiers", "recall_memory", "book_appointment"}


def _decl(name: str, description: str, properties: dict, required: list[str]) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=name, description=description,
        parameters_json_schema={"type": "object", "properties": properties, "required": required},
    )


DECLARATIONS = [
    _decl("get_trends", "Daily check-in and vitals trends for the current patient (mood, pain, sleep, BP, headaches).",
          {"days": {"type": "integer", "description": "How many recent days, 1-21"}}, ["days"]),
    _decl("search_guidelines", "Search trusted postpartum guidelines (CDC, NIH, WHO). Returns cited text chunks.",
          {"query": {"type": "string"}, "k": {"type": "integer", "description": "Number of chunks, 1-3"}}, ["query"]),
    _decl("get_risk_tiers", "Current risk tier per clinical category, with reasons and the REQUIRED next_step.", {}, []),
    _decl("recall_memory", "Recall what the patient said in past conversations.",
          {"query": {"type": "string", "description": "What to look for"}}, ["query"]),
    _decl("get_slots", "Available appointment times in the next 3 days. Say them to the patient using 'label'.",
          {"urgency": {"type": "string", "enum": ["watch", "amber"]}}, []),
    _decl("book_appointment", "Book an appointment. Only call after the patient clearly said yes to a specific slot.",
          {"slot": {"type": "string", "description": "ISO datetime from get_slots"},
           "reason": {"type": "string"}}, ["slot", "reason"]),
]
GEMINI_TOOL = types.Tool(function_declarations=DECLARATIONS)


def call_tool(name: str, args: dict, patient_id: str) -> Any:
    fn = TOOLS[name]
    args = dict(args or {})
    args.pop("patient_id", None)  # never trust a model-supplied patient id
    if name in NEEDS_PATIENT:
        args["patient_id"] = patient_id
    return fn(**args)
