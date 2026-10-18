"""Smartwatch data: parse Health Auto Export payloads and turn daily watch data into gentle nudges.

Pure functions, no I/O (the route in app/routes/wearables.py does the storing).

Health Auto Export (iOS app, Premium) -> "REST API" automation, export format JSON. Its payload is
    {"data": {"metrics": [{"name": "resting_heart_rate", "units": "count/min",
                           "data": [{"date": "2026-10-17 07:00:00 -0400", "qty": 64, "source": "..."}]}, ...],
              "workouts": [...]}}
The parser is deliberately tolerant (key casing, date formats, °F/°C, fractions vs percent, aggregated
or per-stage sleep) because the exact shape depends on the app version and the automation settings.
Anything it does not recognise is reported back as "ignored", never guessed at.

SAFETY RULE: watch data never raises a red flag on its own. Watch metrics only produce nudges
("your resting heart rate is higher than usual, want to check in?"); the voice check-in and the fixed
rules decide. The one exception is blood pressure from a real cuff synced through Apple Health: that is
a measured reading, so the route runs it through the same fixed BP rules as a typed reading, the
moment it arrives (app/routes/wearables.py).

Written by Sreeja (person2-backend); sample_week() added for the website's no-phone demo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from statistics import mean, median
from typing import Any, Iterable, Optional

# Health Auto Export metric name -> TideWell metric name.
METRIC_MAP = {
    "heart_rate": "heart_rate",
    "resting_heart_rate": "resting_hr",
    "heart_rate_variability": "hrv_ms",
    "heart_rate_variability_sdnn": "hrv_ms",
    "step_count": "steps",
    "blood_oxygen_saturation": "spo2",
    "oxygen_saturation": "spo2",
    "respiratory_rate": "resp_rate",
    "apple_sleeping_wrist_temperature": "wrist_temp_c",
    "sleeping_wrist_temperature": "wrist_temp_c",
    "body_temperature": "body_temp_c",
}
SLEEP_NAMES = {"sleep_analysis"}
BP_NAMES = {"blood_pressure"}

# Plausible ranges. A value outside them is a sensor or unit error and is dropped, not stored.
RANGES = {
    "heart_rate": (30, 230),
    "resting_hr": (30, 150),
    "hrv_ms": (1, 300),
    "steps": (0, 100_000),
    "spo2": (50, 100),
    "resp_rate": (4, 60),
    "wrist_temp_c": (30, 43),
    "body_temp_c": (30, 43),
    "sleep_hrs": (0, 24),
}
_ASLEEP_STAGES = {"asleep", "core", "deep", "rem", "asleepcore", "asleepdeep", "asleeprem", "asleepunspecified"}


@dataclass(frozen=True)
class Sample:
    time: datetime
    metric: str
    value: float


@dataclass(frozen=True)
class BpReading:
    time: datetime
    sys: int
    dia: int


@dataclass
class ParseResult:
    samples: list[Sample] = field(default_factory=list)
    bp: list[BpReading] = field(default_factory=list)
    recognized: dict[str, int] = field(default_factory=dict)  # TideWell metric -> points kept
    ignored: list[str] = field(default_factory=list)          # Health Auto Export names not used
    rejected: int = 0                                         # points dropped as unreadable/implausible


# --- Parsing helpers ---------------------------------------------------------------------
_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M %z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def parse_date(raw: Any) -> Optional[datetime]:
    """'2026-10-17 07:00:00 -0400', ISO 8601 ('...T07:00:00-04:00' or 'Z') or a bare date. Naive -> UTC."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue
    else:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _num(point: dict, *keys: str) -> Optional[float]:
    """First numeric value among keys, matched case-insensitively."""
    lower = {str(k).lower(): v for k, v in point.items()}
    for k in keys:
        v = lower.get(k.lower())
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                continue
    return None


def _norm_name(name: Any) -> str:
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def _to_celsius(value: float, units: str) -> float:
    u = units.strip().lower()
    if u in ("degf", "°f", "f", "fahrenheit") or value > 50:  # >50 can only be °F for a body temperature
        return (value - 32) * 5 / 9
    return value


