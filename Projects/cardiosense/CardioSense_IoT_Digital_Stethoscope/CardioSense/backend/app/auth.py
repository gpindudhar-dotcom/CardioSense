"""Cookie-backed user authentication for the CardioSense prototype."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserSession, utc_now

SESSION_COOKIE = "cardiosense_session"
SESSION_DAYS = 7
PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "0").lower() in {"1", "true", "yes"},
        samesite="strict",
        max_age=SESSION_DAYS * 24 * 60 * 60,
        path="/",
    )


def create_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            token_hash=token_digest(token),
            user_id=user.id,
            expires_at=utc_now() + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    set_session_cookie(response, token)


def get_user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.query(UserSession).filter_by(token_hash=token_digest(token)).first()
    if not session or session.expires_at <= utc_now():
        if session:
            db.delete(session)
            db.commit()
        return None
    return db.get(User, session.user_id)


def get_current_user(
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    user = get_user_for_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    return user


def require_role(user: User, role: str) -> None:
    if user.role != role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{role.title()} access required.")


def clear_session(db: Session, token: str | None, response: Response) -> None:
    if token:
        session = db.query(UserSession).filter_by(token_hash=token_digest(token)).first()
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="strict")
