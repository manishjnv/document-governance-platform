"""User lifecycle operations: suspend, reactivate, bulk import.

T-2088: User suspension/deactivation
T-2090: Bulk user import via CSV
"""

from __future__ import annotations

import csv
import secrets
import uuid
from io import StringIO
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.models.enums import UserRole
from app.models.user import User


class LastActiveAdminError(Exception):
    """Raised when attempting to suspend the org's last active admin."""


async def suspend_user(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Suspend a user (set is_active = False).

    Raises:
        ValueError: user doesn't exist or doesn't belong to org_id
        LastActiveAdminError: user is the last active admin in the org
    """
    result = await db.execute(
        select(User).where(
            and_(
                User.user_id == user_id,
                User.org_id == org_id,
                User.deleted_at.is_(None),
            )
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError(f"User {user_id} not found in organization {org_id}")

    # Guard: don't suspend if it's the last active admin
    if user.role == UserRole.ADMIN.value and user.is_active:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                and_(
                    User.org_id == org_id,
                    User.role == UserRole.ADMIN.value,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        )
        if count_result.scalar_one() <= 1:
            raise LastActiveAdminError(
                "Cannot suspend the organization's last remaining active admin"
            )

    user.is_active = False
    await db.commit()
    await db.refresh(user)


async def reactivate_user(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Reactivate a user (set is_active = True).

    Raises:
        ValueError: user doesn't exist or doesn't belong to org_id
    """
    result = await db.execute(
        select(User).where(
            and_(
                User.user_id == user_id,
                User.org_id == org_id,
                User.deleted_at.is_(None),
            )
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError(f"User {user_id} not found in organization {org_id}")

    user.is_active = True
    await db.commit()
    await db.refresh(user)


async def bulk_import_users(db: AsyncSession, org_id: uuid.UUID, csv_content: str) -> dict:
    """Bulk import users from CSV.

    CSV format: email,full_name,role (header required)

    Strategy:
    - Skip rows where email already exists in org (case-insensitive match)
    - Create new User with random temporary password (generate with secrets.token_urlsafe(16))
    - Validate role is admin/reviewer/viewer; skip invalid rows
    - Return summary: {"created": int, "skipped": [...], "errors": [...]}

    Note: No email delivery configured; caller must communicate temp password separately.

    Returns:
        {
            "created": int,
            "skipped": [{"row": int, "reason": str}, ...],
            "errors": [{"row": int, "reason": str}, ...],
        }
    """
    created = 0
    skipped = []
    errors = []

    reader = csv.DictReader(StringIO(csv_content))

    # Verify header
    if reader.fieldnames is None or list(reader.fieldnames) != ["email", "full_name", "role"]:
        return {
            "created": 0,
            "skipped": [],
            "errors": [{"row": 1, "reason": "Invalid header; expected: email,full_name,role"}],
        }

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        email = (row.get("email") or "").strip()
        full_name = (row.get("full_name") or "").strip()
        role = (row.get("role") or "").strip()

        # Validate email
        if not email:
            errors.append({"row": row_num, "reason": "Missing email"})
            continue

        # Validate role
        if role not in {r.value for r in UserRole}:
            errors.append(
                {"row": row_num, "reason": f"Invalid role: {role!r}; must be admin/reviewer/viewer"}
            )
            continue

        # Check if user already exists (case-insensitive email)
        existing_result = await db.execute(
            select(User).where(
                and_(
                    User.org_id == org_id,
                    func.lower(User.email) == email.lower(),
                    User.deleted_at.is_(None),
                )
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            skipped.append(
                {"row": row_num, "reason": f"User with email {email!r} already exists"}
            )
            continue

        # Create user
        try:
            temp_password = secrets.token_urlsafe(16)
            user = User(
                org_id=org_id,
                email=email,
                password_hash=hash_password(temp_password),
                full_name=full_name if full_name else None,
                role=role,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            created += 1
        except Exception as e:
            errors.append({"row": row_num, "reason": f"Database error: {str(e)}"})
            continue

    await db.commit()

    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }
