from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_csrf
from app.core.config import get_settings
from app.core.security import create_token
from app.db.models import User
from app.db.session import get_db
from app.features.auth.schemas import Credentials, CsrfResponse, UserResponse
from app.features.auth.service import authenticate_user, create_session, register_user, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_ttl_seconds,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_ttl_seconds,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, response: Response, db: Session = Depends(get_db)) -> User:
    user = register_user(db, str(credentials.email), credentials.password)
    if user is None:
        return Response(status_code=status.HTTP_409_CONFLICT)
    session_token = create_session(db, user, settings.session_ttl_seconds)
    set_auth_cookies(response, session_token, create_token())
    return user


@router.post("/login", response_model=UserResponse)
def login(credentials: Credentials, response: Response, db: Session = Depends(get_db)) -> User:
    user = authenticate_user(db, str(credentials.email), credentials.password)
    if user is None:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    session_token = create_session(db, user, settings.session_ttl_seconds)
    set_auth_cookies(response, session_token, create_token())
    return user


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/csrf", response_model=CsrfResponse)
def csrf(response: Response) -> CsrfResponse:
    token = create_token()
    response.set_cookie(settings.csrf_cookie_name, token, httponly=False, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    return CsrfResponse(token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def logout(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    del user
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(settings.csrf_cookie_name)