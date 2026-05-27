"""Authentication helpers: JWT token creation / verification and password hashing."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Optional heavy deps — fail gracefully if not yet installed ────────────────
try:
    from jose import JWTError, jwt
    _JOSE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _JOSE_AVAILABLE = False

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _PASSLIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PASSLIB_AVAILABLE = False

# OAuth2 bearer scheme used by protected route dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

# Optional API key header (X-API-Key) for service-to-service calls
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


# ── Password helpers ──────────────────────────────────────────────────────────

def create_password_hash(password: str) -> str:
    """Return bcrypt hash of *password*."""
    if not _PASSLIB_AVAILABLE:
        raise RuntimeError("passlib[bcrypt] is required — run: pip install passlib[bcrypt]")
    return _pwd_context.hash(password)


# Alias kept for code that imports the original name
get_password_hash = create_password_hash


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True when *plain_password* matches *hashed_password*."""
    if not _PASSLIB_AVAILABLE:
        raise RuntimeError("passlib[bcrypt] is required — run: pip install passlib[bcrypt]")
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode *data* as a signed JWT access token.

    Args:
        data:          Payload to encode (e.g. ``{"sub": "user_id"}``).
        expires_delta: How long until the token expires.  Defaults to
                       ``ACCESS_TOKEN_EXPIRE_MINUTES`` from settings.

    Returns:
        Signed JWT string.
    """
    if not _JOSE_AVAILABLE:
        raise RuntimeError(
            "python-jose[cryptography] is required — run: pip install 'python-jose[cryptography]'"
        )

    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    to_encode.setdefault("iat", datetime.now(tz=timezone.utc))
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug("Access token created for sub=%s exp=%s", data.get("sub"), expire.isoformat())
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Raises:
        HTTPException 401: If the token is invalid or expired.
    """
    if not _JOSE_AVAILABLE:
        raise RuntimeError("python-jose[cryptography] is required")

    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise _CREDENTIALS_EXCEPTION from exc


# ── API key validation ────────────────────────────────────────────────────────

def validate_api_key(api_key: str) -> bool:
    """Validate an API key against the configured secret.

    Uses timing-safe comparison to prevent timing attacks.
    Returns True when the key is valid, False otherwise.

    For the hackathon demo this checks against ``SECRET_KEY`` prefixed with
    ``"api-"`` — replace with a proper key store in production.
    """
    if not api_key:
        return False
    settings = get_settings()
    expected = f"api-{settings.SECRET_KEY}"
    return hmac.compare_digest(
        hashlib.sha256(api_key.encode()).hexdigest(),
        hashlib.sha256(expected.encode()).hexdigest(),
    )


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[dict[str, Any]]:
    """Optional JWT dependency.

    Returns the decoded payload when a valid Bearer token is present, or
    *None* for unauthenticated requests (useful during development/hackathon).
    """
    if not token:
        return None
    return decode_access_token(token)


def require_auth(
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """Strict JWT dependency — raises HTTP 401 when no valid token is provided."""
    if not token:
        raise _CREDENTIALS_EXCEPTION
    return decode_access_token(token)


def require_api_key(
    api_key: Optional[str] = Depends(api_key_header),
) -> str:
    """Strict API-key dependency — raises HTTP 403 when the key is invalid."""
    if not api_key or not validate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return api_key
