"""Send one test email through Resend and print exactly what Resend answers.
Run from backend/:  python scripts/test_email.py
Use it when the doctor email does not arrive: it shows whether the key, the sender and the address are accepted."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402


def main() -> None:
    s = get_settings()
    key = s.resend_api_key
    print("RESEND_API_KEY :", f"set ({key[:5]}...{key[-3:]}, {len(key)} characters)" if key else "EMPTY")
    print("DOCTOR_EMAIL   :", s.doctor_email or "EMPTY")
    print("RESEND_FROM    :", s.resend_from)
    if not key or not s.doctor_email:
        sys.exit("\nFill in RESEND_API_KEY and DOCTOR_EMAIL in backend/.env (no quotes, no spaces around =), then run this again.")
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {key}"},
        json={"from": s.resend_from, "to": [s.doctor_email], "subject": "Tidewell test email",
              "text": "If you can read this, Tidewell can email the doctor."},
        timeout=15.0,
    )
    print("\nResend answered:", r.status_code)
    print(r.text)
    if r.status_code in (200, 201):
        print("\nSent. Check the inbox (and spam) of", s.doctor_email)
    elif r.status_code == 403 and "own email" in r.text.lower():
        print("\nWith the free test sender (onboarding@resend.dev), Resend only delivers to the email address of your own Resend account.")
        print("Set DOCTOR_EMAIL to that address, or verify a domain at resend.com/domains and set RESEND_FROM to an address on it.")
    elif r.status_code in (401, 403):
        print("\nResend rejected the key or the sender. Check the API key (create one with 'Sending access') and RESEND_FROM.")


if __name__ == "__main__":
    main()
