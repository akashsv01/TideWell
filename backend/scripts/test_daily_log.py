"""QA for PUT /patients/{id}/days/{day}. Run with the backend up:
  .venv/Scripts/python scripts/test_daily_log.py
Uses urllib only. Never prints tokens. Cleans up with DELETE /patients/{id}.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

BASE = os.environ.get("TIDEWELL_API", "http://127.0.0.1:8001").rstrip("/")
MAYA = "00000000-0000-4000-8000-000000000001"
fails = 0


def utc_today() -> date:
    """Match the backend's day boundary (UTC), not the local clock."""
    return datetime.now(timezone.utc).date()


def req(method: str, path: str, body=None, token: str | None = None, expect: int | None = None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as res:
            raw = res.read()
            code = res.status
            out = json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        code = e.code
        try:
            out = json.loads(raw) if raw else {"detail": e.reason}
        except json.JSONDecodeError:
            out = {"detail": raw.decode(errors="replace")[:200]}
    if expect is not None and code != expect:
        global fails
        fails += 1
        print(f"FAIL {method} {path}: expected {expect}, got {code} -> {out}")
    else:
        print(f"OK   {method} {path} -> {code}")
    return code, out


def check(cond: bool, msg: str) -> None:
    global fails
    if cond:
        print(f"OK   {msg}")
    else:
        fails += 1
        print(f"FAIL {msg}")


def main() -> int:
    print(f"API: {BASE}")
    code, _ = req("GET", "/health", expect=200)
    if code != 200:
        print("Backend not reachable; start uvicorn first.")
        return 1

    user = f"qa_{secrets.token_hex(4)}"
    password = "testpass99"
    code, auth = req("POST", "/auth/register", {"username": user, "password": password}, expect=201)
    if code != 201 or not auth or "token" not in auth:
        print("register failed; abort")
        return 1
    token = auth["token"]

    today = utc_today()
    delivery = today - timedelta(days=10)
    day5 = delivery + timedelta(days=5)
    before = delivery - timedelta(days=1)
    future = today + timedelta(days=1)

    code, prof = req(
        "POST",
        "/onboard",
        {
            "consent_granted": True,
            "delivery_date": delivery.isoformat(),
            "gestation_weeks": 39,
            "delivery_method": "vaginal",
            "feeding_type": "mixed",
            "name": "QA",
        },
        token=token,
        expect=200,
    )
    if code != 200 or not prof:
        print("onboard failed; abort")
        return 1
    pid = prof["patient_id"]
    print(f"patient={pid} delivery={delivery} day5={day5}")

    # First PUT for day 5 postpartum
    req(
        "PUT",
        f"/patients/{pid}/days/{day5.isoformat()}",
        {"mood": 4, "pain": 3, "sleep_hrs": 5.0, "headache": False, "bp_sys": 118, "bp_dia": 76},
        token=token,
        expect=200,
    )
    # Corrected values
    req(
        "PUT",
        f"/patients/{pid}/days/{day5.isoformat()}",
        {"mood": 7, "pain": 2, "sleep_hrs": 6.5, "headache": True, "bp_sys": 125, "bp_dia": 80},
        token=token,
        expect=200,
    )

    code, trends = req("GET", f"/trends/{pid}?range=21d", token=token, expect=200)
    point = None
    if isinstance(trends, list):
        point = next((p for p in trends if p.get("day") == day5.isoformat()), None)
    check(point is not None, f"trends has day {day5}")
    if point:
        check(point.get("mood") == 7, f"corrected mood=7 (got {point.get('mood')})")
        check(point.get("headache") is True, f"corrected headache=True (got {point.get('headache')})")
        check(point.get("bp_sys") == 125, f"corrected bp_sys=125 (got {point.get('bp_sys')})")
        check(point.get("bp_dia") == 80, f"corrected bp_dia=80 (got {point.get('bp_dia')})")
        check(point.get("day_postpartum") == 5, f"day_postpartum=5 (got {point.get('day_postpartum')})")

    req(
        "PUT",
        f"/patients/{pid}/days/{future.isoformat()}",
        {"mood": 5},
        token=token,
        expect=422,
    )
    req(
        "PUT",
        f"/patients/{pid}/days/{before.isoformat()}",
        {"mood": 5},
        token=token,
        expect=422,
    )

    code, severe = req(
        "PUT",
        f"/patients/{pid}/days/{today.isoformat()}",
        {"mood": 5, "bp_sys": 165, "bp_dia": 100},
        token=token,
        expect=200,
    )
    check(
        isinstance(severe, dict) and severe.get("red_flag_level") == "emergency",
        f"BP 165/100 today -> emergency (got {severe})",
    )

    req(
        "PUT",
        f"/patients/{MAYA}/days/{today.isoformat()}",
        {"mood": 5},
        token=token,
        expect=403,
    )
    req(
        "PUT",
        f"/patients/{pid}/days/{day5.isoformat()}",
        {"mood": 5},
        expect=401,
    )

    # Demo check-in: reply but Maya trends unchanged
    code, before_maya = req("GET", f"/trends/{MAYA}?range=21d", expect=200)
    maya_snapshot = json.dumps(before_maya, sort_keys=True) if before_maya is not None else ""
    code, checkin = req(
        "POST",
        "/checkin",
        {"patient_id": MAYA, "text": "I slept okay and my mood is about a six today."},
        expect=200,
    )
    check(
        isinstance(checkin, dict) and bool(checkin.get("reply_text")),
        "demo check-in returns a reply",
    )
    code, after_maya = req("GET", f"/trends/{MAYA}?range=21d", expect=200)
    check(
        json.dumps(after_maya, sort_keys=True) == maya_snapshot,
        "Maya trends unchanged after demo check-in",
    )

    # Cleanup (also deletes the user)
    req("DELETE", f"/patients/{pid}", token=token, expect=204)

    print()
    if fails:
        print(f"{fails} failure(s)")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
