"""
Authentication router.
Handles register, login, token refresh, logout, /me, and password reset.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.limiter import limiter
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
        secure=False,  # Set True in production (HTTPS)
        samesite="lax",
        max_age=_REFRESH_MAX_AGE,
        path="/api/auth/refresh",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/auth/refresh")


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
async def refresh_token(
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
    exp_ts = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc) if exp_ts else datetime.now(timezone.utc)
    db.add(TokenBlacklist(jti=jti, expires_at=expires_at))
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # We blacklist the access token via get_current_user's jti; but we also need it here.
    # Instead, just clear the cookie and return success.
    # The access token will expire naturally (15 min).
):
    """Log out: clear refresh cookie."""
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
    """Generate a password reset token (returns token in response for dev; send email in prod)."""
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

    # TODO: Send email. For dev, return the token directly.
    return {
        "status": "If that email exists, a reset link has been sent",
        "dev_token": token_str,  # Remove in production
    }


@router.post("/reset-password")
async def reset_password(
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
