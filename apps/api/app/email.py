"""Minimal SMTP email sending (stdlib smtplib -- no email-provider SDK
needed for plain SMTP). Used by the OTP login flow.

# ponytail: synchronous smtplib call wrapped in asyncio.to_thread rather
# than an async SMTP client library -- one send per OTP request, not a
# hot path; matches the RCA #6 rule (never block the event loop on a sync
# call) without pulling in aiosmtplib for a single call site.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str, html_body: str | None = None) -> bool:
    """Sends via SMTP if configured; otherwise logs the message and
    returns False (mirrors the existing password-reset "log only"
    fallback for local dev with no SMTP credentials). html_body is
    optional -- plain-text-only callers (or a dev fallback log) still
    work; when given, the email is multipart/alternative so clients that
    render HTML show the styled version and everything else falls back
    to plain text."""
    if not settings.smtp_server:
        logger.info(f"SMTP not configured -- would send to {to}: {subject}\n{body}")
        return False

    import asyncio

    def _send() -> None:
        if html_body:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
        else:
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


def otp_email_html(code: str) -> str:
    """Branded HTML for the OTP login email -- self-contained inline CSS
    (no external stylesheet/CDN, so it renders consistently across email
    clients that strip <head> or block remote assets)."""
    return f"""\
<div style="background:#f2f1ea;padding:32px 16px;font-family:Georgia,'Times New Roman',serif;">
  <div style="max-width:480px;margin:0 auto;">
    <div style="font-size:20px;font-weight:bold;color:#1a1a1a;padding:0 4px 16px;">ScopeWise</div>
    <div style="background:#ffffff;border-radius:8px;padding:32px;">
      <p style="font-size:11px;letter-spacing:1px;color:#2563eb;text-transform:uppercase;margin:0 0 8px;font-family:Arial,sans-serif;">Sign-in code</p>
      <h1 style="font-size:22px;margin:0 0 16px;color:#1a1a1a;">Your sign-in code</h1>
      <p style="font-size:14px;color:#333;margin:0 0 24px;font-family:Arial,sans-serif;">
        Enter this code to finish signing in to <strong>ScopeWise</strong>.
      </p>
      <div style="background:#f6f6f4;border-radius:8px;padding:24px;text-align:center;margin:0 0 24px;">
        <span style="font-family:'Courier New',monospace;font-size:32px;font-weight:bold;letter-spacing:8px;color:#1a1a1a;">{code}</span>
      </div>
      <p style="font-size:12px;color:#777;margin:0;font-family:Arial,sans-serif;">
        This code expires in 10 minutes. If you didn't request this, you can ignore this email.
      </p>
    </div>
  </div>
</div>
"""
