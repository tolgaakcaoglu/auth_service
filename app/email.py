import smtplib
from email.message import EmailMessage

from .config import settings


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        raise ValueError("SMTP credentials are not configured")

    from_email = settings.smtp_from_email or settings.smtp_user
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{from_email}>"
    message["To"] = to_email
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


def build_verification_email(
    token: str,
    service_name: str | None = None,
    verification_method: str = "link",
) -> tuple[str, str, str]:
    link = f"{settings.app_base_url}{settings.root_path}/verify-email?token={token}"
    cleaned_service_name = (service_name or "").strip()
    subject_prefix = f"{cleaned_service_name} " if cleaned_service_name else ""
    subject = f"{subject_prefix}E-posta Onayi"
    if verification_method == "code":
        body = (
            f"{subject_prefix}icin e-posta adresinizi dogrulamak icin asagidaki kodu kullanin:\n\n"
            f"{token}\n\n"
            "Bu istegi siz yapmadiysaniz bu e-postayi yok sayabilirsiniz."
        )
        html_body = f"""\
<!doctype html>
<html lang="tr">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{subject}</title>
  </head>
  <body style="margin:0;padding:24px;background:#f5f6f8;font-family:Arial,Helvetica,sans-serif;color:#1f2933;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td align="center">
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;padding:28px;border:1px solid #e5e7eb;">
            <tr>
              <td>
                <h1 style="margin:0 0 12px 0;font-size:22px;line-height:1.3;color:#111827;">{subject}</h1>
                <p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;color:#374151;">
                  E-posta adresinizi dogrulamak icin asagidaki kodu kullanin.
                </p>
                <div style="margin:0 0 20px 0;padding:12px 16px;background:#f3f4f6;border-radius:8px;display:inline-block;font-size:20px;letter-spacing:2px;font-weight:600;">
                  {token}
                </div>
                <p style="margin:0;font-size:12px;line-height:1.6;color:#6b7280;">
                  Bu istegi siz yapmadiysaniz bu e-postayi yok sayabilirsiniz.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
        return subject, body, html_body

    body = (
        f"{subject_prefix}icin e-posta adresinizi dogrulamak icin asagidaki linke tiklayin:\n\n"
        f"{link}\n\n"
        "Bu istegi siz yapmadiysaniz bu e-postayi yok sayabilirsiniz."
    )
    html_body = f"""\
<!doctype html>
<html lang="tr">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{subject}</title>
  </head>
  <body style="margin:0;padding:24px;background:#f5f6f8;font-family:Arial,Helvetica,sans-serif;color:#1f2933;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td align="center">
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;padding:28px;border:1px solid #e5e7eb;">
            <tr>
              <td>
                <h1 style="margin:0 0 12px 0;font-size:22px;line-height:1.3;color:#111827;">{subject}</h1>
                <p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;color:#374151;">
                  E-posta adresinizi dogrulamak icin asagidaki butona tiklayin.
                </p>
                <p style="margin:0 0 20px 0;">
                  <a href="{link}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:8px;font-size:14px;">
                    E-postami Dogrula
                  </a>
                </p>
                <p style="margin:0 0 12px 0;font-size:12px;line-height:1.6;color:#6b7280;">
                  Buton calismazsa, asagidaki linki tarayicinizda acin:
                </p>
                <p style="margin:0 0 20px 0;font-size:12px;line-height:1.6;word-break:break-all;">
                  <a href="{link}" style="color:#2563eb;text-decoration:none;">{link}</a>
                </p>
                <p style="margin:0;font-size:12px;line-height:1.6;color:#6b7280;">
                  Bu istegi siz yapmadiysaniz bu e-postayi yok sayabilirsiniz.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    return subject, body, html_body


def build_password_reset_email(token: str) -> tuple[str, str]:
    link = f"{settings.app_base_url}{settings.root_path}/password/reset?token={token}"
    subject = "Reset your password"
    body = (
        "You can reset your password using the link below:\n\n"
        f"{link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    return subject, body
