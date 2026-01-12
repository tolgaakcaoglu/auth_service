# Auth Service

TR: `README_TR.md`

FastAPI + PostgreSQL authentication service with JWT, refresh tokens, email verification, password reset, service API keys, and an admin UI.

## Features

- JWT access + refresh token rotation
- Email verification + password reset
- Service API keys (per-service allowlisting + usage tracking)
- Admin UI (dashboard, users, services, API keys, auth events)
- Alembic migrations
- Rate limiting and request logging

## Quick Start (Docker)

1) Copy env example files and update required values:

```bash
cp .env.dev.example .env.dev
cp .env.prod.example .env.prod
```

Required:
- `SECRET_KEY`
- `ADMIN_USER`, `ADMIN_PASSWORD`

2) Start dev or prod:

```bash
docker compose --profile dev up --build
# or
docker compose --profile prod up --build
```

3) Create a service + API key:

```bash
docker compose --profile dev exec auth_dev python scripts/create_service_api_key.py --name my-service --domain my-service.example.com
```

The dev API runs on `http://localhost:8050`, prod on `http://localhost:9050`.

## Access

- Dev API base: `http://localhost:8050`
- Prod API base: `http://localhost:9050`
- Admin UI: `http://localhost:8050/admin` (dev) / `http://localhost:9050/admin` (prod)
- Postgres on host: `localhost:5440` (dev) / `localhost:5441` (prod)

## Authentication Model

- All non-link API endpoints require `X-API-Key`.
- Link-based endpoints do not require `X-API-Key`: `GET /verify-email`, `POST /password/reset`.
- Admin UI does not require `X-API-Key`, but uses Basic Auth.
- User endpoints that return user data require Bearer tokens (e.g., `GET /users/me`).

## Auth Service API

- `POST /register` — register a new user
- `POST /token` — obtain access + refresh token
- `POST /token/refresh` — rotate refresh token + obtain new access token
- `POST /logout` — revoke refresh token
- `GET /verify-email` — verify email via token (link)
- `POST /verify-email/resend` — resend verification email
- `POST /password/forgot` — send reset email
- `POST /password/reset` — reset password with token (link)
- `GET /users/me` — get current user (requires Bearer token)
- `GET /health` — healthcheck (includes DB check)

## Admin UI

- URL: `GET /admin`
- Basic Auth required
- Credentials from `.env.dev` / `.env.prod`: `ADMIN_USER`, `ADMIN_PASSWORD`
- Admin UI does **not** require `X-API-Key`

## Environment Variables

Required:
- `DATABASE_URL`
- `SECRET_KEY`

Common:
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `EMAIL_VERIFY_EXPIRE_MINUTES`
- `PASSWORD_RESET_EXPIRE_MINUTES`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_NAME`, `SMTP_FROM_EMAIL`
- `APP_BASE_URL` (defaults to `http://localhost:8050`)
- `REGISTER_RATE_LIMIT`, `TOKEN_RATE_LIMIT`
- `LOG_FILE`
- `ADMIN_USER`, `ADMIN_PASSWORD`

Notes:
- Docker Compose overrides `DATABASE_URL` and `APP_BASE_URL` for each profile.
- Dev and prod use different Postgres services, ports, and volumes.
- Service API keys are stored hashed; the plain key is shown only once on creation.

## Migrations (Alembic)

Docker Compose runs `alembic upgrade head` on start.

To create a new migration:

```bash
docker compose --profile dev exec auth_dev alembic revision --autogenerate -m "describe change"
# or
docker compose --profile prod exec auth_prod alembic revision --autogenerate -m "describe change"
```

## Notes

- Refresh tokens are stored in DB and rotated on `/token/refresh`.
- Email verification must be completed before login.
- User IDs are UUIDs; access token `sub` is a UUID string.

## Project Layout

```
app/
  api/v1/        # REST endpoints
  templates/     # Admin UI templates
  static/        # Admin UI assets
  models.py      # SQLAlchemy models
  crud.py        # DB queries
  auth.py        # JWT + password helpers
  service_auth.py# API key enforcement
alembic/
  versions/      # migrations
scripts/
  create_db.py
  create_service_api_key.py
```
