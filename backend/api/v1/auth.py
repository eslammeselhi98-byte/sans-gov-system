from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

from core.database import get_db
from core.security import (
    verify_password, hash_password, create_access_token,
    create_refresh_token, decode_token, generate_totp_secret,
    generate_totp_qr, verify_totp, generate_secure_token, hash_token
)
from core.deps import get_current_user, CurrentUser, DB
from models.user import User, RefreshToken, AuditLog
from core.config import settings

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class Enable2FAResponse(BaseModel):
    secret: str
    qr_code: str
    uri: str


class Verify2FARequest(BaseModel):
    code: str


# ─── Routes ───────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, body: LoginRequest, db: DB):
    """Authenticate and return JWT tokens."""
    result = await db.execute(
        select(User).where(User.email == body.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # 2FA check
    if user.totp_enabled:
        if not body.totp_code:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="2FA code required",
            )
        if not verify_totp(user.totp_secret, body.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

    # Generate tokens
    access_token = create_access_token({"sub": str(user.id)})
    raw_refresh = generate_secure_token()
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Store refresh token hash
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Audit log
    log = AuditLog(
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(log)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "full_name_ar": user.full_name_ar,
            "role_id": str(user.role_id) if user.role_id else None,
            "company_id": str(user.company_id),
            "avatar_url": user.avatar_url,
            "must_change_password": user.must_change_password,
            "totp_enabled": user.totp_enabled,
        },
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(body: RefreshRequest, db: DB):
    """Refresh access token using refresh token."""
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old token
    rt.revoked = True

    # Get user
    result = await db.execute(select(User).where(User.id == rt.user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # New tokens
    access_token = create_access_token({"sub": str(user.id)})
    raw_refresh = generate_secure_token()
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_rt)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "full_name_ar": user.full_name_ar,
            "company_id": str(user.company_id),
        },
    )


@router.post("/logout")
async def logout(body: RefreshRequest, current_user: CurrentUser, db: DB):
    """Revoke refresh token."""
    token_hash = hash_token(body.refresh_token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.user_id == current_user.id)
        .values(revoked=True)
    )
    await db.commit()
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_profile(current_user: CurrentUser, db: DB):
    """Get current user profile."""
    await db.refresh(current_user, ["role"])
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "full_name_ar": current_user.full_name_ar,
        "phone": current_user.phone,
        "company_id": str(current_user.company_id),
        "role": {
            "id": str(current_user.role.id),
            "name": current_user.role.name,
            "name_ar": current_user.role.name_ar,
            "permissions": current_user.role.permissions,
        } if current_user.role else None,
        "avatar_url": current_user.avatar_url,
        "totp_enabled": current_user.totp_enabled,
        "telegram_id": current_user.telegram_id,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, current_user: CurrentUser, db: DB):
    """Change current user's password."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    current_user.password_hash = hash_password(body.new_password)
    current_user.must_change_password = False
    current_user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(current_user: CurrentUser, db: DB):
    """Generate 2FA secret and QR code."""
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    secret = generate_totp_secret()
    qr = generate_totp_qr(secret, current_user.email)

    import pyotp
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name=settings.APP_NAME
    )

    # Save secret (not yet enabled — user must verify first)
    current_user.totp_secret = secret
    await db.commit()

    return Enable2FAResponse(secret=secret, qr_code=qr, uri=uri)


@router.post("/2fa/verify")
async def verify_2fa(body: Verify2FARequest, current_user: CurrentUser, db: DB):
    """Verify TOTP code and activate 2FA."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Call /2fa/enable first")
    if not verify_totp(current_user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    current_user.totp_enabled = True
    await db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(body: Verify2FARequest, current_user: CurrentUser, db: DB):
    """Disable 2FA (requires valid code)."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    if not verify_totp(current_user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()
    return {"message": "2FA disabled"}
