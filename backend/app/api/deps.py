from datetime import datetime, timezone

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_token
from app.db.models import SessionRecord, User
from app.db.session import get_db

settings = get_settings()


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = db.scalar(
        select(SessionRecord).where(
            SessionRecord.token_hash == hash_token(session_token),
            SessionRecord.revoked_at.is_(None),
            SessionRecord.expires_at > datetime.now(timezone.utc),
        )
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return session.user


def require_csrf(
    csrf_cookie: str | None = Cookie(default=None, alias=settings.csrf_cookie_name),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")