"""Async email delivery via SMTP (aiosmtplib).

If SMTP is not configured, the message is logged instead of sent so the
app still runs locally without an email provider.
"""
import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger("app.email")


async def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_configured:
        logger.warning(
            "SMTP not configured — email to %s not sent.\nSubject: %s\n%s",
            to,
            subject,
            body,
        )
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_STARTTLS,
    )
    logger.info("OTP email sent to %s", to)
