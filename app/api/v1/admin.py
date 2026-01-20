from uuid import UUID
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ... import crud, db, models
from ...admin_auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def admin_root():
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week(dt: datetime) -> datetime:
    start = _start_of_day(dt)
    return start - timedelta(days=start.weekday())


def _start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _start_of_year(dt: datetime) -> datetime:
    return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(dt: datetime, months: int) -> datetime:
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=year, month=month)


def _bucket_range(now: datetime, period: str, buckets: int):
    if period == "day":
        start = _start_of_day(now) - timedelta(days=buckets - 1)
        step = timedelta(days=1)
        return [start + step * i for i in range(buckets)]
    if period == "week":
        start = _start_of_week(now) - timedelta(weeks=buckets - 1)
        step = timedelta(weeks=1)
        return [start + step * i for i in range(buckets)]
    if period == "month":
        start = _start_of_month(now)
        buckets_list = [_add_months(start, - (buckets - 1) + i) for i in range(buckets)]
        return buckets_list
    if period == "year":
        start = _start_of_year(now)
        return [start.replace(year=start.year - (buckets - 1) + i) for i in range(buckets)]
    raise ValueError("Unsupported period")


def _format_bucket(period: str, dt: datetime) -> str:
    if period == "day":
        return dt.strftime("%Y-%m-%d")
    if period == "week":
        return dt.strftime("W%V %Y")
    if period == "month":
        return dt.strftime("%Y-%m")
    if period == "year":
        return dt.strftime("%Y")
    return str(dt)


@router.get("/dashboard")
def admin_dashboard(request: Request, db_session: Session = Depends(db.get_db)):
    now = datetime.now(timezone.utc)
    totals = {
        "users": crud.count_users(db_session),
        "services": crud.count_services(db_session),
        "service_keys": crud.count_service_api_keys(db_session),
        "auth_events": crud.count_auth_events(db_session),
    }
    latest_events = crud.list_auth_events(db_session, limit=10)

    periods = {
        "day": 7,
        "week": 8,
        "month": 12,
        "year": 5,
    }

    charts = {}
    for period, bucket_count in periods.items():
        bucket_starts = _bucket_range(now, period, bucket_count)
        start = bucket_starts[0]
        end = None
        if period == "day":
            end = _start_of_day(now) + timedelta(days=1)
        elif period == "week":
            end = _start_of_week(now) + timedelta(weeks=1)
        elif period == "month":
            end = _add_months(_start_of_month(now), 1)
        elif period == "year":
            end = _start_of_year(now).replace(year=_start_of_year(now).year + 1)

        user_activity = crud.count_by_period(
            db_session,
            model=models.AuthEvent,
            date_field=models.AuthEvent.created_at,
            period=period,
            start=start,
            end=end,
        )
        items = [
            {"label": _format_bucket(period, bucket), "value": user_activity.get(bucket, 0)}
            for bucket in bucket_starts
        ]
        max_value = max((item["value"] for item in items), default=0) or 1
        charts[f"user_activity_{period}"] = {"items": items, "max": max_value}

    service_months = _bucket_range(now, "month", 12)
    service_start = service_months[0]
    service_end = _add_months(_start_of_month(now), 1)
    service_created = crud.count_by_period(
        db_session,
        model=models.Service,
        date_field=models.Service.created_at,
        period="month",
        start=service_start,
        end=service_end,
    )
    service_items = [
        {"label": _format_bucket("month", bucket), "value": service_created.get(bucket, 0)}
        for bucket in service_months
    ]
    service_max = max((item["value"] for item in service_items), default=0) or 1
    charts["services_monthly"] = {"items": service_items, "max": service_max}

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "totals": totals, "charts": charts, "latest_events": latest_events},
    )


@router.get("/users")
def admin_users(request: Request, db_session: Session = Depends(db.get_db)):
    rows = crud.list_users_with_last_auth_event(db_session)
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "rows": rows},
    )


@router.get("/services")
def admin_services(request: Request, db_session: Session = Depends(db.get_db)):
    services = crud.list_services(db_session)
    service_keys = {service.id: crud.list_service_api_keys(db_session, service.id) for service in services}
    return templates.TemplateResponse(
        "services.html",
        {"request": request, "services": services, "service_keys": service_keys},
    )


@router.post("/services/create")
def admin_create_service(
    request: Request,
    name: str = Form(...),
    domain: str | None = Form(None),
    verification_method: str = Form("link"),
    db_session: Session = Depends(db.get_db),
):
    existing = crud.get_service_by_name(db_session, name)
    if existing:
        raise HTTPException(status_code=400, detail="Service name already exists")
    verification_method = _normalize_verification_method(verification_method)
    service = crud.create_service(
        db_session,
        name=name,
        domain=domain,
        verification_method=verification_method,
    )
    api_key, db_key = crud.create_service_api_key(db_session, service.id)
    return templates.TemplateResponse(
        "service_key_created.html",
        {"request": request, "service": service, "api_key": api_key, "api_key_id": db_key.id},
    )


@router.post("/services/{service_id}/keys")
def admin_create_service_key(
    service_id: UUID,
    request: Request,
    db_session: Session = Depends(db.get_db),
):
    service = crud.get_service_by_id(db_session, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    api_key, db_key = crud.create_service_api_key(db_session, service.id)
    return templates.TemplateResponse(
        "service_key_created.html",
        {"request": request, "service": service, "api_key": api_key, "api_key_id": db_key.id},
    )


@router.post("/services/{service_id}/toggle")
def admin_toggle_service(
    service_id: UUID,
    is_active: bool = Form(...),
    db_session: Session = Depends(db.get_db),
):
    service = crud.get_service_by_id(db_session, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    crud.set_service_active(db_session, service, is_active=is_active)
    return RedirectResponse(url="/admin/services", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/keys/{api_key_id}/toggle")
def admin_toggle_key(
    api_key_id: UUID,
    is_active: bool = Form(...),
    db_session: Session = Depends(db.get_db),
):
    api_key = crud.get_service_api_key_by_id(db_session, api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    crud.set_service_api_key_active(db_session, api_key, is_active=is_active)
    return RedirectResponse(url="/admin/services", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/keys/{api_key_id}/delete")
def admin_delete_key(
    api_key_id: UUID,
    db_session: Session = Depends(db.get_db),
):
    api_key = crud.get_service_api_key_by_id(db_session, api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    crud.delete_service_api_key(db_session, api_key)
    return RedirectResponse(url="/admin/services", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/events")
def admin_events(request: Request, db_session: Session = Depends(db.get_db)):
    events = crud.list_auth_events(db_session)
    return templates.TemplateResponse(
        "events.html",
        {"request": request, "events": events},
    )


def _normalize_verification_method(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"link", "code"}:
        raise HTTPException(status_code=400, detail="Invalid verification method")
    return normalized
