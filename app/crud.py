from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import func, or_
from . import models, schemas
from .auth import hash_token, generate_token, hash_refresh_token, generate_refresh_token
from .config import settings
from .auth import get_password_hash


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_phone(db: Session, phone: str):
    return db.query(models.User).filter(models.User.phone == phone).first()


def get_user_by_identifier(db: Session, identifier: str):
    return (
        db.query(models.User)
        .filter(or_(models.User.email == identifier, models.User.phone == identifier))
        .first()
    )


def get_user_by_id(db: Session, user_id: UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_service_by_name(db: Session, name: str):
    return db.query(models.Service).filter(models.Service.name == name).first()


def get_service_by_id(db: Session, service_id: UUID):
    return db.query(models.Service).filter(models.Service.id == service_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    if not user.email and not user.phone:
        raise ValueError("Email or phone is required")
    hashed = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        phone=user.phone,
        hashed_password=hashed,
        email_verified=user.email is None,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, identifier: str, password: str):
    user = get_user_by_identifier(db, identifier)
    if not user:
        return None
    from .auth import verify_password

    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_refresh_token(db: Session, user_id: UUID):
    token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    db_token = models.RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return token, db_token


def get_refresh_token(db: Session, token: str):
    token_hash = hash_refresh_token(token)
    return db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()


def revoke_refresh_token(db: Session, db_token: models.RefreshToken):
    db_token.revoked = True
    db.commit()
    db.refresh(db_token)
    return db_token


def create_email_verification_token(db: Session, user_id: UUID):
    token = generate_token(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.email_verify_expire_minutes)
    db_token = models.EmailVerificationToken(
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return token, db_token


def get_email_verification_token(db: Session, token: str):
    token_hash = hash_token(token)
    return (
        db.query(models.EmailVerificationToken)
        .filter(models.EmailVerificationToken.token_hash == token_hash)
        .first()
    )


def mark_email_verified(db: Session, db_token: models.EmailVerificationToken):
    db_token.used_at = datetime.now(timezone.utc)
    db_token.user.email_verified = True
    db.commit()
    db.refresh(db_token)
    return db_token


def create_password_reset_token(db: Session, user_id: UUID):
    token = generate_token(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
    db_token = models.PasswordResetToken(
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return token, db_token


def get_password_reset_token(db: Session, token: str):
    token_hash = hash_token(token)
    return (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == token_hash)
        .first()
    )


def mark_password_reset_used(db: Session, db_token: models.PasswordResetToken, new_password: str):
    db_token.used_at = datetime.now(timezone.utc)
    db_token.user.hashed_password = get_password_hash(new_password)
    db.commit()
    db.refresh(db_token)
    return db_token


def create_auth_event(
    db: Session,
    user_id: UUID,
    event_type: str,
    ip_address: str | None,
    service_id: UUID | None,
):
    db_event = models.AuthEvent(
        user_id=user_id,
        event_type=event_type,
        ip_address=ip_address,
        service_id=service_id,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_service_api_key(db: Session, api_key: str):
    key_hash = hash_token(api_key)
    return (
        db.query(models.ServiceApiKey)
        .filter(models.ServiceApiKey.key_hash == key_hash)
        .first()
    )


def get_service_api_key_by_id(db: Session, api_key_id: UUID):
    return db.query(models.ServiceApiKey).filter(models.ServiceApiKey.id == api_key_id).first()


def touch_service_api_key(db: Session, api_key: models.ServiceApiKey):
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(api_key)
    return api_key


def create_service(db: Session, name: str, domain: str | None = None):
    db_service = models.Service(name=name, domain=domain)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service


def create_service_api_key(db: Session, service_id: UUID):
    api_key = generate_token(48)
    db_key = models.ServiceApiKey(
        service_id=service_id,
        key_hash=hash_token(api_key),
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return api_key, db_key


def list_users_with_last_auth_event(db: Session, limit: int = 100, offset: int = 0):
    last_event_subq = (
        db.query(
            models.AuthEvent.user_id.label("user_id"),
            func.max(models.AuthEvent.created_at).label("last_created_at"),
        )
        .group_by(models.AuthEvent.user_id)
        .subquery()
    )
    query = (
        db.query(models.User, models.AuthEvent, models.Service)
        .outerjoin(last_event_subq, models.User.id == last_event_subq.c.user_id)
        .outerjoin(
            models.AuthEvent,
            (models.AuthEvent.user_id == models.User.id)
            & (models.AuthEvent.created_at == last_event_subq.c.last_created_at),
        )
        .outerjoin(models.Service, models.AuthEvent.service_id == models.Service.id)
        .order_by(models.User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return query.all()


def list_services(db: Session):
    return db.query(models.Service).order_by(models.Service.created_at.desc()).all()


def list_service_api_keys(db: Session, service_id: UUID):
    return (
        db.query(models.ServiceApiKey)
        .filter(models.ServiceApiKey.service_id == service_id)
        .order_by(models.ServiceApiKey.created_at.desc())
        .all()
    )


def set_service_active(db: Session, service: models.Service, is_active: bool):
    service.is_active = is_active
    db.commit()
    db.refresh(service)
    return service


def set_service_api_key_active(db: Session, api_key: models.ServiceApiKey, is_active: bool):
    api_key.is_active = is_active
    db.commit()
    db.refresh(api_key)
    return api_key


def delete_service_api_key(db: Session, api_key: models.ServiceApiKey):
    db.delete(api_key)
    db.commit()


def list_auth_events(db: Session, limit: int = 200):
    return (
        db.query(models.AuthEvent, models.User, models.Service)
        .outerjoin(models.User, models.AuthEvent.user_id == models.User.id)
        .outerjoin(models.Service, models.AuthEvent.service_id == models.Service.id)
        .order_by(models.AuthEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def count_users(db: Session) -> int:
    return db.query(func.count(models.User.id)).scalar() or 0


def count_services(db: Session) -> int:
    return db.query(func.count(models.Service.id)).scalar() or 0


def count_service_api_keys(db: Session) -> int:
    return db.query(func.count(models.ServiceApiKey.id)).scalar() or 0


def count_auth_events(db: Session) -> int:
    return db.query(func.count(models.AuthEvent.id)).scalar() or 0


def count_by_period(db: Session, model, date_field, period: str, start, end):
    rows = (
        db.query(
            func.date_trunc(period, date_field).label("bucket"),
            func.count(model.id).label("count"),
        )
        .filter(date_field >= start, date_field < end)
        .group_by("bucket")
        .order_by("bucket")
        .all()
    )
    return {row.bucket: row.count for row in rows}
