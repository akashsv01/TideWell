import pytest

from app.ai import red_flags
from app.ai.red_flags import EMERGENCY_RESPONSE, URGENT_RESPONSE, RedFlagResult, check, check_rules
from app.schemas import CheckinMetrics

E, U = "emergency", "urgent"

# (text, substring of reason, expected level). Levels follow RED/AMBER in clinical_assets/guidelines.json.
DANGEROUS = [
    ("everything looks kind of fuzzy since this morning", "vision", E),
    ("My vision has been blurry and I keep seeing spots", "vision", E),
    ("there are these flashing lights in the corner of my eye", "vision", E),
    ("I'm seeing double when I look at my phone", "vision", E),
    ("It was better yesterday, but now I'm seeing spots again", "vision", E),
    ("This is honestly the worst headache I've ever had", "headache", U),
    ("I've had a headache for two days that won't go away even with Tylenol", "headache", U),
    ("my head is pounding and the medicine isn't helping my head at all", "headache", U),
    ("My chest feels tight and it hurts when I lie down", "chest", E),
    ("I get out of breath just walking to the kitchen, I can't catch my breath", "breathing", E),
    ("my heart keeps racing even when I'm lying down", "heartbeat", E),
    ("I'm soaking through a pad every hour", "bleeding", E),
    ("I passed a clot the size of a golf ball this morning", "bleeding", E),
    ("I passed an egg sized clot", "bleeding", E),
    ("I keep thinking the baby would be better off without me", "suicide", E),
    ("sometimes I just don't want to be here anymore", "suicide", E),
    ("I want to hurt the baby", "intent to harm the baby", E),
    ("the voices are telling me to do things", "psychosis", E),
    ("I had a scary thought about hurting the baby", "harming the baby", U),
    ("I'm terrified I'll hurt my baby when I'm this tired", "harming the baby", U),
    ("I can't do this anymore", "unable to cope", U),
    ("I fainted in the shower yesterday", "fainting", E),
    ("I think I had a seizure last night", "seizure", E),
    ("I have a fever and the pain in my incision is like a nine", "fever", U),
    ("my temperature was 101.2 this morning", "fever", U),
    ("I think I'm running a fever", "fever", U),
    ("my left calf is really swollen and red", "leg", U),
    ("my right arm is swollen and red", "leg or arm", U),
    ("my face and hands puffed up out of nowhere tonight", "swelling of face", E),
    ("my fingers are so swollen I can't get my rings off", "swelling of face", E),
    ("I have this sharp stomach pain that won't go away", "belly", E),
    ("I can't keep anything down, I keep throwing up", "nausea", E),
    ("I've been really dizzy every time I stand up", "dizziness", U),
    ("I feel kind of faint when I get up", "dizziness", U),
    ("I'm so exhausted I can't take care of the baby", "tiredness", U),
    # Upper right / upper belly pain (bp-02): urgent alone
    ("I have this pain under my right ribs", "upper", U),
    ("there's a pain in the top of my stomach", "upper", U),
    ("my upper right belly hurts", "upper", U),
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
    "No fever today, temperature was 98.6",
    "temperature was 99.1 so I think I'm fine",
    "I'm so tired, the baby was up every two hours",
    "my feet are a little swollen at the end of the day",
    "my stomach is a bit crampy while feeding",
    "not dizzy anymore since I started drinking more water",
]

BP_CASES = [  # (metrics, expected level or None)
    (CheckinMetrics(bp_sys=165, bp_dia=95), E),
    (CheckinMetrics(bp_sys=140, bp_dia=112), E),
    (CheckinMetrics(bp_sys=red_flags.SEVERE_BP_SYS, bp_dia=80), E),
    (CheckinMetrics(bp_sys=144, bp_dia=92), None),  # elevated alone: risk engine AMBER, not a red flag
    (CheckinMetrics(bp_sys=128, bp_dia=82), None),
    (CheckinMetrics(bp_sys=None, bp_dia=None), None),
]


