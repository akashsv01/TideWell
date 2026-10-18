"""Username/password accounts with server-side sessions.

- Passwords: scrypt (Python stdlib, memory-hard), random 16-byte salt, stored as
  "scrypt$N$r$p$salt_b64$hash_b64". Plain passwords are never stored or logged.
- Sessions: a random 32-byte token goes to the client (Authorization: Bearer <token>); only its
  SHA-256 is stored, so a database leak does not leak live sessions. Logout deletes the row.
- Access: every patient-scoped route calls authorize_patient(). The demo patient (Maya) is open to
  everyone without a login; any other patient is readable only by the account that owns it.
"""
import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException

from app import db, demo_data

SESSION_DAYS = 30
_N, _R, _P = 2**14, 8, 1  # scrypt cost: ~16 MB, ~50 ms per hash


# --- Passwords -------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r),
                                p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# A real-looking hash for unknown usernames, so login takes the same time whether or not the
# account exists (no username probing by timing).
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# --- Users and sessions ------------------------------------------------------------------
@dataclass(frozen=True)
class User:
    id: UUID
    username: str
    patient_id: Optional[UUID]


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(username: str, password: str, email: Optional[str] = None) -> Optional[User]:
    """None if the username is taken (case-insensitive)."""
    with db.connection() as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(username) = lower(%s)", (username,)).fetchone():
            return None
        row = conn.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s) RETURNING id",
            (username, hash_password(password), email.strip().lower() if email else None),
        ).fetchone()
    return User(id=row["id"], username=username, patient_id=None)


def check_login(username: str, password: str) -> Optional[User]:
    with db.connection() as conn:
        row = conn.execute(
            """SELECT u.id, u.username, u.password_hash, p.id AS patient_id
               FROM users u LEFT JOIN patients p ON p.user_id = u.id
               WHERE lower(u.username) = lower(%s)""",
            (username,),
        ).fetchone()
    if not row:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return User(id=row["id"], username=row["username"], patient_id=row["patient_id"])


def create_session(user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
            (_token_hash(token), user_id, datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = %s AND expires_at < now()", (user_id,))
    return token


def end_session(token: str) -> None:
    with db.connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = %s", (_token_hash(token),))


def user_for_token(token: str) -> Optional[User]:
    with db.connection() as conn:
        row = conn.execute(
            """SELECT u.id, u.username, p.id AS patient_id
               FROM sessions s JOIN users u ON u.id = s.user_id
               LEFT JOIN patients p ON p.user_id = u.id
               WHERE s.token_hash = %s AND s.expires_at > now()""",
            (_token_hash(token),),
        ).fetchone()
    return User(id=row["id"], username=row["username"], patient_id=row["patient_id"]) if row else None


def delete_user(user_id: UUID) -> None:
    """Deletes the account; sessions go with it (ON DELETE CASCADE)."""
    with db.connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))


# --- FastAPI dependencies ------------------------------------------------------------------
def bearer_token(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[User]:
    token = bearer_token(authorization)
    if not token or not db.enabled():
        return None
    return user_for_token(token)


def require_user(authorization: Optional[str] = Header(default=None)) -> User:
    user = optional_user(authorization)
    if user is None:
        raise HTTPException(401, "sign in required", headers={"WWW-Authenticate": "Bearer"})
    return user


def is_demo(patient_id: UUID) -> bool:
    return patient_id == demo_data.MAYA_ID


def authorize_patient(patient_id: UUID, user: Optional[User]) -> None:
    """Raise unless this caller may read/write this patient: the demo, or the owner's account."""
    if is_demo(patient_id):
        return
    if user is None:
        raise HTTPException(401, "sign in required", headers={"WWW-Authenticate": "Bearer"})
    if user.patient_id != patient_id:
        raise HTTPException(403, "this record belongs to another account")
