# FastAPI PostgreSQL Auth Service

Minimal authentication service using FastAPI, PostgreSQL and JWT.

Quick start

1. Create a `.env` (see `.env.example`) and set `DATABASE_URL` and `SECRET_KEY`.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run database migrations (creates tables):

```bash
python scripts/create_db.py
alembic upgrade head
```

4. Run the app (example using uvicorn):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints

- `POST /register` — register a new user
- `POST /token` — obtain access + refresh token (OAuth2 password)
- `POST /token/refresh` — rotate refresh token + obtain new access token
- `POST /logout` — revoke refresh token
- `GET /verify-email` — verify email via token (sent by email)
- `POST /verify-email/resend` — resend verification email
- `POST /password/forgot` — send reset email
- `POST /password/reset` — reset password with token
- `GET /users/me` — get current user (requires Bearer token)
- `GET /health` — healthcheck (includes DB check)

Migrations (Alembic)

- `alembic.ini` is scaffolded, but the connection URL is read from `DATABASE_URL` at runtime in `alembic/env.py` for safety and flexibility.
- The initial migration lives in `alembic/versions/2f0b6a2f2f35_initial.py`. New schema changes should be captured with:

```bash
alembic revision --autogenerate -m "describe change"
```

- Apply latest migrations:

```bash
alembic upgrade head
```

- Roll back one migration:

```bash
alembic downgrade -1
```

- See history/current revision:

```bash
alembic history
alembic current
```

Notes (TR)

- Autogenerate icin modellerin import edilip metadata'nin yuklenmesi gerekir; bu zaten `alembic/env.py` icinde yapilir.
- `DATABASE_URL` ortam degiskenini ayarlamadan migration calistirmayin.
- Veritabani yoksa once olusturmak icin `python scripts/create_db.py` kullanin. Varsayilan admin DB `postgres`'tir; gerekirse `POSTGRES_ADMIN_DB` ile degistirebilirsiniz.
- Refresh token'lar DB'de saklanir ve her `/token/refresh` cagrisinda rotate edilir (coklu cihaz desteklenir).
- E-posta dogrulama Gmail SMTP ile gonderilir. Gmail'de 2FA acip "App Password" uretin ve `.env`'e ekleyin.
- DOGRULAMA suresi 5 dakikadir (`EMAIL_VERIFY_EXPIRE_MINUTES=5`). E-posta dogrulanmadan login izinli degildir.
- `/register` ve `/token` icin rate limit uygulanir. Degerler `.env` ile degistirilebilir: `REGISTER_RATE_LIMIT`, `TOKEN_RATE_LIMIT`.
- Basit request logging aciktir ve `X-Request-ID` header'i eklenir (extra bagimlilik gerekmez).
- Kullanici ID'leri UUID'dir; access token `sub` claim'i UUID string olarak gonderilir.
