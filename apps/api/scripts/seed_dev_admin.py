"""Dev-only bootstrap: create one organization + one admin user so
POST /api/v1/auth/login has something real to authenticate against.

There is no self-serve registration endpoint in this codebase (org/user
provisioning is assumed to be an admin/ops action, not signup) -- this
script is the smallest way to get a first login working locally. Idempotent:
safe to re-run, skips creation if the org/user already exist.

Usage:
    python scripts/seed_dev_admin.py [--email E] [--password P] [--org NAME]
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.auth import hash_password
from app.db.session import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User


async def seed(email: str, password: str, org_name: str, full_name: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Organization).where(
                Organization.name == org_name, Organization.deleted_at.is_(None)
            )
        )
        org = result.scalar_one_or_none()
        if org is None:
            org = Organization(name=org_name, subscription_tier="enterprise")
            db.add(org)
            await db.flush()
            print(f"Created organization '{org_name}' ({org.org_id})")
        else:
            print(f"Organization '{org_name}' already exists ({org.org_id})")

        result = await db.execute(
            select(User).where(
                User.org_id == org.org_id,
                User.email.ilike(email),
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                org_id=org.org_id,
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role="admin",
                is_active=True,
            )
            db.add(user)
            await db.commit()
            print(f"Created admin user '{email}' in org '{org_name}'")
        else:
            print(f"User '{email}' already exists in org '{org_name}' -- not modified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="password123")
    parser.add_argument("--org", default="Default Organization")
    parser.add_argument("--name", default="Admin User")
    args = parser.parse_args()

    asyncio.run(seed(args.email, args.password, args.org, args.name))
