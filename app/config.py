from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    email_verify_expire_minutes: int = 5
    password_reset_expire_minutes: int = 30
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_name: str = "Auth Service"
    smtp_from_email: str | None = None
    app_base_url: str = "http://localhost:8050"
    register_rate_limit: str = "5/10 minute"
    token_rate_limit: str = "10/5 minute"
    log_file: str = "app.log"
    admin_user: str = "admin"
    admin_password: str = "admin"
    root_path: str = "/auth"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    google_scopes: str = "openid email profile"
    google_authorize_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    google_jwks_url: str = "https://www.googleapis.com/oauth2/v3/certs"
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
