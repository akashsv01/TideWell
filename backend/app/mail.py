"""Welcome email to a new account, through Resend (same key as the doctor emails in provider_mail.py).

Never raises into registration: with no key configured it logs and does nothing, and a failed send is only
logged. It runs on a background thread so creating an account stays fast. Fixed text, no health data.
"""
import html
import logging
import threading

import httpx

from app.config import get_settings

log = logging.getLogger("tidewell.mail")

RESEND_API = "https://api.resend.com/emails"


def _run(fn) -> None:  # tests replace this to run synchronously
    threading.Thread(target=fn, daemon=True).start()


def build_welcome(username: str) -> dict:
    lines = [
        f"Hi {username}, welcome to Tidewell.",
        "Tidewell is a one-minute check-in for the year after birth. Talk or type how you are, and it keeps "
        "your mood, sleep, pain and blood pressure in one picture, so you and your care team can see what is changing.",
        "Next: answer a few questions about your birth (about two minutes), then do your first check-in.",
        "Tidewell does not diagnose. If something feels like an emergency, call 911. If you are thinking of "
        "harming yourself or your baby, call or text 988 any time.",
        "You can delete your account and everything in it at any time in Settings.",
    ]
    text = "\n\n".join(lines) + "\n\nTidewell"
    body = "".join(f'<p style="margin:0 0 14px;line-height:1.55">{html.escape(l)}</p>' for l in lines)
    page = ('<div style="font-family:Arial,sans-serif;color:#1b2a22;background:#f7f1e4;padding:24px">'
            '<div style="max-width:520px;margin:auto;background:#fffdf8;border-radius:16px;padding:28px">'
            '<p style="font-family:Georgia,serif;font-size:24px;color:#23463a;margin:0 0 18px;font-weight:700">Tidewell</p>'
            f"{body}</div></div>")
    return {"subject": "Welcome to Tidewell", "text": text, "html": page}


def send_welcome(email: str, username: str) -> bool:
    s = get_settings()
    if not s.resend_api_key:
        log.warning("Welcome email not sent: RESEND_API_KEY is empty in backend/.env")
        return False
    try:
        r = httpx.post(
            RESEND_API,
            headers={"Authorization": f"Bearer {s.resend_api_key}"},
            json={"from": s.resend_from, "to": [email], **build_welcome(username)},
            timeout=10.0,
        )
        if r.status_code >= 400:
            log.warning("Welcome email failed: Resend answered %s %s", r.status_code, r.text[:300])
            return False
        log.info("Welcome email sent (Resend id %s)", (r.json() or {}).get("id"))  # address not logged
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("Welcome email failed (%s: %s)", type(e).__name__, e)
        return False


def welcome(email: str, username: str) -> None:
    """Fire and forget."""
    _run(lambda: send_welcome(email, username))
