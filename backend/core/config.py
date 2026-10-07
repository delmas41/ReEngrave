"""
Centralised application settings loaded from environment variables / .env file.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings

# The JWT/HMAC secret shipped in this file. Startup refuses it unless
# ALLOW_DEFAULT_SECRET is set (dev compose only) -- see check_startup_secret.
DEFAULT_SECRET_KEY = "changeme-please-use-a-long-random-string-in-production"


class Settings(BaseSettings):
    # --- Existing ---
    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./reengrave.db"
    upload_dir: str = "./uploads"
    export_dir: str = "./exports"

    # --- Auth ---
    secret_key: str = DEFAULT_SECRET_KEY
    # True only in the dev docker-compose.yml: lets the app start with the
    # shipped default secret_key. Never set it in production.
    allow_default_secret: bool = False
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    # Comma-separated list of admin email addresses (ADMIN_EMAILS in .env)
    admin_emails: str = ""
    # Refresh cookie `secure` flag. True (HTTPS only) unless the dev stack
    # sets COOKIE_SECURE=false for plain-http localhost.
    cookie_secure: bool = True
    # Dev only: forgot-password returns the reset token in its body.
    expose_reset_token: bool = False

    # --- Uploads ---
    # Per-file upload cap; every upload route answers 413 above it.
    max_upload_bytes: int = 50 * 1024 * 1024
    # Lifetime of a signed /uploads URL (?t=<exp>.<sig>), seconds.
    upload_url_ttl_s: int = 3600

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_price_id: str = ""
    stripe_webhook_secret: str = ""

    # --- CORS / Frontend ---
    # Comma-separated list of allowed origins
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"

    # --- OMR job budget (ROADMAP 3.3, second half) ---
    # A `staged` job whose estimated cost (tools.omr.staged.budget) exceeds
    # this is refused up front, never silently truncated to the page cap.
    # ~14 h: just over the one measured whole-movement data point (16
    # Litolff pages, ~12.7-13.9 h depending on the direction-text gate —
    # see budget.py's own module docstring for why that figure is an upper
    # bound). Override with OMR_JOB_BUDGET_S.
    omr_job_budget_s: float = 50400.0

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def admin_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def check_startup_secret(s: "Settings") -> None:
    """Refuse to run with the shipped default secret_key.

    Every JWT and every signed /uploads URL is keyed on it, so the default
    lets anyone forge both. Raised from the app lifespan (main.py).
    """
    if s.secret_key == DEFAULT_SECRET_KEY and not s.allow_default_secret:
        raise RuntimeError(
            "SECRET_KEY is the shipped default. Set SECRET_KEY to a long "
            "random string in backend/.env (e.g. `python3 -c \"import "
            "secrets; print(secrets.token_urlsafe(48))\"`), or set "
            "ALLOW_DEFAULT_SECRET=true for a local dev stack only."
        )


settings = Settings()
