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
    app_base_url: str = "http://localhost:8000"
    register_rate_limit: str = "5/10 minute"
    token_rate_limit: str = "10/5 minute"
    log_file: str = "app.log"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
