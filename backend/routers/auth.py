"""
Authentication router.
Handles register, login, token refresh, logout, /me, and password reset.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.limiter import limiter, setting_limit
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from database.connection import get_db
from database.models import PasswordResetToken, TokenBlacklist, User, UserResponse
from dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
# The cookie must reach /api/auth/refresh AND /api/auth/logout (logout revokes
# it), so it is scoped to the auth prefix. Before ROADMAP 3.6c it was scoped to
# /api/auth/refresh alone; that path is still expired on every set and clear.
_REFRESH_PATH = "/api/auth"
_LEGACY_REFRESH_PATH = "/api/auth/refresh"
_bearer = HTTPBearer(auto_error=False)
_REFRESH_MAX_AGE = settings.refresh_token_expire_days * 24 * 3600


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,  # COOKIE_SECURE=false in dev compose only
        samesite="lax",
        max_age=_REFRESH_MAX_AGE,
        path=_REFRESH_PATH,
    )
    # Retire a cookie issued under the pre-3.6c path so the browser does not
    # hold two (the old one is already blacklisted by rotation).
    response.delete_cookie(key=_REFRESH_COOKIE, path=_LEGACY_REFRESH_PATH)


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path=_REFRESH_PATH)
    response.delete_cookie(key=_REFRESH_COOKIE, path=_LEGACY_REFRESH_PATH)


def _blacklist(db: AsyncSession, payload: dict) -> None:
    """Add a decoded token's jti to the blacklist until its own `exp`."""
    jti = payload.get("jti")
    if not jti:
        return
    exp_ts = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc) if exp_ts else datetime.now(timezone.utc)
    db.add(TokenBlacklist(jti=jti, expires_at=expires_at))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Create a new account. Admin emails get role='admin' automatically."""
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if len(body.password.encode()) > 72:
        raise HTTPException(status_code=400, detail="Password must be 72 characters or fewer (bcrypt limit)")

    is_admin = body.email.lower() in settings.admin_email_list
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        name=body.name,
        role="admin" if is_admin else "user",
        email_verified=True,  # Skip email verification for now
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.post("/login")
@limiter.limit("10/15 minutes")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and return JWT access token + set refresh cookie."""
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Promote to admin if email matches (handles users registered before ADMIN_EMAILS was set)
    if body.email.lower() in settings.admin_email_list and user.role != "admin":
        user.role = "admin"
        await db.flush()

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.post("/refresh")
@limiter.limit(setting_limit("rate_limit_refresh"))
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(default=None, alias=_REFRESH_COOKIE),
):
    """Use the refresh cookie to obtain a new access token (also rotates refresh token)."""
    exc = HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if refresh_token is None:
        raise exc
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise exc

    if payload.get("type") != "refresh":
        raise exc

    user_id: Optional[str] = payload.get("sub")
    jti: Optional[str] = payload.get("jti")
    if not user_id or not jti:
        raise exc

    # Check blacklist
    bl = await db.execute(select(TokenBlacklist).where(TokenBlacklist.jti == jti))
    if bl.scalar_one_or_none() is not None:
        raise exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise exc

    # Blacklist old refresh token
    _blacklist(db, payload)
    await db.flush()

    # Issue new tokens
    new_access = create_access_token(user.id, user.email)
    new_refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh)

    return {
        "access_token": new_access,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.post("/logout")
async def logout(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(default=None, alias=_REFRESH_COOKIE),
):
    """Log out: blacklist the access token and the refresh cookie's token
    (each until its own expiry) and clear the cookie."""
    # get_current_user has already validated the bearer token.
    _blacklist(db, decode_token(credentials.credentials))
    if refresh_token:
        try:
            rp = decode_token(refresh_token)
        except JWTError:
            rp = None
        # Only the caller's own refresh token, only once.
        if rp and rp.get("type") == "refresh" and rp.get("sub") == current_user.id:
            jti = rp.get("jti")
            seen = await db.execute(select(TokenBlacklist).where(TokenBlacklist.jti == jti))
            if jti and seen.scalar_one_or_none() is None:
                _blacklist(db, rp)
    await db.flush()
    _clear_refresh_cookie(response)
    return {"status": "logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a password reset token.

    The body is the same whether or not the email exists, and never
    carries the token unless EXPOSE_RESET_TOKEN is set (dev only). No mail
    is sent yet; the token is in the password_reset_tokens table.
    """
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    # Always return success to avoid email enumeration
    if user is None:
        return {"status": "If that email exists, a reset link has been sent"}

    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token=token_str,
            expires_at=expires_at,
        )
    )
    await db.flush()

    # TODO: send the reset link by email.
    body_out = {"status": "If that email exists, a reset link has been sent"}
    if settings.expose_reset_token:
        body_out["dev_token"] = token_str
    return body_out


@router.post("/reset-password")
@limiter.limit(setting_limit("rate_limit_reset_password"))
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify a password reset token and update the user's password."""
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == body.token,
            PasswordResetToken.used.is_(False),
        )
    )
    token_record = result.scalar_one_or_none()

    if token_record is None:
        raise HTTPException(status_code=400, detail="Invalid or already-used reset token")

    if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user_result = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    token_record.used = True
    await db.flush()

    return {"status": "Password updated successfully"}
