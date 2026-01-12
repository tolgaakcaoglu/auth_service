# Auth Service

FastAPI + PostgreSQL tabanli kimlik dogrulama servisi. JWT, refresh token, e‑posta dogrulama, sifre sifirlama, servis API key’leri ve admin arayuzu icerir.

## Ozellikler

- JWT access + refresh token rotation
- E‑posta dogrulama + sifre sifirlama
- Servis API key’leri (servis bazli allowlist + kullanim takibi)
- Admin UI (dashboard, kullanicilar, servisler, API key’ler, auth event’ler)
- Alembic migration
- Rate limiting ve request logging

## Hizli Baslangic (Docker)

1) Env dosyalarini kopyalayin ve gerekli alanlari duzenleyin:

```bash
cp .env.dev.example .env.dev
cp .env.prod.example .env.prod
```

Gerekli alanlar:
- `SECRET_KEY`
- `ADMIN_USER`, `ADMIN_PASSWORD`

2) Dev veya prod baslatin:

```bash
docker compose --profile dev up --build
# veya
docker compose --profile prod up --build
```

3) Servis + API key olusturun:

```bash
docker compose --profile dev exec auth_dev python scripts/create_service_api_key.py --name my-service --domain my-service.example.com
```

Dev API: `http://localhost:8050`, prod: `http://localhost:9050`.

## Erisim

- Dev API: `http://localhost:8050`
- Prod API: `http://localhost:9050`
- Admin UI: `http://localhost:8050/admin` (dev) / `http://localhost:9050/admin` (prod)
- Postgres (host): `localhost:5440` (dev) / `localhost:5441` (prod)

## Kimlik Dogrulama Mantigi

- Link bazli olmayan tum endpoint’ler `X-API-Key` ister.
- Link bazli endpoint’ler `X-API-Key` istemez: `GET /verify-email`, `POST /password/reset`.
- Admin UI `X-API-Key` istemez, Basic Auth ister.
- Kullanici bilgisi donduren endpoint’ler Bearer token ister (orn. `GET /users/me`).

## Auth Service API

- `POST /register` — yeni kullanici kaydi
- `POST /token` — access + refresh token al
- `POST /token/refresh` — refresh token rotate + yeni access token
- `POST /logout` — refresh token revoke
- `GET /verify-email` — e‑posta dogrulama (link)
- `POST /verify-email/resend` — dogrulama e‑postasi tekrar gonder
- `POST /password/forgot` — sifre sifirlama e‑postasi
- `POST /password/reset` — sifre sifirla (link)
- `GET /users/me` — mevcut kullanici (Bearer token)
- `GET /health` — healthcheck (DB kontrolu dahil)

## Admin UI

- URL: `GET /admin`
- Basic Auth gerekli
- Kimlik bilgileri: `.env.dev` / `.env.prod` icindeki `ADMIN_USER`, `ADMIN_PASSWORD`
- Admin UI `X-API-Key` istemez

## Ortam Degiskenleri

Gerekli:
- `DATABASE_URL`
- `SECRET_KEY`

Yaygin:
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `EMAIL_VERIFY_EXPIRE_MINUTES`
- `PASSWORD_RESET_EXPIRE_MINUTES`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_NAME`, `SMTP_FROM_EMAIL`
- `APP_BASE_URL` (varsayilan `http://localhost:8050`)
- `REGISTER_RATE_LIMIT`, `TOKEN_RATE_LIMIT`
- `LOG_FILE`
- `ADMIN_USER`, `ADMIN_PASSWORD`

Notlar:
- Docker Compose her profil icin `DATABASE_URL` ve `APP_BASE_URL` degerlerini override eder.
- Dev ve prod ayri Postgres servisleri, portlar ve volume’lar kullanir.
- Servis API key’leri hash’lenerek saklanir; key sadece olusturuldugunda bir kez gosterilir.

## Migrations (Alembic)

Docker Compose baslatilirken `alembic upgrade head` calisir.

Yeni migration icin:

```bash
docker compose --profile dev exec auth_dev alembic revision --autogenerate -m "degisiklik"
# veya
docker compose --profile prod exec auth_prod alembic revision --autogenerate -m "degisiklik"
```

## Notlar

- Refresh token’lar DB’de saklanir ve `/token/refresh` cagrisinda rotate edilir.
- E‑posta dogrulamasi tamamlanmadan login olmaz.
- Kullanici ID’leri UUID’dir; access token `sub` claim’i UUID string’idir.

## Proje Yapisi

```
app/
  api/v1/        # REST endpoint’ler
  templates/     # Admin UI template’leri
  static/        # Admin UI asset’leri
  models.py      # SQLAlchemy modelleri
  crud.py        # DB sorgulari
  auth.py        # JWT + sifre helper’lari
  service_auth.py# API key zorunlulugu
alembic/
  versions/      # migrations
scripts/
  create_db.py
  create_service_api_key.py
```
