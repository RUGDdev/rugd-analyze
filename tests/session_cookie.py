"""Open a verified customer session against a running local server."""

from __future__ import annotations

import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid

from app.accounts import register_account
from app.review import SESSION_COOKIE
from app.store import set_email_verified


def open_customer(connection: sqlite3.Connection, base: str) -> tuple[str, str]:
    email = f"customer-{uuid.uuid4().hex[:10]}@pilot.example"
    user = register_account(connection, email=email, password="session-pass-1")
    set_email_verified(connection, user["id"])

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    request = urllib.request.Request(
        base + "/login",
        data=urllib.parse.urlencode({"email": email, "password": "session-pass-1"}).encode(),
        method="POST",
    )
    try:
        response = urllib.request.build_opener(NoRedirect).open(request)
    except urllib.error.HTTPError as exc:
        response = exc
    cookie = (response.headers.get("Set-Cookie") or "").split(";", 1)[0]
    if not cookie.startswith(SESSION_COOKIE + "="):
        raise AssertionError("login did not set a session cookie")
    return cookie, str(user["id"])


def claim(connection: sqlite3.Connection, assessment_id: str, user_id: str) -> None:
    """Attach a test draft to a customer. This does not run in the application."""
    connection.execute(
        "UPDATE assessments SET owner_user_id = ? WHERE id = ?",
        (user_id, assessment_id),
    )
    connection.commit()
