from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ... import db, crud, schemas, auth
from ...config import settings
from ...email import send_email, build_verification_email, build_password_reset_email
from ...limiter import limiter

router = APIRouter()


@router.post("/register", response_model=schemas.UserRead)
@limiter.limit(settings.register_rate_limit)
def register(request: Request, user_in: schemas.UserCreate, db: Session = Depends(db.get_db)):
    existing = crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        user = crud.create_user(db, user_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token, _ = crud.create_email_verification_token(db, user.id)
    subject, body = build_verification_email(token)
    send_email(user.email, subject, body)
    crud.create_auth_event(
        db,
        user_id=user.id,
        event_type="register",
        ip_address=_get_request_ip(request),
        service_id=_get_request_service_id(request),
    )
    return user


@router.post("/token", response_model=schemas.TokenPair)
@limiter.limit(settings.token_rate_limit)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(db.get_db),
):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    refresh_token, _ = crud.create_refresh_token(db, user.id)
    crud.create_auth_event(
        db,
        user_id=user.id,
        event_type="login",
        ip_address=_get_request_ip(request),
        service_id=_get_request_service_id(request),
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/token/refresh", response_model=schemas.TokenPair)
def refresh_access_token(
    request: Request,
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(db.get_db),
):
    db_token = crud.get_refresh_token(db, payload.refresh_token)
    if not db_token or db_token.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if _is_expired(db_token.expires_at):
        crud.revoke_refresh_token(db, db_token)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    access_token = auth.create_access_token(data={"sub": str(db_token.user.id)})
    crud.revoke_refresh_token(db, db_token)
    refresh_token, _ = crud.create_refresh_token(db, db_token.user_id)
    crud.create_auth_event(
        db,
        user_id=db_token.user_id,
        event_type="token_refresh",
        ip_address=_get_request_ip(request),
        service_id=_get_request_service_id(request),
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/logout")
def logout(payload: schemas.RefreshTokenRequest, db: Session = Depends(db.get_db)):
    db_token = crud.get_refresh_token(db, payload.refresh_token)
    if not db_token or db_token.revoked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already logged out")
    crud.revoke_refresh_token(db, db_token)
    return {"detail": "Logged out"}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(db.get_db)):
    db_token = crud.get_email_verification_token(db, token)
    if not db_token or db_token.used_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if _is_expired(db_token.expires_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
    crud.mark_email_verified(db, db_token)
    return {"detail": "Email verified"}


@router.post("/verify-email/resend")
def resend_verification(payload: schemas.EmailRequest, db: Session = Depends(db.get_db)):
    user = crud.get_user_by_email(db, payload.email)
    if user and not user.email_verified:
        token, _ = crud.create_email_verification_token(db, user.id)
        subject, body = build_verification_email(token)
        send_email(user.email, subject, body)
    return {"detail": "If the account exists, a verification email was sent"}


@router.post("/password/forgot")
def forgot_password(payload: schemas.EmailRequest, db: Session = Depends(db.get_db)):
    user = crud.get_user_by_email(db, payload.email)
    if user:
        token, _ = crud.create_password_reset_token(db, user.id)
        subject, body = build_password_reset_email(token)
        send_email(user.email, subject, body)
    return {"detail": "If the account exists, a reset email was sent"}


@router.post("/password/reset")
def reset_password(payload: schemas.PasswordResetRequest, db: Session = Depends(db.get_db)):
    db_token = crud.get_password_reset_token(db, payload.token)
    if not db_token or db_token.used_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if _is_expired(db_token.expires_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
    try:
        crud.mark_password_reset_used(db, db_token, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"detail": "Password updated"}


@router.get("/users/me", response_model=schemas.UserRead)
def read_users_me(current_user=Depends(auth.get_current_user)):
    return current_user


@router.post("/users/id", response_model=schemas.UserIdResponse)
def get_user_id_by_email(payload: schemas.EmailRequest, db: Session = Depends(db.get_db)):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"id": user.id}


def _is_expired(expires_at: datetime) -> bool:
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < now


def _get_request_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def _get_request_service_id(request: Request):
    return getattr(request.state, "service_id", None)
