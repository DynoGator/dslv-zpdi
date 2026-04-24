"""Pluggable email backends.

Only Gmail is wired up today. Adding a new backend is a two-step job:
    1. implement `send(msg, cfg)` that takes an EmailMessage + config dict.
    2. register it in `BACKENDS` below.

Nothing in this module imports project-specific modules — it's pure
plumbing and can be unit-tested without the full DSLV-ZPDI stack.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage


class SendError(Exception):
    pass


def send_gmail(msg: EmailMessage, cfg: dict) -> None:
    user = cfg.get("smtp_user", "").strip()
    password = cfg.get("smtp_password", "").strip()
    if not user or not password:
        raise SendError("gmail backend needs smtp_user + smtp_password (App Password)")
    host = cfg.get("smtp_host", "smtp.gmail.com")
    port = int(cfg.get("smtp_port", 587))
    try:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, password)
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise SendError(
            "Gmail rejected auth. If you're using a regular password, replace "
            "it with a Google App Password (https://myaccount.google.com/apppasswords)."
        ) from e
    except smtplib.SMTPException as e:
        raise SendError(f"SMTP error: {e}") from e


def send_smtp(msg: EmailMessage, cfg: dict) -> None:
    """Generic STARTTLS SMTP — same wire format as Gmail but parameterised."""
    user = cfg.get("smtp_user", "").strip()
    password = cfg.get("smtp_password", "").strip()
    host = cfg.get("smtp_host", "").strip()
    port = int(cfg.get("smtp_port", 587))
    if not host:
        raise SendError("smtp backend needs smtp_host")
    try:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            try:
                s.starttls()
                s.ehlo()
            except smtplib.SMTPNotSupportedError:
                # Plain SMTP — rare but allowed inside tight networks.
                pass
            if user and password:
                s.login(user, password)
            s.send_message(msg)
    except smtplib.SMTPException as e:
        raise SendError(f"SMTP error: {e}") from e


BACKENDS = {
    "gmail": send_gmail,
    "smtp": send_smtp,
}


def dispatch(msg: EmailMessage, cfg: dict) -> None:
    backend = (cfg.get("backend") or "gmail").lower()
    fn = BACKENDS.get(backend)
    if not fn:
        raise SendError(f"unknown backend '{backend}' (available: {', '.join(BACKENDS)})")
    fn(msg, cfg)
