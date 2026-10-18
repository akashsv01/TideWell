"""Email the doctor a join link when a video visit is booked (or cancelled), through Resend.

One inbox for every doctor (DOCTOR_EMAIL) for now. The link in the email is a Tidewell link,
{PUBLIC_API_URL}/visits/doctor/<room>, not the video page itself: when it is opened, the backend checks the
visit is still booked and inside its time window, then sends the doctor on to the video room (for Daily it
mints the doctor's meeting token at that moment, so the emailed link never goes stale).

Never raises into a booking: with no key or address configured it logs and does nothing, and a failed send is
only logged. It runs on a background thread so booking stays fast. Demo data only: the email names the
provider, the time and the reason the patient typed, never the patient's name or contact details.
"""
import html
import logging
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.config import get_settings

log = logging.getLogger("tidewell.mail")

RESEND_API = "https://api.resend.com/emails"
CLINIC_TZ = ZoneInfo("America/New_York")


def _run(fn) -> None:  # tests replace this to run synchronously
    threading.Thread(target=fn, daemon=True).start()


def doctor_link(room: str) -> str:
    base = get_settings().public_api_url.rstrip("/") or "http://localhost:8000"
    return f"{base}/visits/doctor/{room}"


def _when(slot: datetime) -> str:
    return slot.astimezone(CLINIC_TZ).strftime("%A, %B %d at %I:%M %p %Z").replace(" 0", " ")


def build(event: str, visit: dict, room: str) -> dict:
    """event: "booked" or "cancelled". visit is the VisitOut-shaped dict from app/booking.py."""
    p, when = visit["provider"], _when(visit["slot"])
    reason = (visit.get("reason") or "").strip()[:300]
    if event == "cancelled":
        subject = f"Video visit cancelled: {when}"
        lines = [f"The video visit with {p['name']} on {when} was cancelled. The link from the earlier email no longer works."]
        link = None
    else:
        subject = f"New video visit: {when}"
        link = doctor_link(room)
        lines = [
            f"A patient booked a video visit with {p['name']} ({p['specialty']}).",
            f"When: {when}",
            f"Reason: {reason}" if reason else "Reason: not given",
            "Your join link opens 15 minutes before the visit:",
        ]
    text = "\n".join(lines + ([link] if link else [])) + "\n\nTidewell"
    body = "".join(f'<p style="margin:0 0 12px">{html.escape(l)}</p>' for l in lines)
    if link:
        body += (f'<p style="margin:20px 0"><a href="{html.escape(link)}" style="background:#0e6a70;color:#fff;'
                 'padding:14px 28px;border-radius:999px;text-decoration:none;font-weight:600">Join the video visit</a></p>'
                 f'<p style="margin:0;color:#44546a;font-size:14px">Or paste this into your browser: {html.escape(link)}</p>')
    page = ('<div style="font-family:Arial,sans-serif;color:#0b2545;background:#f4f9f9;padding:24px">'
            '<div style="max-width:520px;margin:auto;background:#fff;border-radius:16px;padding:28px">'
            '<p style="font-size:22px;color:#0e6a70;margin:0 0 16px;font-weight:700">Tidewell</p>'
            f"{body}</div></div>")
    return {"subject": subject, "text": text, "html": page}


def send(event: str, visit: dict, room: str) -> bool:
    s = get_settings()
    if not (s.resend_api_key and s.doctor_email):
        log.warning("Doctor email not sent: RESEND_API_KEY or DOCTOR_EMAIL is empty in backend/.env (restart the backend after editing it)")
        return False
    msg = build(event, visit, room)
    try:
        r = httpx.post(
            RESEND_API,
            headers={"Authorization": f"Bearer {s.resend_api_key}"},
            json={"from": s.resend_from, "to": [s.doctor_email], **msg},
            timeout=10.0,
        )
        if r.status_code >= 400:
            log.warning("Doctor email failed: Resend answered %s %s", r.status_code, r.text[:300])
            return False
        log.warning("Doctor email sent to %s (Resend id %s)", s.doctor_email, (r.json() or {}).get("id"))
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("Doctor email failed (%s: %s)", type(e).__name__, e)
        return False


def notify(event: str, visit: dict, room: str) -> None:
    """Fire and forget. Only video visits have a link to send."""
    if visit.get("mode") != "virtual" or not room:
        return
    _run(lambda: send(event, visit, room))
