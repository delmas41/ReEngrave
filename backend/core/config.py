"""
Centralised application settings loaded from environment variables / .env file.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Existing ---
    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./reengrave.db"
    upload_dir: str = "./uploads"
    export_dir: str = "./exports"
    audiveris_home: str = "/opt/Audiveris"

    # --- Auth ---
    secret_key: str = "changeme-please-use-a-long-random-string-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    # Comma-separated list of admin email addresses
    admin_emails: str = "delmas41@gmail.com"

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_price_id: str = ""
    stripe_webhook_secret: str = ""

    # --- CORS / Frontend ---
    # Comma-separated list of allowed origins
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def admin_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
