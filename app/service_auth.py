from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import crud
from .db import get_db

API_KEY_HEADER = "X-API-Key"


def require_service_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
    db: Session = Depends(get_db),
):
    if (
        request.url.path.startswith("/admin")
        or request.url.path.startswith("/auth/admin")
        or request.url.path.startswith("/static")
        or request.url.path.startswith("/auth/static")
    ):
        return None
    if request.url.path in {"/verify-email", "/password/reset"}:
        return None
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    api_key = crud.get_service_api_key(db, x_api_key)
    if not api_key or not api_key.is_active or not api_key.service.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    crud.touch_service_api_key(db, api_key)
    request.state.service = api_key.service
    request.state.service_id = api_key.service_id
    return api_key.service
