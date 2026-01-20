import re

from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, model_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Phone must not be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_identifier(self) -> "UserCreate":
        if not self.email and not self.phone:
            raise ValueError("Email or phone is required")
        return self


class UserRead(BaseModel):
    id: UUID
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: bool
    email_verified: bool
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    email: Optional[str] = None


class EmailRequest(BaseModel):
    email: EmailStr


class UserIdResponse(BaseModel):
    id: UUID


class EmailTokenRequest(BaseModel):
    token: str


class EmailVerificationCodeRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.fullmatch(r"\d{6}", cleaned):
            raise ValueError("Code must be 6 digits")
        return cleaned


class PasswordResetRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


def _validate_password(value: str) -> str:
    pattern = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{6,}$"
    if not re.match(pattern, value):
        raise ValueError(
            "Password must be at least 6 characters and include at least "
            "one letter, one number, and one symbol."
        )
    return value