@pytest.mark.parametrize("text,reason_hint,level", DANGEROUS)
def test_dangerous_flags(text, reason_hint, level):
    r = check_rules(text)
    assert r.flag, f"missed danger sign: {text!r}"
    assert r.source == "rules"
    assert reason_hint in r.reason, r.reason
    assert r.level == level, f"{text!r}: expected {level}, got {r.level} ({r.reason})"


@pytest.mark.parametrize("text", SAFE)
def test_safe_does_not_flag(text):
    r = check_rules(text)
    assert not r.flag, f"false flag ({r.reason}): {text!r}"


@pytest.mark.parametrize("metrics,level", BP_CASES)
def test_bp_from_metrics(metrics, level):
    r = check_rules("feeling okay today", metrics)
    assert r.flag is (level is not None) and r.level == level


# --- Combinations that escalate urgent -> emergency (bp-02, wsign-01) -----------------
@pytest.mark.parametrize("text,metrics", [
    ("this is the worst headache I've ever had", CheckinMetrics(bp_sys=145, bp_dia=95)),
    ("I have this pain under my right ribs", CheckinMetrics(bp_sys=150, bp_dia=96)),
    ("terrible headache and a pain under my right ribs", None),
])
def test_combinations_escalate_to_emergency(text, metrics):
    r = check_rules(text, metrics)
    assert r.level == E, r


def test_maya_demo_is_not_a_red_flag():
    # Demo path: an ordinary headache + 144/92 must reach the agent (risk engine AMBER -> offer a visit).
    r = check_rules("I had another headache this afternoon and slept four hours",
                    CheckinMetrics(bp_sys=144, bp_dia=92, headache=True, sleep_hrs=4))
    assert not r.flag, r


def test_emergency_beats_urgent():
    r = check_rules("I'm a bit dizzy and I'm soaking through a pad every hour")
    assert r.level == E and "bleeding" in r.reason


def test_harm_language_is_never_negated():
    # Deliberate over-flag: negation is ignored for harm language, but it stays urgent, not 911.
    r = check_rules("I would never hurt my baby, I just feel so empty")
    assert r.flag and r.level == U


def test_fixed_responses():
    assert check_rules("I'm soaking through a pad every hour").response == EMERGENCY_RESPONSE
    assert check_rules("I think I'm running a fever").response == URGENT_RESPONSE
    assert red_flags.SAFE.response is None
    assert "911" in EMERGENCY_RESPONSE and "988" in EMERGENCY_RESPONSE
    assert "call your doctor" in URGENT_RESPONSE and "1-833-852-6262" in URGENT_RESPONSE


# --- Gemini backup (mocked) -------------------------------------------------
RULES_MISS = [
    "I feel like my family would honestly be happier if I just disappeared",
    "something just feels really wrong with my body and I'm scared",
    "I'm so confused, I couldn't remember my own address earlier",
]


@pytest.mark.parametrize("text", RULES_MISS)
def test_gemini_catches_what_rules_miss(monkeypatch, text):
    assert not check_rules(text).flag, "rules caught it; move this case to DANGEROUS"
    monkeypatch.setattr(red_flags, "gemini_flag", lambda t: (True, "possible warning sign", U))
    assert check(text) == RedFlagResult(True, "possible warning sign", "gemini", U)


def test_gemini_emergency_level_passes_through(monkeypatch):
    monkeypatch.setattr(red_flags, "gemini_flag", lambda t: (True, "suicidal thoughts", E))
    r = check(RULES_MISS[0])
    assert r.level == E and r.response == EMERGENCY_RESPONSE


def test_gemini_cannot_clear_a_rules_flag(monkeypatch):
    called = []
    monkeypatch.setattr(red_flags, "gemini_flag", lambda t: called.append(t) or (False, None, None))
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
    assert red_flags.gemini_flag("feeling okay") == (False, None, None)
