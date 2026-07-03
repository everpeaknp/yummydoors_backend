from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings


class PasswordResetDeliveryResult(dict):
    delivered: bool
    channel: str | None
    reason: str | None


def smtp_is_configured() -> bool:
    return bool(
        settings.smtp_host
        and settings.smtp_from_email
        and settings.smtp_username
        and settings.smtp_password
    )


async def send_password_reset_code(*, recipient: str, code: str) -> PasswordResetDeliveryResult:
    if not smtp_is_configured():
        return PasswordResetDeliveryResult(delivered=False, channel="email", reason="smtp_not_configured")

    await asyncio.to_thread(_send_password_reset_code_sync, recipient=recipient, code=code)
    return PasswordResetDeliveryResult(delivered=True, channel="email", reason=None)


def _send_password_reset_code_sync(*, recipient: str, code: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Your YummyDoors password reset code"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        (
            "Use this YummyDoors password reset code to continue:\n\n"
            f"{code}\n\n"
            f"This code expires in {settings.reset_code_expire_minutes} minutes."
        )
    )

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
