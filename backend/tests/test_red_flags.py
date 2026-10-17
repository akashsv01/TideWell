import pytest

from app.ai import red_flags
from app.ai.red_flags import RedFlagResult, check, check_rules
from app.schemas import CheckinMetrics

DANGEROUS = [
    ("everything looks kind of fuzzy since this morning", "vision"),
    ("My vision has been blurry and I keep seeing spots", "vision"),
    ("there are these flashing lights in the corner of my eye", "vision"),
    ("I'm seeing double when I look at my phone", "vision"),
    ("This is honestly the worst headache I've ever had", "headache"),
    ("I've had a headache for two days that won't go away even with Tylenol", "headache"),
    ("my head is pounding and the medicine isn't helping my head at all", "headache"),
    ("My chest feels tight and it hurts when I lie down", "chest"),
    ("I get out of breath just walking to the kitchen, I can't catch my breath", "breath"),
    ("I'm soaking through a pad every hour", "bleeding"),
    ("I passed a clot the size of a golf ball this morning", "bleeding"),
    ("I keep thinking the baby would be better off without me", "harming"),
    ("sometimes I just don't want to be here anymore", "harming"),
    ("I had a scary thought about hurting the baby", "harming"),
    ("I fainted in the shower yesterday", "fainting"),
    ("I think I had a seizure last night", "seizure"),
    ("I have a fever and the pain in my incision is like a nine", "fever"),
    ("my left calf is really swollen and red", "leg"),
    ("It was better yesterday, but now I'm seeing spots again", "vision"),
]

SAFE = [
    "No blurry vision today, which is nice",
    "My headache is finally gone",
    "I'm not bleeding much anymore",
    "Bleeding has slowed down a lot",
    "The baby slept four hours straight and I feel almost human",
    "My incision is a little sore but getting better each day",
    "I haven't had any spots in my vision",
    "I'm tired and a bit weepy, but I had a nice walk",
    "The days are all a blur with a newborn",
    "Breastfeeding hurts a little at the start of each feed",
    "Mild headache this morning but it went away after coffee",
    "The spots in my eyes went away",
]

BP_CASES = [
    (CheckinMetrics(bp_sys=165, bp_dia=95), True),
    (CheckinMetrics(bp_sys=140, bp_dia=112), True),
    (CheckinMetrics(bp_sys=red_flags.SEVERE_BP_SYS, bp_dia=80), True),
    (CheckinMetrics(bp_sys=128, bp_dia=82), False),
    (CheckinMetrics(bp_sys=None, bp_dia=None), False),
]


@pytest.mark.parametrize("text,reason_hint", DANGEROUS)
def test_dangerous_flags(text, reason_hint):
    r = check_rules(text)
    assert r.flag, f"missed danger sign: {text!r}"
    assert r.source == "rules"
    assert reason_hint in r.reason


@pytest.mark.parametrize("text", SAFE)
def test_safe_does_not_flag(text):
    r = check_rules(text)
    assert not r.flag, f"false flag ({r.reason}): {text!r}"


@pytest.mark.parametrize("metrics,expected", BP_CASES)
def test_bp_from_metrics(metrics, expected):
    assert check_rules("feeling okay today", metrics).flag is expected


def test_self_harm_is_never_negated():
    # Deliberate over-flag: negation is ignored for self-harm language.
    assert check_rules("I would never hurt my baby, I just feel so empty").flag


# --- Gemini backup (mocked) -------------------------------------------------
RULES_MISS = [
    "I feel like my family would honestly be happier if I just disappeared",
    "my face and hands puffed up out of nowhere tonight",
    "I'm so confused, I couldn't remember my own address earlier",
]


@pytest.mark.parametrize("text", RULES_MISS)
def test_gemini_catches_what_rules_miss(monkeypatch, text):
    assert not check_rules(text).flag, "rules caught it; move this case to DANGEROUS"
    monkeypatch.setattr(red_flags, "gemini_flag", lambda t: (True, "possible warning sign"))
    r = check(text)
    assert r == RedFlagResult(True, "possible warning sign", "gemini")


def test_gemini_cannot_clear_a_rules_flag(monkeypatch):
    called = []
    monkeypatch.setattr(red_flags, "gemini_flag", lambda t: called.append(t) or (False, None))
    r = check("I'm soaking through a pad every hour")
    assert r.flag and r.source == "rules"
    assert called == [], "gemini must not run when rules already flagged"


def test_gemini_failure_never_crashes(monkeypatch):
    def boom(_):
        raise RuntimeError("network down")

    monkeypatch.setattr(red_flags.get_settings(), "gemini_api_key", "fake-key")
    monkeypatch.setattr(red_flags, "_gemini_call", boom)
    assert check("feeling okay today") == red_flags.SAFE


def test_gemini_timeout_is_no_flag(monkeypatch):
    import time

    monkeypatch.setattr(red_flags.get_settings(), "gemini_api_key", "fake-key")
    monkeypatch.setattr(red_flags, "GEMINI_TIMEOUT_S", 0.2)
    monkeypatch.setattr(red_flags, "_gemini_call", lambda t: time.sleep(1))
    assert red_flags.gemini_flag("feeling okay") == (False, None)
