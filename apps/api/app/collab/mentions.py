"""Extract @-mentions from comment text (T-2064)."""

from __future__ import annotations

import re
import uuid
from typing import Optional


def extract_mentions(
    content: str, org_member_emails: dict[str, uuid.UUID]
) -> list[uuid.UUID]:
    """Extract @-mentions from comment content.

    Strategy: match patterns like @user.name@org.com (full email mentions) or @handle
    where handle is a key in org_member_emails lookup dict.

    Args:
        content: Comment text containing @-mentions.
        org_member_emails: Mapping of email/handle → user_id (e.g., {"alice@example.com": <uuid>})

    Returns:
        List of matched user UUIDs; empty if no matches or no org_member_emails provided.
    """
    if not org_member_emails or not content:
        return []

    mentioned_ids = []
    seen = set()

    # Match @email (full email): @[\w.+-]+@[\w.-]+
    email_pattern = r"@([\w.+-]+@[\w.-]+)"
    for match in re.finditer(email_pattern, content):
        email = match.group(1)
        if email in org_member_emails and email not in seen:
            user_id = org_member_emails[email]
            mentioned_ids.append(user_id)
            seen.add(email)

    # Match @handle (alphanumeric + underscore): @(\w+)
    # Only if no email pattern matched it already
    handle_pattern = r"@(\w+)"
    for match in re.finditer(handle_pattern, content):
        handle = match.group(1)
        # Skip if it looks like an email domain (has a dot or is part of an email we already matched)
        if "." not in handle and handle not in seen:
            if handle in org_member_emails:
                user_id = org_member_emails[handle]
                mentioned_ids.append(user_id)
                seen.add(handle)

    return mentioned_ids
