from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from . import models, schemas
from .auth import hash_token, generate_token, hash_refresh_token, generate_refresh_token
from .config import settings
from .auth import get_password_hash


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    from .auth import verify_password

    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_refresh_token(db: Session, user_id: int):
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


def create_email_verification_token(db: Session, user_id: int):
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


def create_password_reset_token(db: Session, user_id: int):
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
