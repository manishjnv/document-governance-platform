"""Minimal SMTP email sending (stdlib smtplib -- no email-provider SDK
needed for plain SMTP). Used by the OTP login flow.

# ponytail: synchronous smtplib call wrapped in asyncio.to_thread rather
# than an async SMTP client library -- one send per OTP request, not a
# hot path; matches the RCA #6 rule (never block the event loop on a sync
# call) without pulling in aiosmtplib for a single call site.
"""

import logging
import smtplib
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> bool:
    """Sends via SMTP if configured; otherwise logs the message and
    returns False (mirrors the existing password-reset "log only"
    fallback for local dev with no SMTP credentials)."""
    if not settings.smtp_server:
        logger.info(f"SMTP not configured -- would send to {to}: {subject}\n{body}")
        return False

    import asyncio

    def _send() -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = to

        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to], msg.as_string())

    try:
        await asyncio.to_thread(_send)
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False
