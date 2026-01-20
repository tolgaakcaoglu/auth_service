# Auth Service Endpoint ve Response Dokumani

Bu dosya, projedeki endpoint'leri ve temel request/response formatlarini ozetler.

## Base URL

- Prod (reverse proxy ile): `http://95.70.226.110/auth`
- Proxy yoksa: `http://95.70.226.110` (servisin dinledigi porta gore)

## Kimlik Dogrulama

- `X-API-Key`: Link bazli olmayan tum API endpoint'leri icin zorunlu.
- Bearer token: Kullanici bilgisi donduren endpoint'ler icin zorunlu (orn. `/users/me`).
  - Header: `Authorization: Bearer <access_token>`
- E-posta dogrulama modu servis bazlidir: `services.verification_method` = `link` veya `code`.

## Genel Hata Format

```json
{
  "detail": "Hata mesaji"
}
```

## Ortak Response Nesneleri

### UserRead
```json
{
  "id": "f1b0c2a6-4d8e-4c4e-bc93-0d9f0e8d1b7c",
  "email": "user@example.com",
  "phone": "+905551112233",
  "is_active": true,
  "email_verified": false,
  "created_at": "2024-01-01T10:00:00Z"
}
```

### TokenPair
```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "token_type": "bearer"
}
```

### Detay Mesaji
```json
{
  "detail": "Mesaj"
}
```

## Auth Service API (JSON)

### POST /register
- ISTEK TIPI: `POST`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/register`
- Body (JSON):
```json
{
  "email": "user@example.com",
  "phone": "+905551112233",
  "password": "Abcdef!1"
}
```
Not: `email` veya `phone` zorunludur. Sifre en az 6 karakter, 1 harf, 1 sayi, 1 sembol icermelidir.
- YANIT: `UserRead`
- YANIT KODU: `200`
- Not: Dogrulama e-postasi servis ayarina gore `link` veya `code` modunda gonderilir. Baslik servis adina gore ozellesir.
- HATA KODLARI:
  - `400` `Email already registered` / `Phone already registered` / sifre kurali hatasi
  - `401` `API key required` / `Invalid API key`

### POST /token
- ISTEK TIPI: `POST`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/token`
- Body: `application/x-www-form-urlencoded`
  - `username`: email veya phone
  - `password`
- YANIT: `TokenPair`
- YANIT KODU: `200`
- HATA KODLARI:
  - `401` `Incorrect username or password` / `API key required` / `Invalid API key`
  - `403` `Email not verified`

### GET /google/login
- ISTEK TIPI: `GET`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/google/login`
- Aciklama: Google login sayfasina yonlendirir. OAuth2 Authorization Code akisi kullanilir.
- YANIT: HTTP redirect (Google authorize URL)
- YANIT KODU: `307` / `302`
- HATA KODLARI:
  - `500` `Google login not configured`
  - `401` `API key required` / `Invalid API key`

### GET /google/callback
- ISTEK TIPI: `GET`
- GEREKSINIMLER: Yok (Google redirect eder)
- ENDPOINT: `/google/callback?code=...&state=...`
- Aciklama: Google'dan gelen `code` ile token degisimi yapar, `id_token` dogrular ve kullanici icin TokenPair dondurur.
- YANIT: `TokenPair`
- YANIT KODU: `200`
- HATA KODLARI:
  - `400` `Missing code or state` / `Invalid state` / `Failed to exchange code` / `Invalid id_token`
  - `403` `Email not verified`

### POST /token/refresh
- ISTEK TIPI: `POST`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/token/refresh`
- Body (JSON):
```json
{
  "refresh_token": "jwt-refresh-token"
}
```
- YANIT: `TokenPair`
- YANIT KODU: `200`
- HATA KODLARI:
  - `401` `Invalid refresh token` / `Refresh token expired` / `API key required` / `Invalid API key`

### POST /logout
- ISTEK TIPI: `POST`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/logout`
- Body (JSON):
```json
{
  "refresh_token": "jwt-refresh-token"
}
```
- YANIT:
```json
{
  "detail": "Logged out"
}
```
- YANIT KODU: `200`
- HATA KODLARI:
  - `401` `API key required` / `Invalid API key`
  - `409` `Already logged out`

### GET /verify-email
- ISTEK TIPI: `GET`
- GEREKSINIMLER: Yok (link bazli)
- ENDPOINT: `/verify-email?token=...`
- YANIT:
```json
{
  "detail": "Email verified"
}
```
- YANIT KODU: `200`
- HATA KODLARI:
  - `400` `Invalid token` / `Token expired`

### POST /verify-email
- ISTEK TIPI: `POST`
- GEREKSINIMLER: Yok (kod bazli)
- ENDPOINT: `/verify-email`
- Body (JSON):
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```
- YANIT:
```json
{
  "detail": "Email verified"
}
```
- YANIT KODU: `200`
- HATA KODLARI:
  - `400` `Invalid code` / `Code expired`

### POST /verify-email/resend
- ISTEK TIPI: `POST`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/verify-email/resend`
- Body (JSON):
```json
{
  "email": "user@example.com"
}
```
- YANIT:
```json
{
  "detail": "If the account exists, a verification email was sent"
}
```
- YANIT KODU: `200`
- Not: Servisin dogrulama moduna gore link veya 6 haneli kod gonderilir.
- HATA KODLARI:
  - `401` `API key required` / `Invalid API key`

### POST /password/forgot
- ISTEK TIPI: `POST`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/password/forgot`
- Body (JSON):
```json
{
  "email": "user@example.com"
}
```
- YANIT:
```json
{
  "detail": "If the account exists, a reset email was sent"
}
```
- YANIT KODU: `200`
- HATA KODLARI:
  - `401` `API key required` / `Invalid API key`

### GET /password/reset
- ISTEK TIPI: `GET`
- GEREKSINIMLER: Yok (link bazli)
- ENDPOINT: `/password/reset?token=...`
- YANIT: HTML form (template: `reset_password.html`)
- YANIT KODU: `200`

### POST /password/reset
- ISTEK TIPI: `POST`
- GEREKSINIMLER: Yok (link bazli)
- ENDPOINT: `/password/reset`
- Body (JSON):
```json
{
  "token": "reset-token",
  "password": "Abcdef!1"
}
```
- YANIT:
```json
{
  "detail": "Password updated"
}
```
- YANIT KODU: `200`
- HATA KODLARI:
  - `400` `Invalid token` / `Token expired` / sifre kurali hatasi

### GET /users/me
- ISTEK TIPI: `GET`
- GEREKSINIMLER: `X-API-Key` + `Authorization: Bearer <token>`
- ENDPOINT: `/users/me`
- YANIT: `UserRead`
- YANIT KODU: `200`
- HATA KODLARI:
  - `401` `API key required` / `Invalid API key`
  - `401` `Not authenticated` (Bearer token yok/hatali)

### POST /users/id
- ISTEK TIPI: `POST`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/users/id`
- Body (JSON):
```json
{
  "email": "user@example.com"
}
```
- YANIT:
```json
{
  "id": "f1b0c2a6-4d8e-4c4e-bc93-0d9f0e8d1b7c"
}
```
- YANIT KODU: `200`
- HATA KODLARI:
  - `401` `API key required` / `Invalid API key`
  - `404` `User not found`

### GET /health
- ISTEK TIPI: `GET`
- GEREKSINIMLER: `X-API-Key`
- ENDPOINT: `/health`
- YANIT:
```json
{
  "status": "ok",
  "db": "ok"
}
```
- YANIT KODU: `200`
- HATA KODLARI:
  - `401` `API key required` / `Invalid API key`
  - `503` `db_unavailable`
