import time
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwk, jwt

from .auth import generate_token
from .config import settings

ISSUER_VALUES = {"https://accounts.google.com", "accounts.google.com"}


def build_google_auth_url(state: str, nonce: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": settings.google_scopes,
        "state": state,
        "nonce": nonce,
    }
    return f"{settings.google_authorize_url}?{urlencode(params)}"


def create_state(service_id: str | None, nonce: str) -> str:
    now = int(time.time())
    payload = {
        "nonce": nonce,
        "service_id": service_id,
        "iat": now,
        "exp": now + 600,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_state(state: str) -> dict[str, Any]:
    return jwt.decode(state, settings.secret_key, algorithms=["HS256"])


def exchange_code_for_token(code: str) -> dict[str, Any]:
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.google_redirect_uri,
    }
    response = httpx.post(settings.google_token_url, data=data, timeout=10.0)
    response.raise_for_status()
    return response.json()


def _fetch_jwks() -> dict[str, Any]:
    response = httpx.get(settings.google_jwks_url, timeout=10.0)
    response.raise_for_status()
    return response.json()


def verify_id_token(id_token: str, nonce: str) -> dict[str, Any]:
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    if not kid:
        raise ValueError("Missing kid in token header")

    jwks = _fetch_jwks()
    key_data = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
    if not key_data:
        raise ValueError("Unable to find matching JWKS key")

    public_key = jwk.construct(key_data)
    payload = jwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=settings.google_client_id,
        options={"verify_iss": False},
    )
    issuer = payload.get("iss")
    if issuer not in ISSUER_VALUES:
        raise ValueError("Invalid issuer")
    if payload.get("nonce") != nonce:
        raise ValueError("Invalid nonce")
    return payload


def generate_nonce() -> str:
    return generate_token(16)
