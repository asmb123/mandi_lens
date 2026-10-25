from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, hash_token, verify_password
from app.db.models import SessionRecord, User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(db: Session, email: str, password: str) -> User | None:
    normalized_email = normalize_email(email)
    if db.scalar(select(User).where(User.email == normalized_email)):
        return None
    user = User(email=normalized_email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: User, ttl_seconds: int) -> str:
    token = create_token()
    session = SessionRecord(
        token_hash=hash_token(token),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
    )
    db.add(session)
    db.commit()
    return token


def revoke_session(db: Session, token: str) -> None:
    session = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == hash_token(token)))
    if session:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()