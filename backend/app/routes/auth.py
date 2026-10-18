"""POST /auth/register, POST /auth/login, POST /auth/logout, GET /auth/me."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from app import auth, db
from app.schemas_data import AccountOut, AuthOut, Credentials

router = APIRouter(prefix="/auth")


def _need_db() -> None:
    if not db.enabled():
        raise HTTPException(503, "accounts need the database (TIGER_DATABASE_URL)")


@router.post("/register", response_model=AuthOut, status_code=201)
def register(body: Credentials) -> AuthOut:
    _need_db()
    user = auth.create_user(body.username, body.password)
    if user is None:
        raise HTTPException(409, "that username is taken")
    return AuthOut(token=auth.create_session(user.id), username=user.username, patient_id=None)


@router.post("/login", response_model=AuthOut)
def login(body: Credentials) -> AuthOut:
    _need_db()
    user = auth.check_login(body.username, body.password)
    if user is None:
        # Same message for unknown user and wrong password: don't reveal which usernames exist.
        raise HTTPException(401, "wrong username or password")
    return AuthOut(token=auth.create_session(user.id), username=user.username, patient_id=user.patient_id)


@router.post("/logout", status_code=204)
def logout(authorization: Optional[str] = Header(default=None)) -> Response:
    token = auth.bearer_token(authorization)
    if token and db.enabled():
        auth.end_session(token)
    return Response(status_code=204)


@router.get("/me", response_model=AccountOut)
def me(user: auth.User = Depends(auth.require_user)) -> AccountOut:
    return AccountOut(username=user.username, patient_id=user.patient_id)
