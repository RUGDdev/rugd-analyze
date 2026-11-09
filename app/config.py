"""Environment configuration for local runs and the Render pilot.

The default is the local server. RUGD_ENV=production changes the bind address,
the database path, and the session cookie. It does not enable billing, scoring,
or a customer approval control. Prototype warnings stay on.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "same-origin"),
)


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_production() -> bool:
    return os.environ.get("RUGD_ENV", "").strip().lower() == "production"


def secure_cookies_enabled() -> bool:
    """Secure cookies follow RUGD_ENV=production or SECURE_COOKIES=true."""
    return is_production() or _flag("SECURE_COOKIES")


def secret_key() -> str:
    return os.environ.get("SECRET_KEY", "")


def production_secret_error() -> str | None:
    """Production must name a secret. Local runs may omit it."""
    if not is_production():
        return None
    if len(secret_key()) < 32:
        return "SECRET_KEY must be set to at least 32 characters when RUGD_ENV=production."
    return None


def database_path(default: Path) -> Path:
    raw = os.environ.get("RUGD_DATABASE", "").strip()
    if not raw:
        return default
    return Path(raw)


def bind_host() -> str:
    if is_production():
        return "0.0.0.0"
    return "127.0.0.1"


def public_base_url(request_host: str = "") -> str:
    """Base used in account links. RUGD_PUBLIC_URL wins. Otherwise use the request host."""
    raw = os.environ.get("RUGD_PUBLIC_URL", "").strip().rstrip("/")
    if raw:
        return raw
    host = request_host.strip()
    if host and " " not in host and "\n" not in host and "\r" not in host:
        return f"http://{host}"
    return "http://127.0.0.1:8765"


def bind_port(default: int = 8765) -> int:
    if not is_production():
        return default
    raw = os.environ.get("PORT", "").strip() or "10000"
    return int(raw)


def session_storage_key(token: str) -> str:
    """Hash stored for a session. A SECRET_KEY peppers the hash. The raw token is not stored."""
    material = token.encode("utf-8")
    secret = secret_key().encode("utf-8")
    if secret:
        return hmac.new(secret, material, hashlib.sha256).hexdigest()
    return hashlib.sha256(material).hexdigest()


def session_cookie(name: str, token: str, max_age: int) -> str:
    parts = [
        f"{name}={token}",
        "HttpOnly",
        "Path=/",
        "SameSite=Lax",
        f"Max-Age={max_age}",
    ]
    if secure_cookies_enabled():
        parts.append("Secure")
    return "; ".join(parts)
