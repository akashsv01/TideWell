"""Red-flag safety check. Runs BEFORE the agent; the agent never makes the safety decision.

Two layers, combined as rules OR gemini:
  1. check_rules(): deterministic regex rules, no network. Always runs.
  2. gemini_flag(): Gemini backup for phrasing the rules miss. Runs only when the rules found
     nothing, can only RAISE a flag, and any error/timeout (3 s) counts as "no extra flag".
Policy: over-flagging is acceptable; missing a real danger sign is not. When in doubt, flag.

If check().flag is True, the caller skips the agent and returns URGENT_RESPONSE verbatim.
Gemini API used (see extract.py header): models.generate_content with response_schema;
the 3 s cap is enforced client-side with a future timeout, because the API rejects
request deadlines under 10 s ("Minimum allowed deadline is 10s").
"""
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel

from app.config import get_settings
from app.schemas import CheckinMetrics

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TODO(clinical): P4 is verifying these against ACOG / CDC. PLACEHOLDER VALUES, do not ship as-is.
SEVERE_BP_SYS = 160  # TODO verify: systolic at/above this is a red flag
SEVERE_BP_DIA = 110  # TODO verify: diastolic at/above this is a red flag
SEVERE_PAIN = 7  # TODO verify: pain score (0-10) that counts as "severe" when combined with fever
# ---------------------------------------------------------------------------

GEMINI_TIMEOUT_S = 3
NEGATION_WINDOW = 3  # words checked before a match ("no blurry vision", "haven't had any spots")

URGENT_RESPONSE = (
    "What you just described can be a sign of a serious problem after birth, and it needs care right now. "
    "Please call 911 or go to the nearest emergency room. Tell them you recently gave birth. "
    "If you are thinking about harming yourself or your baby, you can also call or text 988 any time. "
    "You are not alone, and getting help right now is the right thing to do."
)


@dataclass(frozen=True)
class RedFlagResult:
    flag: bool
    reason: Optional[str] = None
    source: Optional[Literal["rules", "gemini"]] = None


SAFE = RedFlagResult(False)

# --- Negation ----------------------------------------------------------------
# A negator shortly BEFORE the term ("no blurry vision"), or a resolver shortly AFTER it
# ("the spots went away"), cancels that one match. Clause punctuation and contrast words
# ("but", "now") reset the window, so "it was better, but now I'm seeing spots" still flags.
_NEGATORS = {
    "no", "not", "never", "without", "none", "nor", "zero",
    "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't", "didn't", "haven't", "hasn't", "hadn't",
}
_CONTRAST = {"but", "though", "although", "however", "except", "now", "until", "yet", "still"}
_RESOLVED_AFTER = re.compile(
    r"^\W*(\w+\W+){0,3}?(is |are |has |have |had |finally |completely |totally )*"
    r"(gone|went away|stopped|cleared( up)?|resolved|disappeared|over)\b",
    re.IGNORECASE,
)
_CLAUSE_BREAK = re.compile(r"[.,;!?]")


def _negated(text: str, start: int, end: int) -> bool:
    before = _CLAUSE_BREAK.split(text[:start])[-1].lower().split()
    window = before[-NEGATION_WINDOW:]
    for i in range(len(window) - 1, -1, -1):  # ignore anything before the last contrast word
        if window[i] in _CONTRAST:
            window = window[i + 1:]
            break
    if any(w in _NEGATORS for w in window):
        return True
    after = _CLAUSE_BREAK.split(text[end:])[0]
    return bool(_RESOLVED_AFTER.match(after))