def _sleep_hours(point: dict, units: str) -> Optional[tuple[datetime, float]]:
    """Aggregated rows carry totalSleep/asleep (or core+deep+rem); per-stage rows carry
    startDate/endDate + value ('Core', 'Deep', 'REM', 'Awake', 'In Bed'). Awake and in-bed time
    are not sleep."""
    in_minutes = units.lower().startswith("min")
    total = _num(point, "totalSleep", "asleep")
    if total is None:
        stages = [_num(point, k) for k in ("core", "deep", "rem")]
        if any(s is not None for s in stages):
            total = sum(s or 0 for s in stages)
    if total is not None:
        when = parse_date(point.get("date")) or parse_date(point.get("sleepEnd")) or parse_date(point.get("endDate"))
        return (when, total / 60 if in_minutes else total) if when else None

    stage = str(point.get("value", "")).lower().replace(" ", "").replace("_", "")
    start, end = parse_date(point.get("startDate")), parse_date(point.get("endDate"))
    if stage in _ASLEEP_STAGES and start and end and end > start:
        return end, (end - start).total_seconds() / 3600
    return None


def _in_range(metric: str, value: float) -> bool:
    lo, hi = RANGES.get(metric, (float("-inf"), float("inf")))
    return lo <= value <= hi


def parse_health_auto_export(payload: Any) -> ParseResult:
    out = ParseResult()
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    metrics = data.get("metrics", []) if isinstance(data, dict) else []
    if not isinstance(metrics, list):
        return out
    ignored: set[str] = set()
    per_stage_sleep: dict[date, list[tuple[datetime, float]]] = {}

    for m in metrics:
        if not isinstance(m, dict):
            continue
        name = _norm_name(m.get("name"))
        units = str(m.get("units") or "")
        points = m.get("data") or []
        if not isinstance(points, list):
            continue

        if name in BP_NAMES:
            for p in points:
                when, s, d = parse_date(p.get("date")), _num(p, "systolic"), _num(p, "diastolic")
                if when and s is not None and d is not None and 60 <= s <= 260 and 30 <= d <= 180 and d < s:
                    out.bp.append(BpReading(when, round(s), round(d)))
                else:
                    out.rejected += 1
            if out.bp:
                out.recognized["blood_pressure"] = len(out.bp)
            continue

        if name in SLEEP_NAMES:
            for p in points:
                got = _sleep_hours(p, units) if isinstance(p, dict) else None
                if got is None:
                    continue  # awake / in-bed stage rows are expected, not errors
                when, hours = got
                if "startDate" in p and "totalSleep" not in p and "asleep" not in p:
                    per_stage_sleep.setdefault(when.date(), []).append((when, hours))
                elif _in_range("sleep_hrs", hours):
                    out.samples.append(Sample(when, "sleep_hrs", round(hours, 2)))
                    out.recognized["sleep_hrs"] = out.recognized.get("sleep_hrs", 0) + 1
                else:
                    out.rejected += 1
            continue

        metric = METRIC_MAP.get(name)
        if metric is None:
            ignored.add(name or "(unnamed)")
            continue
        for p in points:
            if not isinstance(p, dict):
                out.rejected += 1
                continue
            when = parse_date(p.get("date"))
            value = _num(p, "Avg", "qty", "value") if metric == "heart_rate" else _num(p, "qty", "value", "Avg")
            if when is None or value is None:
                out.rejected += 1
                continue
            if metric == "spo2" and value <= 1:
                value *= 100  # some exports send 0.97 for 97 %
            if metric in ("wrist_temp_c", "body_temp_c"):
                value = _to_celsius(value, units)
            if not _in_range(metric, value):
                out.rejected += 1
                continue
            out.samples.append(Sample(when, metric, round(value, 2)))
            out.recognized[metric] = out.recognized.get(metric, 0) + 1

    # Per-stage sleep rows: one total per night, stamped at the last stage's end.
    for _, parts in per_stage_sleep.items():
        hours = sum(h for _, h in parts)
        if _in_range("sleep_hrs", hours):
            out.samples.append(Sample(max(t for t, _ in parts), "sleep_hrs", round(hours, 2)))
            out.recognized["sleep_hrs"] = out.recognized.get("sleep_hrs", 0) + 1

    out.ignored = sorted(ignored)
    return out


# --- Nudges --------------------------------------------------------------------------------
# PLACEHOLDER THRESHOLDS: these are conservative product heuristics for when to *ask* how someone
# feels, not clinical cutoffs. They need clinician review before real use (like thresholds.md).
BASELINE_MIN_DAYS = 4   # need this many earlier days before comparing against a personal baseline
RECENT_DAYS = 3
RESTING_HR_RISE = 10     # bpm above her own baseline
HRV_DROP = 0.75          # recent average at or below 75 % of her baseline
TEMP_RISE_C = 0.5        # °C above her own baseline (Apple's sleeping wrist temperature)
LOW_SLEEP_HRS = 4.0
LOW_SPO2 = 94.0


def _series(days: list[dict], key: str) -> list[float]:
    return [float(d[key]) for d in days if d.get(key) is not None]


