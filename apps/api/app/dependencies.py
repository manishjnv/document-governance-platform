"""FastAPI dependency injection for authentication and authorization."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import extract_token_from_header, verify_token
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenData:
    """
    Dependency to get current authenticated user from JWT token.

    Raises:
        HTTPException 401: If token missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    token_data = verify_token(token, token_type="access")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[TokenData]:
    """
    Dependency for optional authentication (public endpoints).

    Returns:
        TokenData if authenticated, None otherwise
    """
    if not credentials:
        return None

    token = credentials.credentials
    return verify_token(token, token_type="access")


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: TokenData = Depends(require_role("admin"))):
            ...

    Args:
        allowed_roles: Roles that have access

    Returns:
        Dependency function
    """

    async def role_checker(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


async def verify_org_access(
    org_id: int,
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    Verify that user has access to organization.

    In Phase 1, users can only access their own org.
    Future: Support cross-org access for admins.

    Args:
        org_id: Organization ID to access
        current_user: Current authenticated user

    Returns:
        TokenData if authorized

    Raises:
        HTTPException 403: If user is not in organization
    """
    if current_user.org_id != org_id:
        logger.warning(
            f"Cross-org access attempt: user {current_user.user_id} "
            f"(org {current_user.org_id}) tried to access org {org_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    return current_user


class RateLimitMiddleware:
    """
    Simple in-memory rate limiter middleware.

    Future: Use Redis for distributed rate limiting.
    """

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # {ip: [(timestamp, count)]}

    async def __call__(self, request, call_next):
        """Rate limit by IP address."""
        from time import time

        client_ip = request.client.host
        now = time()
        window_start = now - 60

        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        # Clean old entries
        self.request_counts[client_ip] = [
            (ts, count)
            for ts, count in self.request_counts[client_ip]
            if ts > window_start
        ]

        # Check limit
        total_requests = sum(count for _, count in self.request_counts[client_ip])
        if total_requests >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        # Record request
        if not self.request_counts[client_ip] or self.request_counts[client_ip][-1][0] != now:
            self.request_counts[client_ip].append((now, 1))
        else:
            self.request_counts[client_ip][-1] = (now, total_requests + 1)

        response = await call_next(request)
        return response
