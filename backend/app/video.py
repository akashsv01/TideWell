"""Video rooms for virtual visits.

Primary: Daily (https://docs.daily.co/reference/rest-api). One private room per appointment, joined with a
short-lived meeting token that is minted when the patient taps "Join" (so no long-lived link is stored).
Default when DAILY_API_KEY is empty or Daily is unreachable: Tidewell's own WebRTC video server (video-server/,
Flask-SocketIO). The room is just an unguessable name; the page lives at WEBRTC_BASE_URL and opens in a new tab.
Rooms booked earlier with Jitsi keep working: their stored link is used as is.

Never raises into a booking: a failed room creation falls back to WebRTC, it does not lose the appointment.
The seeded demo uses synthetic data only. For real patients use a provider that signs a HIPAA BAA
(Daily offers one on its healthcare plans) and review privacy settings first.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import get_settings

log = logging.getLogger("tidewell.video")

DAILY_API = "https://api.daily.co/v1"
EARLY = timedelta(minutes=15)   # people can join this long before the start time
LATE = timedelta(hours=2)       # and this long after it
_TIMEOUT = 8.0


def _room_name() -> str:
    # Letters, digits and dashes only; unguessable because it is the only thing a stranger would need.
    return "tw-" + secrets.token_urlsafe(12).replace("_", "x")


def window(slot: datetime) -> tuple[datetime, datetime]:
    return slot - EARLY, slot + LATE


def create_room(slot: datetime) -> dict:
    """Returns {provider, room, url}. provider is "daily" or "webrtc"."""
    key = get_settings().daily_api_key
    name = _room_name()
    if key:
        opens, closes = window(slot)
        try:
            r = httpx.post(
                f"{DAILY_API}/rooms",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "name": name,
                    "privacy": "private",
                    "properties": {
                        "nbf": int((opens - timedelta(minutes=15)).timestamp()),
                        "exp": int(closes.timestamp()),
                        "max_participants": 6,
                        "enable_prejoin_ui": True,
                        "enable_chat": True,
                        "eject_at_room_exp": True,
                    },
                },
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            return {"provider": "daily", "room": data["name"], "url": data["url"]}
        except Exception as e:  # noqa: BLE001
            log.warning("Daily room creation failed (%s: %s); using WebRTC instead", type(e).__name__, e)
    return {"provider": "webrtc", "room": name, "url": _webrtc_base()}


def _frontend_origin() -> str:
    return (get_settings().frontend_origins.split(",")[0].strip() or "http://localhost:3000").rstrip("/")


def _webrtc_base() -> str:
    return get_settings().webrtc_base_url.rstrip("/")


def join_url(meeting: dict, slot: datetime, display_name: Optional[str], owner: bool = False) -> str:
    """The URL to open for this room. Daily rooms are private, so this mints a token (raises on failure)."""
    if meeting["provider"] == "webrtc":
        # Built now from the current setting, so a changed ngrok address does not break booked visits.
        q = {"room": meeting["room"], "role": "provider" if owner else "patient"}
        if not owner:  # when the patient leaves, the video page sends them back to their visits
            q["return"] = _frontend_origin() + "/visits"
        return f"{_webrtc_base()}/?{urlencode(q)}"
    if meeting["provider"] != "daily":
        return meeting["url"]  # a visit booked earlier with another service
    key = get_settings().daily_api_key
    if not key:
        raise RuntimeError("Daily is not configured")
    _, closes = window(slot)
    props: dict = {
        "room_name": meeting["room"],
        "is_owner": owner,
        "exp": int(min(closes, datetime.now(timezone.utc) + LATE).timestamp()),
    }
    if display_name:
        props["user_name"] = display_name[:60]
    r = httpx.post(
        f"{DAILY_API}/meeting-tokens",
        headers={"Authorization": f"Bearer {key}"},
        json={"properties": props},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return f"{meeting['url']}?t={r.json()['token']}"
