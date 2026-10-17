"""Phase 0 smoke test. Run from backend/:  .venv/Scripts/python scripts/smoke_test.py
Prints PASS / FAIL / SKIPPED per service. Never prints API keys."""
import sys
import time
import traceback
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
results: dict[str, str] = {}


def run(name: str, required_keys: list[str], fn) -> None:
    print(f"\n=== {name} ===")
    s = get_settings()
    missing = [k for k in required_keys if not getattr(s, k)]
    if missing:
        results[name] = f"SKIPPED (missing {', '.join(k.upper() for k in missing)})"
        print(results[name])
        return
    try:
        fn()
        results[name] = "PASS"
    except Exception as e:  # noqa: BLE001
        results[name] = f"FAIL: {type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc(limit=2)
    print(results[name])


def gemini() -> None:
    from app.ai.extract import extract_metrics

    m = extract_metrics("I slept about 3 hours, my headache is back and my BP this morning was 142 over 91")
    print(m.model_dump_json(indent=2))
    assert m.bp_sys == 142 and m.bp_dia == 91 and m.headache, "extraction did not match expected values"


def elevenlabs() -> None:
    from app.ai.stt import transcribe
    from app.ai.tts import speak

    OUT.mkdir(exist_ok=True)
    audio = speak("Hi, I'm Tidewell")
    path = OUT / "hello.mp3"
    path.write_bytes(audio)
    print(f"TTS wrote {len(audio)} bytes -> {path}")
    text = transcribe(path.read_bytes())
    print(f"STT: {text!r}")
    assert "tidewell" in text.lower().replace(" ", ""), "round-trip transcript missing 'Tidewell'"


def backboard() -> None:
    from app.ai import memory

    patient = f"smoke-{uuid.uuid4().hex[:8]}"
    r1 = memory.chat(patient, "My name is Maya and I had a C-section")
    print(f"Reply 1: {r1}")
    for _ in range(10):  # memory extraction is usually instant but runs async on Backboard's side
        if memory.recall(patient, "surgery"):
            break
        time.sleep(2)
    # Fresh thread on the same assistant: the answer must come from Backboard memory, not chat history.
    memory.get_or_create(patient, new_thread=True)
    r2 = memory.chat(patient, "What surgery did I have?")
    print(f"Reply 2 (new thread): {r2}")
    print(f"recall('surgery'): {memory.recall(patient, 'surgery')}")
    assert any(k in r2.lower() for k in ("c-section", "cesarean", "caesarean")),         "second reply did not recall the C-section"


def red_flags() -> None:
    from app.ai.red_flags import check

    safe = [
        "I'm tired but the baby slept four hours straight last night.",
        "My incision is a little sore but getting better each day.",
        "Feeling a bit weepy today, but I had a nice walk.",
    ]
    danger = [
        "My vision has been blurry since this morning and I'm seeing spots.",
        "I'm soaking through a pad every hour.",
        "Sometimes I think everyone would be better off without me.",
    ]
    ok = True
    for s in safe:
        flag, reason = (r := check(s, use_gemini=False)).flag, r.reason
        print(f"  [{'FLAG' if flag else 'safe'}] expected safe   | {reason} | {s}")
        ok &= not flag
    for s in danger:
        flag, reason = (r := check(s, use_gemini=False)).flag, r.reason
        print(f"  [{'FLAG' if flag else 'safe'}] expected FLAG   | {reason} | {s}")
        ok &= flag
    assert ok, "a sample was misclassified"


run("Gemini extraction", ["gemini_api_key"], gemini)
run("ElevenLabs TTS+STT", ["elevenlabs_api_key"], elevenlabs)
run("Backboard memory", ["backboard_api_key"], backboard)
run("Red flags", [], red_flags)

print("\n=== SUMMARY ===")
for k, v in results.items():
    print(f"{k:22} {v}")
