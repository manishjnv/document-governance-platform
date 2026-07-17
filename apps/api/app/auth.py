"""JWT token handling and authentication utilities."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from app.config import settings
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    org_id: uuid.UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """
    Create a JWT access token.

    Args:
        user_id: User ID
        email: User email
        org_id: Organization ID
        role: User role
        expires_delta: Custom expiration delta (uses config default if None)

    Returns:
        Tuple of (token, expiration_datetime)
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.jwt_expiration_hours)

    now = datetime.utcnow()
    expires = now + expires_delta

    # user_id/org_id are UUID objects -- jose's jwt.encode json-dumps the
    # payload and json can't serialize UUID directly, so stringify here.
    # verify_token()'s TokenData(**payload) parses the strings back into
    # real uuid.UUID objects on the way out (Pydantic coerces a valid UUID
    # string to uuid.UUID automatically).
    payload = {
        "user_id": str(user_id),
        "email": email,
        "org_id": str(org_id),
        "role": role,
        "exp": expires,
        "iat": now,
        "type": "access",
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt, expires


def create_refresh_token(
    user_id: uuid.UUID,
    email: str,
    org_id: uuid.UUID,
) -> tuple[str, datetime]:
    """
    Create a JWT refresh token (longer expiration).

    Args:
        user_id: User ID
        email: User email
        org_id: Organization ID

    Returns:
        Tuple of (token, expiration_datetime)
    """
    expires_delta = timedelta(days=settings.jwt_refresh_expiration_days)
    now = datetime.utcnow()
    expires = now + expires_delta

    payload = {
        "user_id": str(user_id),
        "email": email,
        "org_id": str(org_id),
        "exp": expires,
        "iat": now,
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt, expires


def verify_token(
    token: str, token_type: str = "access", model: type = TokenData
) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type (access | refresh | reset)
        model: Pydantic model to parse the payload into -- TokenData for
            access/refresh tokens (carries org_id/role), ResetTokenData for
            password-reset tokens (deliberately doesn't).

    Returns:
        Parsed token model if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        # Validate token type
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None

        # Convert timestamps
        payload["exp"] = datetime.fromtimestamp(payload["exp"])
        payload["iat"] = datetime.fromtimestamp(payload["iat"])

        return model(**payload)

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except ValidationError as e:
        logger.warning(f"Token validation error: {e}")
        return None


def extract_token_from_header(authorization: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Format: "Bearer <token>"

    Args:
        authorization: Authorization header value

    Returns:
        Token string if valid format, None otherwise
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
