from datetime import datetime, timedelta, timezone

from app.agents import watch
from app.schemas import Profile


def _mood_tier(last_epds: dict | None, history: bool | None = None) -> str:
    tiers = watch.assess(
        profile={"delivery_method": "vaginal", "history_mental_health": history},
        points=[],
        last_epds=last_epds,
        last_checkin=None,
    )
    return next(t["tier"] for t in tiers if t["category"] == "depression_anxiety")


def test_epds_score_only_affects_current_tier_for_seven_days():
    now = datetime.now(timezone.utc)

    assert _mood_tier({"time": now - timedelta(days=6), "score": 13, "item10": 0}) == "amber"
    assert _mood_tier({"time": now - timedelta(days=8), "score": 13, "item10": 0}) == "green"


def test_epds_item_ten_only_affects_current_tier_for_seven_days():
    now = datetime.now(timezone.utc)

    assert _mood_tier({"time": now - timedelta(days=6), "score": 0, "item10": 1}) == "amber"
    assert _mood_tier({"time": now - timedelta(days=8), "score": 0, "item10": 1}) == "green"


def test_epds_freshness_boundary_is_exactly_seven_days():
    now = datetime.now(timezone.utc)

    assert watch._epds_is_current({"time": now - timedelta(days=7)}, now)
    assert not watch._epds_is_current({"time": now - timedelta(days=7, seconds=1)}, now)


def test_unknown_history_is_not_scored_as_positive_or_negative():
    assert _mood_tier(None, history=None) == "green"
    assert _mood_tier(None, history=False) == "green"
    assert _mood_tier(None, history=True) == "watch"


def test_profile_preserves_unknown_mental_health_history():
    profile = Profile(
        consent_granted=True,
        delivery_date="2026-10-01",
        delivery_method="vaginal",
        feeding_type="formula",
        history_mental_health=None,
    )

    assert profile.history_mental_health is None
