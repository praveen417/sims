import logging
import smtplib
import ssl
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("sims.mail")


def send_mail(to: str, subject: str, html: str) -> bool:
    """Send one HTML email. Never raises: a mail problem must not break the portal."""
    if not settings.SMTP_HOST:
        log.warning("SMTP_HOST not set - email '%s' to %s not sent", subject, to)
        return False
    if not to:
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.SMTP_FROM, to, subject
    msg.set_content("This message needs an HTML-capable mail client.")
    msg.add_alternative(html, subtype="html")
    try:
        if settings.SMTP_SSL:
            s = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20, context=ssl.create_default_context())
        else:
            s = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
            if settings.SMTP_STARTTLS:
                s.starttls(context=ssl.create_default_context())
        with s:
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001
        log.error("Email to %s failed: %s", to, e)
        return False
