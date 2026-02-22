"""Auth, profile, 2FA, and user management (additions only)."""

import secrets
from base64 import b32encode

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.utils.password import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple in-memory "tokens" for demo (keyed by user id). Replace with JWT in production.
_tokens: dict[str, int] = {}  # token -> user_id


def _user_to_response(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "department": u.department or "",
        "two_fa_enabled": u.two_fa_enabled,
    }


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str | None = None


class LoginResponse(BaseModel):
    user: dict
    token: str


@router.post("/login", response_model=dict)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """Login: require existing user with correct password. Returns user + token."""
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Email required")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.password_hash:
        raise HTTPException(status_code=401, detail="Account not set up; contact admin")
    if not body.password:
        raise HTTPException(status_code=401, detail="Password required")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = secrets.token_urlsafe(32)
    _tokens[token] = user.id
    db.add(
        AuditLog(
            action_type="login",
            entity_type="user",
            entity_id=user.id,
            performed_by=user.email,
        )
    )
    db.commit()
    return {
        "user": _user_to_response(user),
        "token": token,
    }


class MeResponse(BaseModel):
    user: dict


def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: current user from Bearer token. Use in profile and other protected routes."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization[7:].strip()
    user_id = _tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me", response_model=dict)
def me(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Current user from Bearer token."""
    return {"user": _user_to_response(current_user)}


@router.post("/logout", response_model=dict)
def logout(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    """Logout: record audit and invalidate token (client should clear stored token)."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        user_id = _tokens.get(token)
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db.add(
                    AuditLog(
                        action_type="logout",
                        entity_type="user",
                        entity_id=user.id,
                        performed_by=user.email,
                    )
                )
                db.commit()
            del _tokens[token]
    return {"ok": True}


class TwoFAEnableResponse(BaseModel):
    secret: str
    qr_uri: str  # otpauth://... for QR


@router.post("/2fa/enable", response_model=dict)
def two_fa_enable(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    """Generate 2FA secret for current user (call /2fa/verify to enable)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization[7:].strip()
    user_id = _tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    raw = secrets.token_bytes(20)
    secret = b32encode(raw).decode("ascii").rstrip("=")
    user.two_fa_secret = secret
    user.two_fa_enabled = False
    db.commit()
    from urllib.parse import quote

    label = quote(f"Compliance:{user.email}")
    qr_uri = f"otpauth://totp/{label}?secret={secret}&issuer=Compliance"
    return {"secret": secret, "qr_uri": qr_uri}


class TwoFAVerifyRequest(BaseModel):
    code: str


@router.post("/2fa/verify", response_model=dict)
def two_fa_verify(
    body: TwoFAVerifyRequest,
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    """Verify TOTP code and enable 2FA for current user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization[7:].strip()
    user_id = _tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.two_fa_secret:
        raise HTTPException(status_code=400, detail="Call /2fa/enable first")
    try:
        import pyotp
        totp = pyotp.TOTP(user.two_fa_secret)
        if totp.verify(body.code.strip(), valid_window=1):
            user.two_fa_enabled = True
            db.commit()
            return {"enabled": True}
    except ImportError:
        raise HTTPException(status_code=501, detail="2FA verify requires: pip install pyotp")
    except Exception:
        pass
    raise HTTPException(status_code=400, detail="Invalid code")


@router.post("/2fa/disable", response_model=dict)
def two_fa_disable(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    """Disable 2FA for current user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization[7:].strip()
    user_id = _tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user.two_fa_secret = None
    user.two_fa_enabled = False
    db.commit()
    return {"enabled": False}
