from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ... import db, crud, schemas, auth
from ...oauth_google import (
    build_google_auth_url,
    create_state,
    decode_state,
    exchange_code_for_token,
    generate_nonce,
    verify_id_token,
)
from ...config import settings
from ...email import send_email, build_verification_email, build_password_reset_email
from ...limiter import limiter

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/register", response_model=schemas.UserRead)
@limiter.limit(settings.register_rate_limit)
def register(request: Request, user_in: schemas.UserCreate, db: Session = Depends(db.get_db)):
    if user_in.email:
        existing = crud.get_user_by_email(db, user_in.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    if user_in.phone:
        existing = crud.get_user_by_phone(db, user_in.phone)
        if existing:
            raise HTTPException(status_code=400, detail="Phone already registered")
    try:
        user = crud.create_user(db, user_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if user.email:
        verification_method = _get_request_verification_method(request)
        if verification_method == "code":
            token = auth.generate_verification_code()
            token, _ = crud.create_email_verification_token(db, user.id, token=token)
        else:
            token, _ = crud.create_email_verification_token(db, user.id)
        subject, body, html_body = build_verification_email(
            token,
            service_name=_get_request_service_name(request),
            verification_method=verification_method,
        )
        send_email(user.email, subject, body, html_body)
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
    if user.email and not user.email_verified:
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


@router.get("/google/login")
def google_login(request: Request):
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="Google login not configured")
    nonce = generate_nonce()
    service_id = getattr(request.state, "service_id", None)
    state = create_state(str(service_id) if service_id else None, nonce)
    return RedirectResponse(build_google_auth_url(state, nonce))


@router.get("/google/callback", response_model=schemas.TokenPair)
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(db.get_db),
):
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="Google login not configured")

    try:
        state_payload = decode_state(state)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Invalid state") from exc

    nonce = state_payload.get("nonce")
    if not nonce:
        raise HTTPException(status_code=400, detail="Invalid state")

    try:
        token_response = exchange_code_for_token(code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to exchange code") from exc

    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="Missing id_token")

    try:
        payload = verify_id_token(id_token, nonce)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid id_token") from exc

    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not available")
    if not payload.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=400, detail="Invalid subject")

    oauth_account = crud.get_oauth_account(db, "google", subject)
    if oauth_account:
        user = oauth_account.user
    else:
        user = crud.get_user_by_email(db, email)
        if not user:
            user = crud.create_user_from_oauth(db, email)
        crud.create_oauth_account(db, user.id, "google", subject, email)
    if user.email_verified is False:
        user.email_verified = True
        db.commit()
        db.refresh(user)

    access_token = auth.create_access_token(data={"sub": str(user.id)})
    refresh_token, _ = crud.create_refresh_token(db, user.id)
    service_id = state_payload.get("service_id")
    if service_id:
        try:
            service_id = UUID(str(service_id))
        except (TypeError, ValueError):
            service_id = None
    crud.create_auth_event(
        db,
        user_id=user.id,
        event_type="login_google",
        ip_address=_get_request_ip(request),
        service_id=service_id,
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


@router.post("/verify-email")
def verify_email_code(payload: schemas.EmailVerificationCodeRequest, db: Session = Depends(db.get_db)):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    db_token = crud.get_email_verification_token_for_user(db, user.id, payload.code)
    if not db_token or db_token.used_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    if _is_expired(db_token.expires_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")
    crud.mark_email_verified(db, db_token)
    return {"detail": "Email verified"}


@router.post("/verify-email/resend")
def resend_verification(
    request: Request,
    payload: schemas.EmailRequest,
    db: Session = Depends(db.get_db),
):
    user = crud.get_user_by_email(db, payload.email)
    if user and not user.email_verified:
        verification_method = _get_request_verification_method(request)
        if verification_method == "code":
            token = auth.generate_verification_code()
            token, _ = crud.create_email_verification_token(db, user.id, token=token)
        else:
            token, _ = crud.create_email_verification_token(db, user.id)
        subject, body, html_body = build_verification_email(
            token,
            service_name=_get_request_service_name(request),
            verification_method=verification_method,
        )
        send_email(user.email, subject, body, html_body)
    return {"detail": "If the account exists, a verification email was sent"}


@router.post("/password/forgot")
def forgot_password(payload: schemas.EmailRequest, db: Session = Depends(db.get_db)):
    user = crud.get_user_by_email(db, payload.email)
    if user:
        token, _ = crud.create_password_reset_token(db, user.id)
        subject, body = build_password_reset_email(token)
        send_email(user.email, subject, body)
    return {"detail": "If the account exists, a reset email was sent"}


@router.get("/password/reset", response_class=HTMLResponse)
def reset_password_form(request: Request, token: str | None = None):
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "token": token},
    )


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


def _get_request_service_name(request: Request) -> str | None:
    service = getattr(request.state, "service", None)
    if not service:
        return None
    return getattr(service, "name", None)


def _get_request_verification_method(request: Request) -> str:
    service = getattr(request.state, "service", None)
    if not service:
        return "link"
    method = getattr(service, "verification_method", None)
    if method in {"link", "code"}:
        return method
    return "link"
