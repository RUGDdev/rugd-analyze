"""Local HTTP server for RUGD Analyze 0.2. Binds to 127.0.0.1 only."""

from __future__ import annotations

import json
from html import escape
from typing import Any
from urllib.parse import parse_qs, urlparse

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.analysis import analyze_record
from app.analyst import explain
from app.pages import (
    analyst_page,
    audit_html_page,
    analyze_index,
    assessment_form,
    dashboard,
    explore_page,
    layout,
    market_page,
    new_assessment_page,
    partner_page,
    reports_page,
    results_page,
    reviewer_home,
    reviewer_page,
    settings_page,
    validate_page,
)
from app.review import (
    SESSION_LIFETIME_SECONDS,
    ReviewError,
    approve_assessment,
    close_reviewer_session,
    open_reviewer_session,
    result_with_stored_approval,
    reviewer_session_state,
)
from app.store import (
    DEFAULT_DB,
    connect,
    create_assessment,
    get_assessment,
    list_approvals,
    list_assessments,
    list_reviewer_events,
    session_activity,
    request_review,
    save_profile,
    save_result,
    seed,
)


class AppHandler(BaseHTTPRequestHandler):
    db_path = None

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        with self._db() as connection:
            seed(connection)
            if path == "/":
                self._html(dashboard(list_assessments(connection)))
            elif path == "/explore":
                self._html(explore_page(list_assessments(connection)))
            elif path == "/analyze":
                self._html(analyze_index(list_assessments(connection)))
            elif path == "/validate":
                self._html(validate_page(None))
            elif path == "/partner":
                self._html(partner_page())
            elif path == "/market":
                query = parse_qs(urlparse(self.path).query)
                industry = (query.get("industry") or [""])[-1]
                geographic_market = (query.get("geographic_market") or [""])[-1]
                self._html(market_page(list_assessments(connection), industry, geographic_market))
            elif path == "/reports":
                self._html(reports_page(list_assessments(connection)))
            elif path == "/settings":
                self._html(settings_page())
            elif path == "/assessments":
                self._html(dashboard(list_assessments(connection)))
            elif path == "/assessments/new":
                self._html(new_assessment_page())
            elif path == "/reviewer" or path.startswith("/reviewer/"):
                self._reviewer_get(connection, path)
            elif path.startswith("/assessments/"):
                self._assessment_get(connection, path)
            else:
                self._html(layout("Not found", "<h1>Not found</h1>"), status=404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        form = self._form()
        if "human_review_approved" in form:
            self._html(
                layout(
                    "Not allowed",
                    "<h1>Not allowed</h1><p>A customer session cannot set human_review_approved.</p>",
                ),
                status=403,
            )
            return
        with self._db() as connection:
            seed(connection)
            if path == "/assessments":
                assessment_id = create_assessment(
                    connection,
                    business_name=form.get("business_name") or "Untitled",
                    purpose=form.get("purpose") or "startup_feasibility",
                    tier=form.get("tier") or "explore",
                    pilot_label="Customer draft. Not a completed assessment.",
                )
                self._redirect(f"/assessments/{assessment_id}")
                return
            if path == "/reviewer/session":
                self._reviewer_sign_in(connection, form)
                return
            if path == "/reviewer/session/sign-out":
                self._reviewer_sign_out(connection, form)
                return
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 3 and parts[0] == "reviewer":
                self._reviewer_post(connection, parts, form)
                return
            if len(parts) >= 3 and parts[0] == "assessments":
                self._assessment_post(connection, parts, form)
                return
        self._html(layout("Not found", "<h1>Not found</h1>"), status=404)

    def _assessment_get(self, connection: Any, path: str) -> None:
        parts = [part for part in path.split("/") if part]
        assessment_id = parts[1]
        record = get_assessment(connection, assessment_id)
        if record is None:
            self._html(layout("Not found", "<h1>Assessment not found</h1>"), status=404)
            return
        action = parts[2] if len(parts) > 2 else ""
        if action == "results":
            self._html(results_page(record, self._ensure_result(connection, record)))
        elif action == "analyst":
            result = record["result"]
            self._html(analyst_page(record, explain(record, result)))
        elif action == "report":
            result = self._ensure_result(connection, record)
            body = result.get("report_markdown") or result.get("message") or "No report."
            audit_link = f"/assessments/{record['id']}/audit/html"
            if audit_link not in body:
                body += f"\n\nHTML audit view: {audit_link}\n"
            self._bytes(body.encode("utf-8"), "text/markdown; charset=utf-8")
        elif action == "audit" and len(parts) > 3 and parts[3] == "html":
            result = record.get("result") or self._run(connection, record)
            self._html(audit_html_page(record, result, list_reviewer_events(connection, record["id"])))
        elif action == "audit":
            result = self._ensure_result(connection, record)
            payload = dict(result.get("audit") or {"human_review_approved": False, "message": result.get("message")})
            payload["approvals"] = [] if record["read_only"] else list_approvals(connection, record["id"])
            payload["reviewer_events"] = list_reviewer_events(connection, record["id"])
            payload["human_review_approved"] = bool(record["human_review_approved"])
            if not record["human_review_approved"]:
                readiness = payload.get("investor_readiness")
                if isinstance(readiness, dict):
                    readiness["human_review_approved"] = False
            self._bytes(json.dumps(payload, indent=2).encode("utf-8"), "application/json")
        elif action == "validate":
            self._html(validate_page(record))
        else:
            self._html(assessment_form(record))

    def _assessment_post(self, connection: Any, parts: list[str], form: dict[str, str]) -> None:
        assessment_id = parts[1]
        action = parts[2] if len(parts) > 2 else ""
        record = get_assessment(connection, assessment_id)
        if record is None:
            self._html(layout("Not found", "<h1>Assessment not found</h1>"), status=404)
            return
        if action == "save":
            if record["read_only"]:
                self._html(assessment_form(record, "This baseline cannot be edited."), status=403)
                return
            profile = dict(record["profile"])
            profile.update(form)
            profile["inputs_are_measured"] = form.get("inputs_are_measured") == "true"
            profile.pop("human_review_approved", None)
            save_profile(connection, assessment_id, profile)
            self._redirect(f"/assessments/{assessment_id}")
            return
        if action == "analyze":
            if not record["read_only"]:
                profile = dict(record["profile"])
                if form:
                    profile.update({key: value for key, value in form.items() if key != "human_review_approved"})
                    profile["inputs_are_measured"] = form.get("inputs_are_measured") == "true"
                    save_profile(connection, assessment_id, profile)
                    record = get_assessment(connection, assessment_id)
            assert record is not None
            result = self._run(connection, record)
            save_result(connection, assessment_id, record.get("intake") if record["read_only"] else result.get("intake"), result)
            self._redirect(f"/assessments/{assessment_id}/results")
            return
        if action == "review-request":
            request_review(connection, assessment_id)
            self._redirect(f"/assessments/{assessment_id}/validate")
            return
        self._html(layout("Not found", "<h1>Not found</h1>"), status=404)

    def _ensure_result(self, connection: Any, record: dict[str, Any]) -> dict[str, Any]:
        if record.get("result"):
            return record["result"]
        result = self._run(connection, record)
        save_result(
            connection,
            record["id"],
            record.get("intake") if record["read_only"] else result.get("intake"),
            result,
        )
        return result

    def _reviewer_get(self, connection: Any, path: str) -> None:
        parts = [part for part in path.split("/") if part]
        if path == "/reviewer" or parts == ["reviewer"]:
            self._html(
                reviewer_home(
                    self._reviewer_session_state(connection),
                    session_activity(connection),
                )
            )
            return
        if len(parts) < 3 or parts[0] != "reviewer" or parts[1] != "assessments":
            self._html(layout("Not found", "<h1>Not found</h1>"), status=404)
            return
        record = get_assessment(connection, parts[2])
        if record is None:
            self._html(layout("Not found", "<h1>Assessment not found</h1>"), status=404)
            return
        result = record.get("result")
        self._html(
            reviewer_page(
                record,
                result,
                self._reviewer_session_state(connection),
                session_activity(connection),
            )
        )

    def _reviewer_post(self, connection: Any, parts: list[str], form: dict[str, str]) -> None:
        if len(parts) < 4 or parts[1] != "assessments" or parts[3] != "approve":
            self._html(layout("Not found", "<h1>Not found</h1>"), status=404)
            return
        assessment_id = parts[2]
        state = self._reviewer_session_state(connection)
        if not state.get("active"):
            reason = "expired" if state.get("state") == "expired" else "missing or signed out"
            self._html(
                layout(
                    "Not allowed",
                    "<h1>Not allowed</h1>"
                    f"<p>Reviewer session is {escape(reason)}. This is not a customer approval control.</p>",
                ),
                status=403,
            )
            return
        session = state
        try:
            approve_assessment(connection, assessment_id, session=session)
        except ReviewError as exc:
            self._html(layout("Not allowed", f"<h1>Not allowed</h1><p>{escape(str(exc))}</p>"), status=403)
            return
        except KeyError:
            self._html(layout("Not found", "<h1>Assessment not found</h1>"), status=404)
            return
        except ValueError as exc:
            self._html(layout("Reviewer", f"<h1>Reviewer</h1><p>{escape(str(exc))}</p>"), status=400)
            return
        self._redirect(f"/reviewer/assessments/{assessment_id}")

    def _reviewer_sign_in(self, connection: Any, form: dict[str, str]) -> None:
        try:
            session = open_reviewer_session(
                connection,
                reviewer_identity=form.get("reviewer_identity") or "",
                reviewer_passphrase=form.get("reviewer_passphrase") or "",
            )
        except ReviewError as exc:
            self._html(layout("Not allowed", f"<h1>Not allowed</h1><p>{escape(str(exc))}</p>"), status=403)
            return
        target = form.get("next") or "/reviewer"
        if not target.startswith("/reviewer/") or "\\" in target:
            target = "/reviewer"
        self._redirect(target, session["token"])

    def _reviewer_sign_out(self, connection: Any, form: dict[str, str]) -> None:
        close_reviewer_session(connection, self._cookies().get("rugd_reviewer", ""))
        target = form.get("next") or "/reviewer"
        if not target.startswith("/reviewer/") or "\\" in target:
            target = "/reviewer"
        self._redirect(target, clear_session=True)

    def _reviewer_session_state(self, connection: Any) -> dict[str, Any]:
        return reviewer_session_state(connection, self._cookies().get("rugd_reviewer", ""))

    def _cookies(self) -> dict[str, str]:
        jar: dict[str, str] = {}
        for part in (self.headers.get("Cookie") or "").split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            jar[key.strip()] = value.strip()
        return jar

    def _run(self, connection: Any, record: dict[str, Any]) -> dict[str, Any]:
        try:
            result = analyze_record(record)
        except ValueError as exc:
            result = {
                "ok": False,
                "engine_ran": False,
                "message": str(exc),
                "human_review_approved": False,
                "is_final": False,
            }
        result["human_review_approved"] = False
        result["is_final"] = False
        result["human_review_status"] = "pending"
        if isinstance(result.get("demand"), dict):
            result["demand"]["human_review_approved"] = False
            result["demand"]["investor_ready"] = False
        audit = result.get("audit")
        if isinstance(audit, dict):
            audit["human_review_approved"] = False
            readiness = audit.get("investor_readiness")
            if isinstance(readiness, dict):
                readiness["human_review_approved"] = False
            demand = audit.get("demand_evidence")
            if isinstance(demand, dict):
                demand["human_review_approved"] = False
                demand["investor_ready"] = False
        return result_with_stored_approval(record, result, connection)

    def _db(self):
        return connect(type(self).db_path)

    def _form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(raw, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    def _html(self, page: str, status: int = 200) -> None:
        self._bytes(page.encode("utf-8"), "text/html; charset=utf-8", status=status)

    def _bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _redirect(self, target: str, session_token: str | None = None, clear_session: bool = False) -> None:
        self.send_response(303)
        self.send_header("Location", target)
        if session_token:
            self.send_header(
                "Set-Cookie",
                f"rugd_reviewer={session_token}; HttpOnly; Path=/; SameSite=Lax; Max-Age={SESSION_LIFETIME_SECONDS}",
            )
        elif clear_session:
            self.send_header(
                "Set-Cookie",
                "rugd_reviewer=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0",
            )
        self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def make_server(db_path, port: int = 8765) -> ThreadingHTTPServer:
    AppHandler.db_path = db_path
    return ThreadingHTTPServer(("127.0.0.1", port), AppHandler)


def main() -> None:
    server = make_server(DEFAULT_DB)
    host, port = server.server_address
    print(f"RUGD Analyze is running at http://{host}:{port}")
    print("Press Ctrl+C to stop. This server is local only.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.server_close()
