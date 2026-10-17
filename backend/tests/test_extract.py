"""Extraction against the REAL Gemini API. Skipped when GEMINI_API_KEY is missing.
Rule under test: extract only what was said; never infer values that were not stated."""
import pytest

from app.config import get_settings

pytestmark = pytest.mark.skipif(not get_settings().gemini_api_key, reason="GEMINI_API_KEY not set")

# (transcript, expected subset of fields). Fields not listed must be null/False/[] unless in ALLOW.
CASES = [
    pytest.param(
        "So my mom came over and we watched like half a movie, the baby was fussy the whole time, "
        "oh and I took my blood pressure this morning, it was 138 over 88, anyway she finally fell asleep.",
        {"bp_sys": 138, "bp_dia": 88}, id="rambling-bp-buried",
    ),
    pytest.param("BP was one forty over ninety this morning", {"bp_sys": 140, "bp_dia": 90}, id="bp-in-words"),
    pytest.param("I slept maybe four hours last night", {"sleep_hrs": 4.0}, id="sleep-in-words"),
    pytest.param("my pain is like a six today", {"pain": 6}, id="pain-in-words"),
    pytest.param("incision pain is about a three, way better", {"incision_pain": 3}, id="incision-pain"),
    pytest.param(
        "I'm doing okay I guess, just really tired.",
        {}, id="nothing-numeric",
    ),
    pytest.param(
        "Feeling better than yesterday, the pain is less than it was.",
        {}, id="relative-no-numbers",
    ),
    pytest.param(
        "I have a headache, a bit of a fever, and the bleeding is pretty light now",
        {"headache": True, "fever": True, "bleeding": "light"}, id="multi-symptom",
    ),
    pytest.param(
        "Mood's like a four out of ten, I slept three and a half hours, and no headache today.",
        {"mood": 4, "sleep_hrs": 3.5, "headache": False}, id="mood-sleep-negated-headache",
    ),
    pytest.param(
        "Honestly I'm not sure what my blood pressure is, I haven't checked it in days.",
        {"bp_sys": None, "bp_dia": None}, id="bp-not-measured",
    ),
    pytest.param(
        "No bleeding at all anymore and my vision's totally fine",
        {"bleeding": "none", "vision_change": False}, id="explicit-none",
    ),
    pytest.param(
        "I'm seeing spots and my headache is back",
        {"vision_change": True, "headache": True}, id="vision-and-headache",
    ),
]

NUMERIC = ("mood", "pain", "incision_pain", "sleep_hrs", "bp_sys", "bp_dia")


@pytest.mark.parametrize("transcript,expected", CASES)
def test_extract(transcript, expected):
    from app.ai.extract import extract_metrics

    m = extract_metrics(transcript)
    got = m.model_dump()
    for field, value in expected.items():
        assert got[field] == value, f"{field}: expected {value!r}, got {got[field]!r}  ({m.model_dump_json()})"
    for field in NUMERIC:
        if field not in expected:
            assert got[field] is None, f"invented {field}={got[field]!r} that was never said  ({m.model_dump_json()})"
