import re

from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


class UserRead(BaseModel):
    id: int
    email: EmailStr
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


class EmailTokenRequest(BaseModel):
    token: str


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
