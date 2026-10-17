"""Rule-based safety check. Runs BEFORE any AI call. Deterministic, no network.

If check() returns True, the caller must skip the agent and return URGENT_RESPONSE verbatim.
"""
import re
from typing import Optional

from app.schemas import CheckinMetrics

# TODO(clinical): teammate to verify these thresholds against ACOG / AWHONN POST-BIRTH guidance
# before demo. Placeholder values only.
BP_SYS_URGENT = 160  # TODO verify
BP_DIA_URGENT = 110  # TODO verify
BP_SYS_WARN = 140  # TODO verify (not yet used to trigger; Phase 1 "call your provider today" tier)
BP_DIA_WARN = 90  # TODO verify

URGENT_RESPONSE = (
    "What you just described can be a sign of a serious problem after birth, and it needs care right now. "
    "Please call 911 or go to the nearest emergency room. Tell them you recently gave birth. "
    "If you are thinking about harming yourself or your baby, you can also call or text 988 any time. "
    "You are not alone, and getting help right now is the right thing to do."
)

# (reason, patterns). Patterns are matched case-insensitively against the transcript.
RULES: list[tuple[str, list[str]]] = [
    ("thoughts of harming self or baby", [
        r"\b(hurt|harm|kill)(ing)?\s+(my\s?self|me|the baby|my baby|him|her)\b",
        r"\b(suicid\w*|end (my|it all)|don'?t want to (live|be alive|be here))\b",
        r"\bbetter off without me\b",
    ]),
    ("blurry or changed vision", [
        r"\b(blurr?y|blurred|double|spotty)\s+vision\b",
        r"\bvision\s+(is\s+)?(blurr?y|blurred|changed|changing|weird|off|going)\b",
        r"\b(seeing|see)\s+(spots|stars|flashing|flashes|sparkles)\b",
        r"\bcan'?t see (clearly|straight|properly)\b",
    ]),
    ("severe headache", [
        r"\b(severe|terrible|worst|awful|horrible|pounding|splitting|excruciating)\s+(\w+\s+)?headache\b",
        r"\bheadache\s+(that\s+)?(won'?t|will not|doesn'?t)\s+(go away|stop)\b",
        r"\bworst headache\b",
    ]),
    ("chest pain", [
        r"\bchest\s+(pain|pains|hurts|hurting|pressure|tightness|is tight)\b",
        r"\bpain\s+in\s+my\s+chest\b",
    ]),
    ("trouble breathing", [
        r"\b(trouble|difficulty|hard|struggling)\s+(time\s+)?breath(e|ing)\b",
        r"\bcan'?t\s+(catch my\s+)?breath(e)?\b",
        r"\bshort(ness)?\s+of\s+breath\b",
    ]),
    ("heavy bleeding", [
        r"\b(heavy|heavily|lots of|a lot of|soaking|gushing)\s+(\w+\s+)?(bleed\w*|blood)\b",
        r"\bsoak(ed|ing)?\s+(through\s+)?(a|one|my)?\s*pads?\b",
        r"\b(golf ball|egg|large|big)\s*-?(sized)?\s+clots?\b",
        r"\bbleeding\s+(a lot|heavily|through)\b",
    ]),
    ("seizure", [r"\bseizures?\b", r"\bconvuls\w*\b"]),
    ("fainting", [
        r"\b(faint|fainted|fainting|passed out|pass out|blacked out|lost consciousness)\b",
    ]),
]

_COMPILED = [(reason, [re.compile(p, re.IGNORECASE) for p in pats]) for reason, pats in RULES]


def check(transcript: str, metrics: Optional[CheckinMetrics] = None) -> tuple[bool, Optional[str]]:
    text = transcript or ""
    for reason, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            return True, reason

    if metrics is not None:
        if (metrics.bp_sys and metrics.bp_sys >= BP_SYS_URGENT) or (
            metrics.bp_dia and metrics.bp_dia >= BP_DIA_URGENT
        ):
            return True, f"severely high blood pressure ({metrics.bp_sys}/{metrics.bp_dia})"
        if metrics.bleeding == "heavy":
            return True, "heavy bleeding"
        if metrics.vision_change:
            return True, "blurry or changed vision"
    return False, None
