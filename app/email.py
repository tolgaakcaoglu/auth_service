import smtplib
from email.message import EmailMessage

from .config import settings


def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        raise ValueError("SMTP credentials are not configured")

    from_email = settings.smtp_from_email or settings.smtp_user
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{from_email}>"
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


def build_verification_email(token: str) -> tuple[str, str]:
    link = f"{settings.app_base_url}{settings.root_path}/verify-email?token={token}"
    subject = "Verify your email"
    body = (
        "Please verify your email by clicking the link below:\n\n"
        f"{link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    return subject, body


def build_password_reset_email(token: str) -> tuple[str, str]:
    link = f"{settings.app_base_url}{settings.root_path}/password/reset?token={token}"
    subject = "Reset your password"
    body = (
        "You can reset your password using the link below:\n\n"
        f"{link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    return subject, body