# --- Rules -------------------------------------------------------------------
# (reason, patterns, negatable). Self-harm is never negatable: "I'd never hurt my baby" still
# flags, by design, because a missed self-harm signal is the worst failure.
_W = r"(?:\w+\s+)"  # one filler word
RULES: list[tuple[str, list[str], bool]] = [
    ("thoughts of harming self or baby", [
        r"\b(hurt|harm|kill|cut)(ing|s)?\s+myself\b",
        r"\b(hurt|harm|kill|shake|shaking|smother|drown)(ing|s)?\s+(the|my|our)\s+(baby|son|daughter|newborn)\b",
        r"\b(thoughts?|thinking|thought)\s+(of|about)\s+(hurting|harming|killing)\b",
        r"\bsuicid\w*",
        r"\bend\s+(it|it all|my life|things)\b",
        r"\b(don'?t|do not)\s+want\s+to\s+(be here|be alive|live|exist|wake up)( anymore)?\b",
        r"\bwant(ed)?\s+to\s+die\b",
        r"\bbetter\s+off\s+without\s+me\b",
        r"\bwish\s+i\s+(was|were|wasn'?t|weren'?t)\s+(dead|gone|here|alive|born)\b",
        r"\b(no|not any)\s+reason\s+to\s+(live|keep going)\b",
        r"\bcan'?t\s+go\s+on\b",
    ], False),
    ("blurry or changed vision", [
        r"\b(blurry|blurred|blurriness|blurring|fuzzy|hazy)\b",
        r"\b(seeing|see|saw|seen)\s+(spots|stars|double|flashes|sparkles|floaters|flashing)\b",
        r"\bflash(ing|es)?\s+(of\s+)?lights?\b",
        r"\bdouble\s+vision\b",
        r"\bspots\s+in\s+(my\s+)?(eyes?|vision)\b",
        r"\bcan'?t\s+see\s+(properly|clearly|straight|well|right)\b",
        r"\bvision\s+(is\s+|has\s+been\s+|went\s+|keeps\s+|seems\s+)?(off|weird|strange|dim|dark|changed|changing|wrong|funny|going)\b",
        r"\blos(t|ing)\s+(my\s+)?(vision|sight)\b",
    ], True),
    ("severe headache", [
        r"\bworst\s+headache\b",
        rf"\b(severe|terrible|awful|horrible|pounding|splitting|excruciating|unbearable|intense|crushing|blinding|massive)\s+{_W}?headaches?\b",
        r"\b(really|super|so|very)\s+bad\s+headaches?\b",
        r"\bhead\s+(is\s+)?(killing me|pounding|splitting|exploding)\b",
        r"\bheadaches?\b[^.]{0,60}\b(won'?t|will not|doesn'?t|does not|isn'?t|not)\s+(go(ing)?\s+away|stop|help(ing)?|budge|work(ing)?)\b",
        r"\bheadaches?\b[^.]{0,60}\b(even\s+(with|after)|despite)\s+(the\s+)?(medicine|meds|tylenol|ibuprofen|advil|motrin|painkillers?|pain\s+meds)\b",
        r"\b(medicine|meds|tylenol|ibuprofen|advil|motrin|painkillers?)\b[^.]{0,40}\b(didn'?t|doesn'?t|isn'?t|not|hasn'?t|won'?t)\s+(help|helping|helped|work|working|touch)\b[^.]{0,40}\bhead",
    ], True),
    ("chest pain or trouble breathing", [
        r"\bchest\s+(pains?|hurts?|hurting|pressure|tightness|is\s+tight|feels\s+tight|feels\s+heavy|is\s+heavy)\b",
        r"\bpain\s+in\s+(my\s+)?chest\b",
        r"\btight(ness)?\s+in\s+(my\s+)?chest\b",
        rf"\b(trouble|difficulty|hard|struggling|struggle|hard\s+time)\s+{_W}{{0,2}}breath(e|ing)\b",
        r"\bcan'?t\s+(catch\s+my\s+)?breathe?\b",
        r"\bcan'?t\s+get\s+(enough\s+)?air\b",
        r"\bshort(ness)?\s+of\s+breath\b",
        r"\b(gasping|breathless|winded)\b",
    ], True),
    ("heavy bleeding", [
        r"\bsoak(ed|ing|s)?\s+(through\s+)?(a\s+|one\s+|my\s+|the\s+|two\s+)?(\w+\s+)?pads?\b",
        r"\bpads?\b[^.]{0,30}\b(every|in\s+an?|within\s+an?|each)\s+(hour|half\s+hour)\b",
        r"\b(large|big|huge|giant|golf\s*-?\s*ball|egg|plum|lemon)\s*-?\s*(sized\s+)?clots?\b",
        r"\bclots?\s+(the\s+size\s+of|as\s+big\s+as|bigger\s+than)\b",
        r"\bbleeding\s+(a\s+lot|so\s+much|heavily|really\s+heavy|like\s+crazy|through|non-?stop|more\s+and\s+more)\b",
        rf"\b(heavy|heavier|lots\s+of|a\s+lot\s+of|so\s+much|tons\s+of|gushing|pouring)\s+{_W}?(bleeding|blood)\b",
        r"\bblood\s+(is\s+)?(gushing|pouring|everywhere)\b",
        r"\bhemorrhag\w*",
    ], True),
    ("seizure", [r"\bseizures?\b", r"\bconvuls\w*", r"\bhad\s+a\s+fit\b"], True),
    ("fainting or passing out", [
        r"\b(faint|fainted|fainting|faints)\b",
        r"\b(pass|passed|passing)\s+out\b",
        r"\b(black|blacked|blacking)\s+out\b",
        r"\blost\s+consciousness\b",
        r"\bcollapsed\b",
    ], True),
    ("swollen, red or painful leg", [
        r"\b(swollen|swelling|red|hot|warm|painful)\b[^.]{0,25}\b(leg|calf|calves|thigh)\b",
        r"\b(leg|calf|calves|thigh)\b[^.]{0,25}\b(swollen|swelling|red|hot|warm to the touch)\b",
    ], True),
]
_COMPILED = [(r, [re.compile(p, re.IGNORECASE) for p in ps], n) for r, ps, n in RULES]

