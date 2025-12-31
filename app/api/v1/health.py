from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ... import db

router = APIRouter()


@router.get("/health")
def health_check(db_session: Session = Depends(db.get_db)):
    try:
        db_session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="db_unavailable")
    return {"status": "ok", "db": "ok"}