def _split(days: list[dict], key: str) -> tuple[list[float], list[float]]:
    """Baseline = days before the most recent RECENT_DAYS days that have this metric."""
    with_values = [d for d in days if d.get(key) is not None]
    recent = with_values[-RECENT_DAYS:]
    earlier = with_values[:-RECENT_DAYS]
    return _series(earlier, key), _series(recent, key)


def nudges(days: Iterable[dict]) -> list[dict]:
    """days: oldest first, each {"day", "resting_hr", "hrv_ms", "steps", "sleep_hrs", "spo2", "wrist_temp_c", ...}.
    Returns friendly prompts to check in. Never a diagnosis, never a red flag."""
    days = list(days)
    out: list[dict] = []

    def add(metric: str, kind: str, message: str, recent: float, baseline: Optional[float]) -> None:
        out.append({"metric": metric, "kind": kind, "message": message,
                    "recent": round(recent, 1), "baseline": None if baseline is None else round(baseline, 1)})

    base, recent = _split(days, "resting_hr")
    if len(base) >= BASELINE_MIN_DAYS and len(recent) == RECENT_DAYS:
        b, r = median(base), mean(recent)
        if r >= b + RESTING_HR_RISE:
            add("resting_hr", "resting_hr_up",
                f"Your resting heart rate has been about {round(r - b)} beats a minute higher than your usual "
                f"for the last {RECENT_DAYS} days. How are you feeling? A quick check-in helps.", r, b)

    base, recent = _split(days, "hrv_ms")
    if len(base) >= BASELINE_MIN_DAYS and len(recent) == RECENT_DAYS:
        b, r = median(base), mean(recent)
        if b > 0 and r <= b * HRV_DROP:
            add("hrv_ms", "hrv_down",
                "Your watch shows your body has been under more strain than usual this week. "
                "Rest when you can, and tell TideWell how you're doing.", r, b)

    base, recent = _split(days, "wrist_temp_c")
    if len(base) >= BASELINE_MIN_DAYS and recent:
        b, r = median(base), max(recent)
        if r >= b + TEMP_RISE_C:
            add("wrist_temp_c", "temp_up",
                "Your temperature during sleep was higher than your usual. If you have a thermometer, "
                "take your temperature now. 100.4°F (38°C) or higher after giving birth needs a call to your provider.",
                r, b)

    _, recent = _split(days, "sleep_hrs")
    if len(recent) == RECENT_DAYS and mean(recent) < LOW_SLEEP_HRS:
        add("sleep_hrs", "sleep_low",
            f"You've averaged {mean(recent):.1f} hours of sleep over the last {RECENT_DAYS} nights. "
            "That's really hard. Could someone take one night feed so you get a longer stretch?", mean(recent), None)

    _, recent = _split(days, "spo2")
    low = [v for v in recent if v <= LOW_SPO2]
    if len(low) >= 2:
        add("spo2", "spo2_low",
            "Your watch read lower blood oxygen than usual on more than one day. Watch readings can be off, "
            "but if you feel short of breath, call your provider. If it's severe, call 911.", min(low), None)
    return out


# --- Sample data (website, no iPhone connected) -------------------------------------------------
def sample_week(now: datetime, seed: str, days: int = 7) -> tuple[list[Sample], list[BpReading]]:
    """A week of believable Apple Health data for someone with no phone connected, in NORMAL ranges
    on purpose: sample numbers must never trigger an urgent card or a visit suggestion. Stable for a
    given patient (seeded), so re-running the import gives the same week.

    Times are UTC: resting heart rate at 11:00, sleep ending 11:00 (the morning after), steps and
    HRV at 12:00, and one cuff reading at 13:00 every other day. Nothing later than `now`."""
    import random

    rng = random.Random(seed)
    samples: list[Sample] = []
    bp: list[BpReading] = []
    for i in range(days - 1, -1, -1):
        d = now.date().toordinal() - i
        day = date.fromordinal(d)
        at = lambda h: datetime(day.year, day.month, day.day, h, tzinfo=timezone.utc)  # noqa: E731
        samples += [
            Sample(at(11), "resting_hr", float(rng.randint(62, 70))),
            Sample(at(11), "sleep_hrs", round(rng.uniform(5.0, 7.0), 1)),
            Sample(at(12), "hrv_ms", float(rng.randint(42, 58))),
            Sample(at(12), "steps", float(rng.randint(1800, 5200))),
        ]
        if i % 2 == 0:
            bp.append(BpReading(at(13), rng.randint(112, 124), rng.randint(70, 79)))
    return [x for x in samples if x.time <= now], [x for x in bp if x.time <= now]
