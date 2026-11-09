"""Account mail for the local pilot.

Leave SMTP_HOST unset and the running server writes the message to its log.
Set SMTP_HOST, and optionally SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
SMTP_FROM, and SMTP_USE_TLS, to send through an SMTP server. A failed SMTP
send uses the same log. The message never includes a password. Sending mail
does not change a role or approve an assessment.
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.message import EmailMessage

OUTBOX: list[dict[str, str]] = []
echo = False


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST", "").strip())


def deliver(to: str, subject: str, body: str) -> None:
    """Record the message, send it when SMTP is configured, and otherwise log it."""
    OUTBOX.append({"to": to, "subject": subject, "body": body})
    del OUTBOX[:-50]
    if smtp_configured() and _smtp_send(to, subject, body):
        return
    if echo:
        print(
            "RUGD mail fallback. SMTP is not configured, or the SMTP send failed.\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            f"{body}",
            file=sys.stderr,
        )


def _smtp_send(to: str, subject: str, body: str) -> bool:
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587") or "587")
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", "").strip() or "RUGD Analyze <noreply@localhost>"
    use_tls = os.environ.get("SMTP_USE_TLS", "true").strip().lower() not in {"0", "false", "no", "off"}
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError):
        return False
    return True
