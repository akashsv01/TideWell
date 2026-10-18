"""Create the Apple Health test person and send them a week of iPhone data, exactly as the Health Auto
Export app would (POST /wearables/apple-health with their connection code). No iPhone needed.

Run from backend/:
    .venv/Scripts/python scripts/setup_apple_health_test.py              # in-process, real database
    .venv/Scripts/python scripts/setup_apple_health_test.py --url http://localhost:8000
    .venv/Scripts/python scripts/setup_apple_health_test.py --high-bp    # also send 162/112 now, to
                                                                         # show the instant safety alert
    .venv/Scripts/python scripts/setup_apple_health_test.py --reset      # wipe the test person's Apple
                                                                         # Health data first (clean demo)
Then sign in on the website with the login below and tap "Get my Apple Health data".
Safe to re-run: it logs in if the account exists and re-sends the same week (nothing is doubled).
"""
import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Test login (a test account only; not a real person's password).
USERNAME = "applehealth_test"
PASSWORD = "tidewell apple health 1"


def _stamp(t: datetime) -> str:
    """Health Auto Export's date format, in US Eastern (-0400) like a phone in Maryland."""
    return t.astimezone(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d %H:%M:%S %z")


def week_payload(now: datetime, high_bp: bool = False) -> dict:
    """A Health Auto Export JSON body: 7 days of resting heart rate, HRV, steps and sleep, and a cuff BP
    every other morning. Realistic for week 2 after birth: short sleep, BP a little raised but under
    140/90, resting heart rate drifting up."""
    rng = random.Random(7)
    hr, hrv, steps, sleep, bp = [], [], [], [], []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).replace(hour=11, minute=0, second=0, microsecond=0)
        if day > now:
            day = now
        hr.append({"date": _stamp(day), "qty": 64 + (6 - i) + rng.randint(0, 2)})
        hrv.append({"date": _stamp(day), "qty": 52 - (6 - i) * 2 + rng.randint(0, 3)})
        steps.append({"date": _stamp(day), "qty": rng.randint(1500, 4800)})
        sleep.append({"date": _stamp(day), "totalSleep": round(rng.uniform(4.2, 6.2), 2),
                      "core": 2.6, "deep": 0.6, "rem": 0.9})
        if i % 2 == 0:
            bp.append({"date": _stamp(min(day + timedelta(hours=1), now - timedelta(minutes=30))),
                       "systolic": 126 + (6 - i), "diastolic": 80 + (6 - i) // 2})
    if high_bp:
        bp.append({"date": _stamp(now - timedelta(minutes=5)), "systolic": 162, "diastolic": 112})
    return {"data": {"metrics": [
        {"name": "resting_heart_rate", "units": "count/min", "data": hr},
        {"name": "heart_rate_variability", "units": "ms", "data": hrv},
        {"name": "step_count", "units": "count", "data": steps},
        {"name": "sleep_analysis", "units": "hr", "data": sleep},
        {"name": "blood_pressure", "units": "mmHg", "data": bp},
    ]}}


def _reset(patient_id: str) -> None:
    """Remove everything Apple Health added for the test person (needs the database URL in .env)."""
    from app import db, store

    with db.connection() as conn:
        for table in ("wearable_metrics", "health_alerts"):
            conn.execute(f"DELETE FROM {table} WHERE patient_id = %s", (patient_id,))
        for table in ("vitals", "checkins"):
            conn.execute(f"DELETE FROM {table} WHERE patient_id = %s AND source LIKE 'apple_health%%'", (patient_id,))
    store.refresh_all()
    print("Test person's Apple Health data cleared.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="a running backend; default runs in-process")
    ap.add_argument("--high-bp", action="store_true", help="also send an unsafe 162/112 reading from now")
    ap.add_argument("--reset", action="store_true", help="delete the test person's Apple Health data first")
    args = ap.parse_args()

    if args.url:
        import httpx

        c = httpx.Client(base_url=args.url.rstrip("/"), timeout=60)
    else:
        from fastapi.testclient import TestClient

        from app.main import app

        c = TestClient(app)

    r = c.post("/auth/login", json={"username": USERNAME, "password": PASSWORD})
    if r.status_code != 200:
        r = c.post("/auth/register", json={"username": USERNAME, "password": PASSWORD})
        r.raise_for_status()
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    me = c.get("/auth/me", headers=h).json()
    if not me.get("patient_id"):
        today = datetime.now(timezone.utc).date()
        c.post("/onboard", headers=h, json={
            "consent_granted": True, "name": "Jordan", "delivery_date": str(today - timedelta(days=12)),
            "delivery_method": "vaginal", "feeding_type": "breastfeeding",
            "history_pregnancy_complications": [], "language_preference": "en"}).raise_for_status()

    if args.reset:
        _reset(c.get("/auth/me", headers=h).json()["patient_id"])
    code = c.post("/wearables/token", headers=h).json()["code"]  # what the iPhone app would hold
    body = week_payload(datetime.now(timezone.utc), high_bp=args.high_bp)
    r = c.post("/wearables/apple-health", headers={"Authorization": f"Bearer {code}"}, json=body)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))
    print(f"\nTest person ready. Sign in as '{USERNAME}' (password in this script) and tap "
          "'Get my Apple Health data' on the Check in page.")
    if args.high_bp:
        print("An unsafe reading (162/112) was sent: the website shows the urgent card within a minute.")


if __name__ == "__main__":
    main()
