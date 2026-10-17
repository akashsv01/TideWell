"""Red-flag safety check. Runs BEFORE the agent; the agent never makes the safety decision.

Two layers, combined as rules OR gemini:
  1. check_rules(): deterministic regex rules, no network. Always runs.
  2. gemini_flag(): Gemini backup for phrasing the rules miss. Runs only when the rules found
     nothing, can only RAISE a flag, and any error/timeout (3 s) counts as "no extra flag".
Policy: over-flagging is acceptable; missing a real danger sign is not. When in doubt, flag.

Two levels, matching the RED vs AMBER tiers in clinical_assets/guidelines.json:
  - "emergency" (RED): call 911 / go to the ER now      -> EMERGENCY_RESPONSE
  - "urgent"    (AMBER): call your provider now, ER if they can't be reached -> URGENT_RESPONSE
Either level means: skip the agent and reply with result.response verbatim (no AI wording).
When several signs match, the more serious level wins; some urgent signs combine into an emergency.

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

Level = Literal["emergency", "urgent"]

# ---------------------------------------------------------------------------
# Thresholds from clinical_assets/guidelines.json (P4). TODO(clinical): sign-off still pending and
# thresholds.md is empty; the ACOG PDF behind bp-01..03 is encrypted, so we could not re-read it.
SEVERE_BP_SYS = 160  # bp-03: 160+ systolic is severe range -> emergency on its own
SEVERE_BP_DIA = 110  # bp-03: 110+ diastolic is severe range -> emergency on its own
ELEVATED_BP_SYS = 140  # bp-02: 140-159 / 90-109 PLUS severe headache or upper belly pain -> emergency
ELEVATED_BP_DIA = 90  # (on its own this range is the risk engine's AMBER, not a red flag)
FEVER_F = 100.4  # CDC Hear Her: "fever of 100.4 F or higher" (verified 2026-10-17)
# ---------------------------------------------------------------------------

GEMINI_TIMEOUT_S = 3
NEGATION_WINDOW = 3  # words checked before a match ("no blurry vision", "haven't had any spots")

EMERGENCY_RESPONSE = (
    "What you just described can be a sign of a serious problem after birth, and it needs care right now. "
    "Please call 911 or go to the nearest emergency room. Tell them you recently gave birth. "
    "If you are thinking about harming yourself or your baby, you can also call or text 988 any time. "
    "You are not alone, and getting help right now is the right thing to do."
)
URGENT_RESPONSE = (
    "What you just described is a warning sign after birth that should be checked today. "
    "Please call your doctor, midwife or clinic right now and tell them you recently gave birth. "
    "If you can't reach them, go to the emergency room or call 911. "
    "If this is about your mood or scary thoughts, you can also call or text the National Maternal Mental "
    "Health Hotline at 1-833-852-6262, any time, or 988 if you are thinking about harming yourself."
)
RESPONSES: dict[str, str] = {"emergency": EMERGENCY_RESPONSE, "urgent": URGENT_RESPONSE}


@dataclass(frozen=True)
class RedFlagResult:
    flag: bool
    reason: Optional[str] = None
    source: Optional[Literal["rules", "gemini"]] = None
    level: Optional[Level] = None

    @property
    def response(self) -> Optional[str]:
        """The fixed, pre-written reply for this level (None when not flagged)."""
        return RESPONSES.get(self.level) if self.flag else None


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
# (reason, level, patterns, negatable). guidelines.json ids in comments.
# Harm language is never negatable: "I'd never hurt my baby" still flags (urgent), by design.
_W = r"(?:\w+\s+)"  # one filler word
_BABY = r"(the|my|our)\s+(baby|son|daughter|newborn)"
_HARM = r"(hurt|harm|kill|shake|shaking|smother|drown)(ing|s)?"
RULES: list[tuple[str, Level, list[str], bool]] = [
    # mh-08 (RED): suicide or self-harm
    ("thoughts of suicide or self-harm", "emergency", [
        r"\b(hurt|harm|kill|cut)(ing|s)?\s+myself\b",
        r"\bsuicid\w*",
        r"\bend\s+(it|it all|my life|things)\b",
        r"\b(don'?t|do not)\s+want\s+to\s+(be here|be alive|live|exist|wake up)( anymore)?\b",
        r"\bwant(ed)?\s+to\s+die\b",
        r"\bbetter\s+off\s+without\s+me\b",
        r"\bwish\s+i\s+(was|were|wasn'?t|weren'?t)\s+(dead|gone|here|alive|born)\b",
        r"\b(no|not any)\s+reason\s+to\s+(live|keep going)\b",
        r"\bcan'?t\s+go\s+on\b",
    ], False),
    # mh-10, mh-11 (RED): intent to harm the baby, or psychosis signs
    ("intent to harm the baby or signs of psychosis", "emergency", [
        rf"\b(want|wanted|going|gonna|plan|planning|will|might|could)\s+(to\s+)?{_HARM}\s+{_BABY}\b",
        r"\bvoices?\b[^.]{0,30}\b(telling|tell|told)\s+me\b",
        r"\bhear(ing)?\s+voices\b",
        r"\bseeing\s+things\s+(that\s+)?(aren'?t|are\s+not|that\s+aren'?t)\s+there\b",
    ], False),
    # mh-09 (AMBER): thoughts about harm to the baby (often distressing intrusive thoughts)
    ("thoughts about harming the baby", "urgent", [
        rf"\b{_HARM}\s+{_BABY}\b",
        r"\b(thoughts?|thinking|thought|picturing|images?)\s+(of|about)\s+(hurting|harming|killing|dropping|something\s+bad)\b",
        rf"\b(afraid|scared|terrified|worried)\s+(that\s+)?i('ll|\s+will|\s+might|\s+could)\s+{_HARM}\s+{_BABY}\b",
    ], False),
    # mh-08 example phrase; urgent (not 911) so exhausted venting gets a provider + hotline, not an ambulance
    ("feeling unable to cope", "urgent", [r"\bcan'?t\s+do\s+this\s+any\s?more\b"], False),
    # wsign-02 (RED)
    ("blurry or changed vision", "emergency", [
        r"\b(blurry|blurred|blurriness|blurring|fuzzy|hazy)\b",
        r"\b(seeing|see|saw|seen)\s+(spots|stars|double|flashes|sparkles|floaters|flashing)\b",
        r"\bflash(ing|es)?\s+(of\s+)?lights?\b",
        r"\bdouble\s+vision\b",
        r"\bspots\s+in\s+(my\s+)?(eyes?|vision)\b",
        r"\bcan'?t\s+see\s+(properly|clearly|straight|well|right)\b",
        r"\bvision\s+(is\s+|has\s+been\s+|went\s+|keeps\s+|seems\s+)?(off|weird|strange|dim|dark|changed|changing|wrong|funny|going)\b",
        r"\blos(t|ing)\s+(my\s+)?(vision|sight)\b",
    ], True),
    # wsign-01 (AMBER); becomes an emergency with vision change, high BP or upper belly pain
    ("severe headache", "urgent", [
        r"\bworst\s+headache\b",
        rf"\b(severe|terrible|awful|horrible|pounding|splitting|excruciating|unbearable|intense|crushing|blinding|massive)\s+{_W}?headaches?\b",
        r"\b(really|super|so|very)\s+bad\s+headaches?\b",
        r"\bhead\s+(is\s+)?(killing me|pounding|splitting|exploding)\b",
        r"\bheadaches?\b[^.]{0,60}\b(won'?t|will not|doesn'?t|does not|isn'?t|not)\s+(go(ing)?\s+away|stop|help(ing)?|budge|work(ing)?)\b",
        r"\bheadaches?\b[^.]{0,60}\b(even\s+(with|after)|despite)\s+(the\s+)?(medicine|meds|tylenol|ibuprofen|advil|motrin|painkillers?|pain\s+meds)\b",
        r"\b(medicine|meds|tylenol|ibuprofen|advil|motrin|painkillers?)\b[^.]{0,40}\b(didn'?t|doesn'?t|isn'?t|not|hasn'?t|won'?t)\s+(help|helping|helped|work|working|touch)\b[^.]{0,40}\bhead",
    ], True),
    # bp-02 (with high BP or headache -> emergency); alone it is urgent
    ("upper right or upper belly pain", "urgent", [
        r"\b(pain|hurts?|hurting|ache|aching|sore)\b[^.]{0,25}\b(under|below|beneath)\s+(my\s+)?(right\s+)?(ribs?|rib\s*cage)\b",
        r"\bright\s+(side\s+)?(ribs?|rib\s*cage)\b[^.]{0,20}\b(pain|hurts?|hurting|aching|sore)\b",
        r"\b(upper|top)\s+(right\s+)?(of\s+(my\s+)?)?(belly|stomach|abdomen|tummy)\b[^.]{0,20}\b(pain|hurts?|hurting|aching)\b",
        r"\b(pain|hurts?|hurting|ache|aching)\b[^.]{0,20}\b(upper|top)\s+(right\s+)?(part\s+|side\s+)?(of\s+)?(my\s+)?(belly|stomach|abdomen|tummy)\b",
        r"\b(upper\s+right|right\s+upper)\s+(belly|stomach|abdomen|abdominal|quadrant)\b",
        r"\bepigastric\b",
    ], True),
    # wsign-04 (RED)
    ("chest pain, trouble breathing or fast heartbeat", "emergency", [
        r"\bchest\s+(pains?|hurts?|hurting|pressure|tightness|is\s+tight|feels\s+tight|feels\s+heavy|is\s+heavy)\b",
        r"\bpain\s+in\s+(my\s+)?chest\b",
        r"\btight(ness)?\s+in\s+(my\s+)?chest\b",
        rf"\b(trouble|difficulty|hard|struggling|struggle|hard\s+time)\s+{_W}{{0,2}}breath(e|ing)\b",
        r"\bcan'?t\s+(catch\s+my\s+)?breathe?\b",
        r"\bcan'?t\s+get\s+(enough\s+)?air\b",
        r"\bshort(ness)?\s+of\s+breath\b",
        r"\b(gasping|breathless|winded)\b",
        r"\b(heart|heartbeat|pulse)\b[^.]{0,20}\b(racing|pounding|fluttering|skipping|irregular|beating\s+(so\s+|really\s+)?fast|going\s+(so\s+|really\s+)?fast)\b",
        r"\b(racing|pounding)\s+heart\b",
        r"\bpalpitations?\b",
    ], True),
    # bleed-01 (RED). Clots: CDC says "bigger than an egg"; we also match golf ball and larger.
    ("heavy bleeding", "emergency", [
        r"\bsoak(ed|ing|s)?\s+(through\s+)?(a\s+|one\s+|my\s+|the\s+|two\s+)?(\w+\s+)?pads?\b",
        r"\bpads?\b[^.]{0,30}\b(every|in\s+an?|within\s+an?|each)\s+(hour|half\s+hour)\b",
        r"\b(large|big|huge|giant|golf\s*-?\s*ball|egg|plum|lemon)\s*-?\s*(sized\s+)?clots?\b",
        r"\bclots?\s+(the\s+size\s+of|as\s+big\s+as|bigger\s+than)\b",
        r"\bbleeding\s+(a\s+lot|so\s+much|heavily|really\s+heavy|like\s+crazy|through|non-?stop|more\s+and\s+more)\b",
        rf"\b(heavy|heavier|lots\s+of|a\s+lot\s+of|so\s+much|tons\s+of|gushing|pouring)\s+{_W}?(bleeding|blood)\b",
        r"\bblood\s+(is\s+)?(gushing|pouring|everywhere)\b",
        r"\bhemorrhag\w*",
    ], True),
    # wsign-03 (RED)
    ("seizure", "emergency", [r"\bseizures?\b", r"\bconvuls\w*", r"\bhad\s+a\s+fit\b"], True),
    # wsign-07: fainting -> 911
    ("fainting or passing out", "emergency", [
        r"\b(fainted|fainting|faints)\b",
        r"\b(pass|passed|passing)\s+out\b",
        r"\b(black|blacked|blacking)\s+out\b",
        r"\blost\s+consciousness\b",
        r"\bcollapsed\b",
    ], True),
    # wsign-07 (AMBER): dizziness or feeling faint
    ("dizziness", "urgent", [
        r"\b(dizzy|dizziness|light-?\s?headed(ness)?|woozy|vertigo)\b",
        r"\b(room|everything)\s+(is\s+|was\s+|keeps\s+)?spinning\b",
        r"\b(feel|felt|feeling)\s+(\w+\s+){0,2}faint\b",
    ], True),
    # wsign-05 (AMBER)
    ("swollen, red or painful leg or arm", "urgent", [
        r"\b(swollen|swelling|red|hot|warm|painful)\b[^.]{0,25}\b(legs?|calf|calves|thighs?|arms?)\b",
        r"\b(legs?|calf|calves|thighs?|arms?)\b[^.]{0,25}\b(swollen|swelling|red|hot|warm to the touch)\b",
        r"\b(severe|terrible|awful|unbearable|really\s+bad)\s+pain\s+in\s+(my\s+)?(leg|calf|thigh|arm)\b",
    ], True),
    # wsign-02 (RED)
    ("extreme swelling of face or hands", "emergency", [
        r"\b(swollen|swelling|puffy|puffed(\s+up)?|puffiness|bloated)\b[^.]{0,25}\b(face|hands?|fingers|eyes|eyelids)\b",
        r"\b(face|hands?|fingers|eyes|eyelids)\b[^.]{0,25}\b(swollen|swelling|puffy|puffed(\s+up)?|so\s+swollen)\b",
        r"\bcan'?t\s+(get|take)\s+(my\s+)?rings?\s+off\b",
    ], True),
    # wsign-02 (RED)
    ("severe belly pain", "emergency", [
        rf"\b(severe|terrible|awful|horrible|unbearable|excruciating|intense|sharp|really\s+bad)\s+{_W}?(belly|stomach|abdominal|tummy|abdomen|pelvic)\s+pain\b",
        r"\b(belly|stomach|abdomen|tummy)\b[^.]{0,30}\b(killing me|unbearable|won'?t stop hurting|hurts so (bad|much))\b",
        r"\b(belly|stomach|abdominal|tummy)\s+pain\b[^.]{0,40}\b(won'?t|doesn'?t|isn'?t|not)\s+(go(ing)?\s+away|stop|getting better)\b",
    ], True),
    # wsign-02 (RED)
    ("severe nausea or vomiting", "emergency", [
        r"\b(can'?t|cannot)\s+stop\s+(throwing\s+up|vomiting|puking)\b",
        r"\b(keep|kept|been|keeps)\s+(throwing\s+up|vomiting|puking)\b",
        r"\b(vomiting|throwing\s+up)\s+(all\s+day|nonstop|non-stop|everything|constantly)\b",
        r"\b(severe|terrible|really\s+bad|constant)\s+nausea\b",
        r"\bcan'?t\s+keep\s+(anything|food|water|fluids|liquids)\s+down\b",
    ], True),
    # wsign-08 (AMBER). Narrow on purpose: ordinary "I'm so tired" is near-universal postpartum.
    ("overwhelming tiredness", "urgent", [
        r"\boverwhelming(ly)?\s+(tired|tiredness|exhausted|exhaustion|fatigue)\b",
        r"\b(tired|exhausted)\b[^.]{0,20}\bcan'?t\s+(get\s+out\s+of\s+bed|stand|stay\s+awake|function|take\s+care\s+of\s+(the|my)\s+baby)\b",
    ], True),
]
_COMPILED = [(r, lvl, [re.compile(p, re.IGNORECASE) for p in ps], n) for r, lvl, ps, n in RULES]

# wsign-06 (AMBER): fever 100.4 F or higher. A stated temperature decides; otherwise the word flags.
_FEVER_WORD = re.compile(r"\b(fever|feverish|febrile|running\s+a\s+temp(erature)?)\b", re.I)
_TEMP = re.compile(
    r"\b(temp|temperature|fever|thermometer)\b[^.\d]{0,25}(\d{2,3}(?:\.\d+)?)\s*(degrees?)?\s*([fc])?\b", re.I
)


def _fever(text: str) -> bool:
    temps = []
    for m in _TEMP.finditer(text):
        v, unit = float(m.group(2)), (m.group(4) or "").lower()
        temps.append(v >= FEVER_F if unit != "c" and v > 45 else 38.0 <= v <= 45)
    if temps:
        return any(temps)
    return _find(_FEVER_WORD, text, True)


def _find(pattern: re.Pattern, text: str, negatable: bool) -> bool:
    return any(not (negatable and _negated(text, m.start(), m.end())) for m in pattern.finditer(text))


def _normalize(text: str) -> str:
    return (text or "").replace("’", "'").replace("‘", "'")


def _matches(text: str, metrics: Optional[CheckinMetrics]) -> list[tuple[Level, str]]:
    found: list[tuple[Level, str]] = [
        (level, reason)
        for reason, level, patterns, negatable in _COMPILED
        if any(_find(p, text, negatable) for p in patterns)
    ]
    if _fever(text):
        found.append(("urgent", "fever of 100.4 F or higher"))
    if metrics is not None:
        if (metrics.bp_sys or 0) >= SEVERE_BP_SYS or (metrics.bp_dia or 0) >= SEVERE_BP_DIA:
            found.append(("emergency", f"severe-range blood pressure ({metrics.bp_sys}/{metrics.bp_dia})"))
        if metrics.bleeding == "heavy":
            found.append(("emergency", "heavy bleeding"))
        if metrics.vision_change:
            found.append(("emergency", "blurry or changed vision"))
        if metrics.fever:
            found.append(("urgent", "fever of 100.4 F or higher"))
    return found


def check_rules(transcript: str, metrics: Optional[CheckinMetrics] = None) -> RedFlagResult:
    found = _matches(_normalize(transcript), metrics)
    if not found:
        return SAFE
    for level, reason in found:
        if level == "emergency":
            return RedFlagResult(True, reason, "rules", "emergency")

    # Urgent signs that combine into an emergency (bp-02, wsign-01).
    reasons = {r for _, r in found}
    headache, upper_belly = "severe headache" in reasons, "upper right or upper belly pain" in reasons
    elevated_bp = metrics is not None and (
        (metrics.bp_sys or 0) >= ELEVATED_BP_SYS or (metrics.bp_dia or 0) >= ELEVATED_BP_DIA
    )
    if elevated_bp and (headache or upper_belly):
        return RedFlagResult(True, "high blood pressure with severe headache or upper belly pain", "rules", "emergency")
    if headache and upper_belly:
        return RedFlagResult(True, "severe headache with upper belly pain", "rules", "emergency")
    return RedFlagResult(True, found[0][1], "rules", "urgent")


# --- Gemini backup -----------------------------------------------------------
class _GeminiVerdict(BaseModel):
    urgent: bool = False
    emergency: bool = False
    reason: Optional[str] = None


_GEMINI_PROMPT = (
    "You are a safety screener for a postpartum check-in app. You do not diagnose. "
    "Decide if the parent's words describe ANY urgent maternal warning sign, even if phrased indirectly or "
    "casually: thoughts of harming themself or the baby or not wanting to live; vision changes; severe or "
    "persistent headache; chest pain, trouble breathing or a fast-beating heart; heavy bleeding or large clots; "
    "seizure; fainting or dizziness; fever of 100.4 F or higher; severe belly pain; severe nausea or vomiting; "
    "a swollen, red or painful leg or arm; extreme swelling of face or hands; overwhelming tiredness; "
    "extreme confusion, hallucinations or paranoia. Ignore symptoms the person says are absent or resolved. "
    "If you are unsure, answer urgent=true. Set emergency=true as well when it needs 911 now: suicidal "
    "thoughts or intent, intent to harm the baby, hallucinations, chest pain or trouble breathing, heavy "
    "bleeding, seizure, fainting, vision changes, or severe belly pain. reason is a short plain phrase "
    "naming the sign, or null."
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


def gemini_flag(transcript: str) -> tuple[bool, Optional[str], Optional[Level]]:
    """Backup screen -> (flagged, reason, level). Never raises; any failure or a call over
    GEMINI_TIMEOUT_S means (False, None, None)."""
    if not transcript.strip() or not get_settings().gemini_api_key:
        return False, None, None
    try:
        v = _pool.submit(_gemini_call, transcript).result(timeout=GEMINI_TIMEOUT_S)
        if v.urgent or v.emergency:
            return True, v.reason or "possible urgent warning sign", "emergency" if v.emergency else "urgent"
        return False, None, None
    except FutureTimeout:
        log.warning("gemini_flag timed out after %ss; treating as no extra flag", GEMINI_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001 - safety check must never crash the check-in
        log.warning("gemini_flag failed (%s: %s); treating as no extra flag", type(e).__name__, e)
    return False, None, None


def check(transcript: str, metrics: Optional[CheckinMetrics] = None, use_gemini: bool = True) -> RedFlagResult:
    """Final safety decision = rules OR gemini. Gemini only runs when rules found nothing."""
    result = check_rules(transcript, metrics)
    if result.flag or not use_gemini:
        return result
    flagged, reason, level = gemini_flag(transcript)
    return RedFlagResult(True, reason, "gemini", level) if flagged else result