# Fever + severe pain only flags in combination.
_FEVER = re.compile(r"\b(fever|feverish|temperature\s+of\s+10[0-5]|10[0-5](\.\d)?\s*degrees|chills)\b", re.I)
_SEVERE_PAIN = re.compile(
    r"\b((severe|terrible|awful|horrible|unbearable|excruciating|intense|really\s+bad|so\s+much)\s+(\w+\s+)?pain"
    r"|pain\b[^.]{0,30}\b(is|at|like|about|around)\s+(like\s+|about\s+|an?\s+)*(7|8|9|10|seven|eight|nine|ten)\b"
    r"|(incision|belly|stomach|breast)\b[^.]{0,20}\b(killing me|unbearable|so painful))",
    re.I,
)


def _find(pattern: re.Pattern, text: str, negatable: bool) -> bool:
    return any(not (negatable and _negated(text, m.start(), m.end())) for m in pattern.finditer(text))


def _normalize(text: str) -> str:
    return (text or "").replace("’", "'").replace("‘", "'")


def check_rules(transcript: str, metrics: Optional[CheckinMetrics] = None) -> RedFlagResult:
    text = _normalize(transcript)
    for reason, patterns, negatable in _COMPILED:
        if any(_find(p, text, negatable) for p in patterns):
            return RedFlagResult(True, reason, "rules")

    if _find(_FEVER, text, True) and _find(_SEVERE_PAIN, text, True):
        return RedFlagResult(True, "fever with severe pain", "rules")

    if metrics is not None:
        if (metrics.bp_sys or 0) >= SEVERE_BP_SYS or (metrics.bp_dia or 0) >= SEVERE_BP_DIA:
            return RedFlagResult(True, f"severely high blood pressure ({metrics.bp_sys}/{metrics.bp_dia})", "rules")
        if metrics.bleeding == "heavy":
            return RedFlagResult(True, "heavy bleeding", "rules")
        if metrics.vision_change:
            return RedFlagResult(True, "blurry or changed vision", "rules")
        if metrics.fever and max(metrics.pain or 0, metrics.incision_pain or 0) >= SEVERE_PAIN:
            return RedFlagResult(True, "fever with severe pain", "rules")
    return SAFE


# --- Gemini backup -----------------------------------------------------------
class _GeminiVerdict(BaseModel):
    urgent: bool = False
    reason: Optional[str] = None


_GEMINI_PROMPT = (
    "You are a safety screener for a postpartum check-in app. You do not diagnose. "
    "Decide if the parent's words describe ANY urgent maternal warning sign, even if phrased indirectly or "
    "casually: thoughts of harming themself or the baby or not wanting to live; vision changes; severe or "
    "persistent headache; chest pain or trouble breathing; heavy bleeding or large clots; seizure; fainting; "
    "fever with severe pain; a swollen, red or painful leg; sudden severe swelling of face or hands; "
    "extreme confusion. Ignore symptoms the person says are absent or resolved. If you are unsure, answer "
    "urgent=true. reason is a short plain phrase naming the sign, or null."
)
_pool = ThreadPoolExecutor(max_workers=4)


def _gemini_call(transcript: str) -> _GeminiVerdict:
    from google.genai import types

    from app.ai._gemini import get_client

    r = get_client().models.generate_content(
        model=get_settings().gemini_fast_model,
        contents=transcript,
        config=types.GenerateContentConfig(
            system_instruction=_GEMINI_PROMPT,
            response_mime_type="application/json",
            response_schema=_GeminiVerdict,
            temperature=0,
        ),
    )
    if isinstance(r.parsed, _GeminiVerdict):
        return r.parsed
    return _GeminiVerdict.model_validate_json(r.text or "{}")


def gemini_flag(transcript: str) -> tuple[bool, Optional[str]]:
    """Backup screen. Never raises; any failure or a call over GEMINI_TIMEOUT_S means (False, None)."""
    if not transcript.strip() or not get_settings().gemini_api_key:
        return False, None
    try:
        v = _pool.submit(_gemini_call, transcript).result(timeout=GEMINI_TIMEOUT_S)
        return bool(v.urgent), (v.reason or "possible urgent warning sign") if v.urgent else None
    except FutureTimeout:
        log.warning("gemini_flag timed out after %ss; treating as no extra flag", GEMINI_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001 - safety check must never crash the check-in
        log.warning("gemini_flag failed (%s: %s); treating as no extra flag", type(e).__name__, e)
    return False, None


def check(transcript: str, metrics: Optional[CheckinMetrics] = None, use_gemini: bool = True) -> RedFlagResult:
    """Final safety decision = rules OR gemini. Gemini only runs when rules found nothing."""
    result = check_rules(transcript, metrics)
    if result.flag or not use_gemini:
        return result
    flagged, reason = gemini_flag(transcript)
    return RedFlagResult(True, reason, "gemini") if flagged else result
