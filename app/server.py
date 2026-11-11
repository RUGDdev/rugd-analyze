"""HTTP server for RUGD Analyze. Local runs bind to 127.0.0.1. Production bind comes from config."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from html import escape
from typing import Any
from urllib.parse import parse_qs, urlparse

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.analysis import analyze_record
from app.config import (
    SECURITY_HEADERS,
    bind_host,
    bind_port,
    database_path,
    production_secret_error,
    public_base_url,
    session_cookie,
)
from app.market import export_market_observations, get_market_provider
from app.export import (
    export_advisor_package,
    export_assessment,
    export_drafts,
    export_research_package,
    research_package_markdown,
)
from app.adviser_flow import (
    apply_proposal,
    discard_proposal,
    note_provider_failure,
    note_provider_reply,
    receive_answer,
    start_conversation,
)
from app.analyst import answer, explain, get_analyst
from app.objectives import objective_by_id
from app.pages import (
    analyst_page,
    assistant_page,
    audit_html_page,
    analyze_index,
    assessment_form,
    dashboard,
    explore_page,
    layout,
    market_page,
    market_pulse_page,
    new_assessment_page,
    partner_page,
    forgot_password_page,
    login_page,
    logout_page,
    register_page,
    reset_password_page,
    verification_banner,
    verify_email_page,
    reports_page,
    advisor_summary_page,
    research_brief_page,
    results_page,
    share_panel,
    shared_assessment_page,
    reviewer_accounts_page,
    reviewer_home,
    reviewer_page,
    settings_page,
    validate_page,
)
from app.accounts import (
    RESET_NOTICE,
    AccountError,
    confirm_email,
    create_reviewer_account,
    register_account,
    request_password_reset,
    reset_password,
    send_verification,
)
import app.mail as account_mail
from app.share import ShareError, active_share_links, can_manage_share, issue_share_link, open_share, revoke_share
from app.review import (
    SESSION_COOKIE,
    SESSION_LIFETIME_SECONDS,
    ReviewError,
    approve_assessment,
    close_reviewer_session,
    open_account_session,
    result_with_stored_approval,
    reviewer_session_state,
)
from app.store import (
    BASELINE_ID,
    get_user_by_id,
    DEFAULT_DB,
    ISOLATION_CUSTOMER,
    connect,
    create_assessment,
    dismiss_welcome,
    create_linked_assessment,
    get_business_profile,
    label_for_new_assessment,
    list_business_profiles,
    get_assessment,
    list_approvals,
    list_assessments,
    list_reviewer_events,
    session_activity,
    list_guidance_notes,
    request_review,
    save_guidance_note,
    save_checklist,
    save_profile,
    save_notification_preferences,
    save_result,
    save_scenarios,
    seed,
)
from app.notifications import notify_owner, preferences_from_form
from app.ratelimit import AUTH_LIMIT_MESSAGE, AttemptLimiter, client_key


def _keep_venture_path(profile: dict[str, str], original: dict[str, Any]) -> None:
    """A later save cannot change the onboarding path or approve the assessment."""
    kept = str(original.get("venture_path") or "")
    if kept in {"startup", "existing"}:
        profile["venture_path"] = kept
    else:
        profile.pop("venture_path", None)
    profile.pop("human_review_approved", None)


class AppHandler(BaseHTTPRequestHandler):
    db_path = None

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/static/rugd-logo.png":
            logo = Path(__file__).resolve().parent / "static" / "rugd-logo.png"
            self._bytes(logo.read_bytes(), "image/png")
            return
        with self._db() as connection:
            self._request_connection = connection
            try:
                self._get_routes(connection, path)
            finally:
                self._request_connection = None

    def _get_routes(self, connection: Any, path: str) -> None:
        seed(connection)
        if path == "/":
            self._html(self._dashboard_page(connection))
        elif path == "/explore":
            records = list_assessments(connection)
            notes = {
                item["id"]: list_guidance_notes(connection, item["id"]) for item in records
            }
            self._html(explore_page(records, notes))
        elif path == "/analyze":
            self._html(analyze_index(list_assessments(connection)))
        elif path == "/validate":
            self._html(validate_page(None))
        elif path == "/partner":
            self._html(partner_page())
        elif path == "/market-pulse":
            self._html(market_pulse_page())
        elif path == "/market/export":
            query = parse_qs(urlparse(self.path).query)
            industry = (query.get("industry") or [""])[-1]
            geographic_market = (query.get("geographic_market") or [""])[-1]
            tier = (query.get("tier") or ["explore"])[-1]
            payload = json.dumps(
                export_market_observations(
                    industry,
                    geographic_market,
                    provider=get_market_provider(),
                    tier=tier,
                ),
                indent=2,
            ).encode("utf-8")
            self._bytes(payload, "application/json", disposition=_market_disposition(industry, geographic_market))
        elif path == "/market":
            query = parse_qs(urlparse(self.path).query)
            industry = (query.get("industry") or [""])[-1]
            geographic_market = (query.get("geographic_market") or [""])[-1]
            tier = (query.get("tier") or ["explore"])[-1]
            self._html(
                market_page(
                    list_assessments(connection),
                    industry,
                    geographic_market,
                    provider=get_market_provider(),
                    tier=tier,
                )
            )
        elif path == "/reports":
            self._html(reports_page(list_assessments(connection)))
        elif path == "/settings":
            with_user = None
            state = self._account_state(connection)
            user_id = str(state.get("user_id") or "")
            if state.get("active") and user_id:
                with_user = get_user_by_id(connection, user_id)
            self._html(settings_page(with_user))
        elif path == "/login":
            self._html(login_page(self._safe_next(self._query_value("next"), "/")))
        elif path == "/register":
            self._html(register_page())
        elif path == "/forgot-password":
            self._html(forgot_password_page())
        elif path == "/account/verify":
            self._verify_email(connection)
        elif path == "/account/reset":
            self._html(reset_password_page(self._query_value("token")))
        elif path == "/logout":
            self._html(logout_page(self._account_state(connection)))
        elif path == "/assessments":
            self._html(self._dashboard_page(connection, surface="assessments"))
        elif path == "/assessments/export":
            payload = json.dumps(export_drafts(list_assessments(connection)), indent=2).encode("utf-8")
            self._bytes(
                payload,
                "application/json",
                disposition=f'attachment; filename="rugd-drafts-{_today()}.json"',
            )
        elif path == "/assessments/new":
            self._html(
                new_assessment_page(
                    list_business_profiles(connection, isolation=ISOLATION_CUSTOMER)
                )
            )
        elif path == "/reviewer" or path.startswith("/reviewer/"):
            self._reviewer_get(connection, path)
        elif path.startswith("/assessments/"):
            self._assessment_get(connection, path)
        elif path.startswith("/share/"):
            self._share_get(connection, path)
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
            self._request_connection = connection
            try:
                self._post_routes(connection, path, form)
            finally:
                self._request_connection = None

    def _post_routes(self, connection: Any, path: str, form: dict[str, str]) -> None:
        seed(connection)
        if path == "/start":
            self._start_objective(connection, form)
            return
        if path == "/assessments":
            business_name = (form.get("business_name") or "Untitled").strip() or "Untitled"
            profile_id = (form.get("business_profile_id") or "").strip()
            posted_path = (form.get("venture_path") or "").strip()
            if posted_path and posted_path not in {"startup", "existing"}:
                self._html(
                    new_assessment_page(
                        list_business_profiles(connection, isolation=ISOLATION_CUSTOMER),
                        "Choose a startup idea or an existing or expanding business.",
                    ),
                    status=403,
                )
                return
            try:
                if profile_id:
                    business = get_business_profile(connection, profile_id)
                    if business is None or business["isolation"] != ISOLATION_CUSTOMER:
                        raise PermissionError(
                            "Only a customer business profile can be selected here."
                        )
                    business_name = str(business["display_name"] or business_name)
                    path_choice = str(business.get("venture_path") or "startup")
                else:
                    path_choice = posted_path or "startup"
                if path_choice not in {"startup", "existing"}:
                    path_choice = "startup"
                state = self._account_state(connection)
                owner = (
                    str(state.get("user_id") or "")
                    if state.get("active") and state.get("role") in {"customer", "reviewer"}
                    else ""
                )
                assessment_id = create_assessment(
                    connection,
                    business_name=business_name,
                    purpose=form.get("purpose") or "startup_feasibility",
                    tier=form.get("tier") or "explore",
                    pilot_label=label_for_new_assessment(business_name),
                    business_profile_id=profile_id or None,
                    owner_user_id=owner or None,
                    venture_path=path_choice,
                )
            except PermissionError:
                self._html(
                    layout(
                        "Not allowed",
                        "<h1>Not allowed</h1><p>That business profile cannot be linked to this draft. "
                        "The official baseline and named pilots stay isolated.</p>",
                    ),
                    status=403,
                )
                return
            self._redirect(
                f"/assessments/{assessment_id}",
                extra_cookies=[self._welcome_cookie()] if not owner else None,
            )
            return
        if path in {"/login", "/reviewer/session"}:
            if not self._auth_attempt_allowed():
                self._html(
                    login_page(self._safe_next(form.get("next") or "", "/"), AUTH_LIMIT_MESSAGE),
                    status=429,
                )
                return
            self._account_sign_in(connection, form)
            return
        if path == "/register":
            if not self._auth_attempt_allowed():
                self._html(register_page(AUTH_LIMIT_MESSAGE), status=429)
                return
            self._account_register(connection, form)
            return
        if path == "/welcome/dismiss":
            self._dismiss_welcome(connection)
            return
        if path == "/forgot-password":
            request_password_reset(
                connection,
                form.get("email") or "",
                base_url=self._public_base(),
            )
            self._html(forgot_password_page(RESET_NOTICE))
            return
        if path == "/account/reset":
            self._reset_password(connection, form)
            return
        if path == "/account/verification":
            self._resend_verification(connection)
            return
        if path == "/reviewer/accounts":
            self._create_reviewer_account(connection, form)
            return
        if path == "/settings/notifications":
            self._save_notification_preferences(connection, form)
            return
        if path in {"/logout", "/reviewer/session/sign-out"}:
            self._account_sign_out(connection, form)
            return
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 3 and parts[0] == "reviewer":
            self._reviewer_post(connection, parts, form)
            return
        if len(parts) >= 3 and parts[0] == "assessments":
            self._assessment_post(connection, parts, form)
            return
        if parts and parts[0] == "share":
            self._html(
                layout(
                    "Not allowed",
                    "<h1>Not allowed</h1><p>A read-only share cannot change the assessment or approve it.</p>",
                ),
                status=403,
            )
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
            stored = record.get("result") or {"engine_ran": False, "message": "Analyze has not been run."}
            self._html(results_page(record, stored, list_guidance_notes(connection, record["id"])))
        elif action == "advisor":
            self._advisor_get(connection, record, parts)
        elif action == "research":
            package = self._research_package(record)
            form = parts[3] if len(parts) > 3 else ""
            if form == "brief":
                self._html(research_brief_page(package))
            elif form == "markdown":
                payload = research_package_markdown(package).encode("utf-8")
                self._bytes(
                    payload,
                    "text/markdown; charset=utf-8",
                    disposition=_download_disposition(record, record.get("result") or {}, "research", "md"),
                )
            else:
                payload = json.dumps(package, indent=2).encode("utf-8")
                self._bytes(
                    payload,
                    "application/json",
                    disposition=_download_disposition(record, record.get("result") or {}, "research", "json"),
                )
        elif action == "export":
            payload = json.dumps(export_assessment(record), indent=2).encode("utf-8")
            self._bytes(
                payload,
                "application/json",
                disposition=_download_disposition(record, record.get("result") or {}, "export", "json"),
            )
        elif action == "analyst":
            result = record["result"]
            self._html(analyst_page(record, explain(record, result)))
        elif action == "report" and len(parts) > 3 and parts[3] == "download":
            payload, result = self._report_bytes(connection, record)
            self._bytes(
                payload,
                "text/markdown; charset=utf-8",
                disposition=_download_disposition(record, result, "report", "md"),
            )
        elif action == "report":
            payload, _result = self._report_bytes(connection, record)
            self._bytes(payload, "text/markdown; charset=utf-8")
        elif action == "audit" and len(parts) > 3 and parts[3] == "html":
            result = record.get("result") or self._run(connection, record)
            self._html(
                audit_html_page(
                    record,
                    result,
                    list_reviewer_events(connection, record["id"]),
                    notes=list_guidance_notes(connection, record["id"]),
                )
            )
        elif action == "audit" and len(parts) > 3 and parts[3] == "print":
            result = record.get("result") or self._run(connection, record)
            self._html(
                audit_html_page(
                    record,
                    result,
                    list_reviewer_events(connection, record["id"]),
                    printable=True,
                    notes=list_guidance_notes(connection, record["id"]),
                )
            )
        elif action == "audit" and len(parts) > 3 and parts[3] == "download":
            payload, result = self._audit_bytes(connection, record)
            self._bytes(
                payload,
                "application/json",
                disposition=_download_disposition(record, result, "audit", "json"),
            )
        elif action == "audit":
            payload, _result = self._audit_bytes(connection, record)
            self._bytes(payload, "application/json")
        elif action == "validate":
            self._html(validate_page(record, list_guidance_notes(connection, record["id"])))
        else:
            page = assessment_form(record, notes=list_guidance_notes(connection, record["id"]))
            state = self._account_state(connection)
            if can_manage_share(state, record):
                revealed = ""
                token = self._query_value("share")
                if token:
                    try:
                        shared = open_share(connection, token)
                    except ShareError:
                        shared = None
                    if shared is not None and shared["id"] == record["id"]:
                        revealed = f"/share/{token}"
                panel = share_panel(
                    record,
                    active_share_links(connection, record["id"]),
                    reveal_path=revealed,
                )
                page = page.replace("</main>", panel + "</main>", 1)
            self._html(page)

    def _assessment_post(self, connection: Any, parts: list[str], form: dict[str, str]) -> None:
        assessment_id = parts[1]
        action = parts[2] if len(parts) > 2 else ""
        record = get_assessment(connection, assessment_id)
        if record is None:
            self._html(layout("Not found", "<h1>Assessment not found</h1>"), status=404)
            return
        if action == "linked":
            try:
                linked_id = create_linked_assessment(
                    connection,
                    assessment_id,
                    tier=form.get("tier") or record["tier"],
                    purpose=form.get("purpose") or record["purpose"],
                )
            except PermissionError:
                self._html(
                    layout(
                        "Not allowed",
                        "<h1>Not allowed</h1><p>The official baseline profile cannot be linked to a draft.</p>",
                    ),
                    status=403,
                )
                return
            self._redirect(f"/assessments/{linked_id}")
            return
        if action == "guidance":
            self._save_guidance(connection, record, form)
            return
        if action == "checklist":
            self._save_checklist(connection, record, form)
            return
        if action == "assistant":
            self._assistant_post(connection, record, form)
            return
        if action == "adviser":
            self._adviser_turn(connection, record, parts, form)
            return
        if action == "scenarios":
            self._save_scenario(connection, record, form)
            return
        if action == "save":
            if record["read_only"]:
                self._html(assessment_form(record, "This baseline cannot be edited."), status=403)
                return
            profile = dict(record["profile"])
            profile.update(form)
            profile["inputs_are_measured"] = form.get("inputs_are_measured") == "true"
            _keep_venture_path(profile, record["profile"])
            save_profile(connection, assessment_id, profile)
            self._redirect(f"/assessments/{assessment_id}")
            return
        if action == "analyze":
            if not record["read_only"]:
                profile = dict(record["profile"])
                if form:
                    profile.update({key: value for key, value in form.items() if key != "human_review_approved"})
                    profile["inputs_are_measured"] = form.get("inputs_are_measured") == "true"
                    _keep_venture_path(profile, record["profile"])
                    save_profile(connection, assessment_id, profile)
                    record = get_assessment(connection, assessment_id)
            assert record is not None
            result = self._run(connection, record)
            save_result(connection, assessment_id, record.get("intake") if record["read_only"] else result.get("intake"), result)
            self._redirect(f"/assessments/{assessment_id}/results")
            return
        if action == "review-request":
            request_review(connection, assessment_id)
            notify_owner(connection, record, "review_requested")
            self._redirect(f"/assessments/{assessment_id}/validate")
            return
        if action == "share":
            self._share_post(connection, record, parts, form)
            return
        self._html(layout("Not found", "<h1>Not found</h1>"), status=404)

    def _share_get(self, connection: Any, path: str) -> None:
        parts = [part for part in path.split("/") if part]
        token = parts[1] if len(parts) > 1 else ""
        try:
            record = open_share(connection, token)
        except ShareError as exc:
            self._html(layout("Read-only share", f"<h1>Read-only share</h1><p>{escape(str(exc))}</p>"), status=403)
            return
        action = parts[2] if len(parts) > 2 else ""
        if action == "advisor":
            self._advisor_response(
                record,
                list_guidance_notes(connection, record["id"]),
                parts[3] if len(parts) > 3 else "",
                link_base=f"/share/{token}/advisor",
                active="none",
            )
            return
        if action:
            self._html(layout("Not found", "<h1>Not found</h1>"), status=404)
            return
        stored = record.get("result") or {"engine_ran": False}
        self._html(
            shared_assessment_page(
                record,
                stored,
                list_guidance_notes(connection, record["id"]),
                share_path=f"/share/{token}",
            )
        )

    def _advisor_get(self, connection: Any, record: dict[str, Any], parts: list[str]) -> None:
        form = parts[3] if len(parts) > 3 else ""
        self._advisor_response(
            record,
            list_guidance_notes(connection, record["id"]),
            form,
            link_base=f"/assessments/{record['id']}/advisor",
            active="",
        )

    def _advisor_response(
        self,
        record: dict[str, Any],
        notes: list[dict[str, Any]],
        form: str,
        *,
        link_base: str,
        active: str,
    ) -> None:
        stored = record.get("result") if isinstance(record.get("result"), dict) else None
        package = export_advisor_package(record, stored, notes)
        if form == "download":
            payload = json.dumps(package, indent=2).encode("utf-8")
            self._bytes(
                payload,
                "application/json",
                disposition=_download_disposition(record, stored or {}, "advisor", "json"),
            )
            return
        if form == "print":
            self._html(
                advisor_summary_page(
                    package,
                    printable=True,
                    link_base="",
                    active=active,
                    review_requested=bool(record.get("review_requested")),
                )
            )
            return
        if form:
            self._html(layout("Not found", "<h1>Not found</h1>"), status=404)
            return
        self._html(
            advisor_summary_page(
                package,
                link_base=link_base,
                active=active,
                review_requested=bool(record.get("review_requested")),
            )
        )

    def _share_post(self, connection: Any, record: dict[str, Any], parts: list[str], form: dict[str, str]) -> None:
        state = self._account_state(connection)
        try:
            if len(parts) >= 5 and parts[4] == "revoke":
                revoke_share(connection, record, state, parts[3])
                self._redirect(f"/assessments/{record['id']}")
                return
            issued = issue_share_link(connection, record, state, form.get("lifetime") or "7d")
        except ShareError as exc:
            self._html(layout("Not allowed", f"<h1>Not allowed</h1><p>{escape(str(exc))}</p>"), status=403)
            return
        notify_owner(connection, record, "assessment_shared")
        self._redirect(f"/assessments/{record['id']}?share={issued['token']}")

    def _save_scenario(self, connection: Any, record: dict[str, Any], form: dict[str, str]) -> None:
        from app.scenarios import update_scenarios

        stored = record.get("result") if isinstance(record.get("result"), dict) else None
        if not stored or not stored.get("engine_ran"):
            self._html(
                results_page(
                    record,
                    stored or {"engine_ran": False, "message": "Analyze has not been run."},
                    list_guidance_notes(connection, record["id"]),
                ),
                status=400,
            )
            return
        try:
            state = update_scenarios(record, form.get("case") or "")
        except ValueError as exc:
            self._html(
                layout("Not allowed", f"<h1>Not allowed</h1><p>{escape(str(exc))}</p>"),
                status=400,
            )
            return
        save_scenarios(connection, record["id"], state)
        self._redirect(f"/assessments/{record['id']}/results")

    def _save_checklist(self, connection: Any, record: dict[str, Any], form: dict[str, str]) -> None:
        from app.checklist import apply_posted, posted_checks

        notes = list_guidance_notes(connection, record["id"])
        state = apply_posted(record, posted_checks(form), record.get("result"), notes)
        save_checklist(connection, record["id"], state)
        destination = form.get("return_to") or "draft"
        if destination == "explore":
            self._redirect("/explore")
            return
        if destination == "results":
            self._redirect(f"/assessments/{record['id']}/results")
            return
        self._redirect(f"/assessments/{record['id']}")

    def _save_guidance(self, connection: Any, record: dict[str, Any], form: dict[str, str]) -> None:
        if record["read_only"] or record["id"] == BASELINE_ID:
            self._html(
                layout(
                    "Not allowed",
                    "<h1>Not allowed</h1><p>Educational notes cannot be stored on the official baseline. "
                    "This note was not saved and the engine was not run.</p>",
                ),
                status=403,
            )
            return
        try:
            save_guidance_note(
                connection,
                record["id"],
                form.get("pillar_id") or "",
                form.get("note") or "",
            )
        except ValueError as exc:
            self._html(
                assessment_form(
                    record,
                    str(exc),
                    list_guidance_notes(connection, record["id"]),
                ),
                status=400,
            )
            return
        if record.get("tier") == "explore":
            self._redirect(f"/assessments/{record['id']}")
        else:
            self._redirect(f"/assessments/{record['id']}/results")

    def _research_package(self, record: dict[str, Any]) -> dict[str, Any]:
        result = record.get("result") if isinstance(record.get("result"), dict) else None
        stored = result or {"engine_ran": False, "message": "Analyze has not been run."}
        profile = record.get("profile") or {}
        try:
            analyst_lines = explain(record, stored)
        except Exception:
            analyst_lines = ["Analyst explanation is not available. The demonstration fallback applies."]
        market = export_market_observations(
            str(profile.get("industry") or ""),
            str(profile.get("market") or profile.get("geographic_market") or ""),
            provider=get_market_provider(),
            tier="partner",
        )
        return export_research_package(record, stored, market=market, analyst_lines=analyst_lines)

    def _report_bytes(self, connection: Any, record: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
        result = self._ensure_result(connection, record)
        body = result.get("report_markdown") or result.get("message") or "No report."
        audit_link = f"/assessments/{record['id']}/audit/html"
        if audit_link not in body:
            body += f"\n\nHTML audit view: {audit_link}\n"
        return body.encode("utf-8"), result

    def _audit_bytes(self, connection: Any, record: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
        result = self._ensure_result(connection, record)
        payload = dict(result.get("audit") or {"human_review_approved": False, "message": result.get("message")})
        payload["approvals"] = [] if record["read_only"] else list_approvals(connection, record["id"])
        payload["reviewer_events"] = list_reviewer_events(connection, record["id"])
        payload["human_review_approved"] = bool(record["human_review_approved"])
        if not record["human_review_approved"]:
            readiness = payload.get("investor_readiness")
            if isinstance(readiness, dict):
                readiness["human_review_approved"] = False
        return json.dumps(payload, indent=2).encode("utf-8"), result

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
        if path == "/reviewer/accounts":
            state = self._reviewer_session_state(connection)
            if not state.get("active") or state.get("role") != "reviewer":
                detail = (
                    "A customer account cannot create a reviewer."
                    if state.get("active") and state.get("role") == "customer"
                    else "A signed-in reviewer is required to create a reviewer."
                )
                self._html(
                    layout(
                        "Not allowed",
                        f"<h1>Not allowed</h1><p>{detail}</p>",
                    ),
                    status=403,
                )
                return
            self._html(reviewer_accounts_page())
            return
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
        if not state.get("active") or state.get("role") != "reviewer":
            if state.get("active") and state.get("role") == "customer":
                reason = "a customer account"
            elif state.get("state") == "expired":
                reason = "expired"
            else:
                reason = "missing or signed out"
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
        updated = get_assessment(connection, assessment_id)
        if updated is not None:
            notify_owner(connection, updated, "review_recorded")
        self._redirect(f"/reviewer/assessments/{assessment_id}")

    def _verify_email(self, connection: Any) -> None:
        try:
            confirm_email(connection, self._query_value("token"))
        except AccountError as exc:
            self._html(verify_email_page(str(exc)), status=400)
            return
        self._html(
            verify_email_page(
                "Email verified. Your role is unchanged. "
                "This does not approve an assessment or grant investor-ready status."
            )
        )

    def _reset_password(self, connection: Any, form: dict[str, str]) -> None:
        token = form.get("token") or ""
        password = form.get("password") or ""
        if password != (form.get("password_confirm") or ""):
            self._html(reset_password_page(token, "Passwords do not match."), status=400)
            return
        try:
            reset_password(connection, token, password)
        except AccountError as exc:
            self._html(reset_password_page(token, str(exc)), status=400)
            return
        self._html(
            login_page(
                "/",
                "Password updated. Your role is unchanged. "
                "This does not approve an assessment or grant investor-ready status.",
            )
        )

    def _resend_verification(self, connection: Any) -> None:
        state = self._account_state(connection)
        user_id = str(state.get("user_id") or "")
        user = get_user_by_id(connection, user_id) if state.get("active") and user_id else None
        if user is None:
            self._html(
                layout("Not allowed", "<h1>Not allowed</h1><p>Log in to send a verification email.</p>"),
                status=403,
            )
            return
        if not user["email_verified"]:
            send_verification(connection, user, base_url=self._public_base())
        self._redirect("/")

    def _public_base(self) -> str:
        return public_base_url(self.headers.get("Host") or "")

    def _auth_attempt_allowed(self) -> bool:
        limiter = getattr(self.server, "auth_limiter", None)
        if limiter is None:
            return True
        peer = str(self.client_address[0]) if self.client_address else ""
        return limiter.allow(client_key(peer, self.headers.get("X-Forwarded-For")))

    def _dashboard_page(self, connection: Any, surface: str = "home") -> str:
        state = self._account_state(connection)
        user_id = str(state.get("user_id") or "")
        if not state.get("active") or not user_id:
            return dashboard([])
        owned = [
            item
            for item in list_assessments(connection)
            if str(item.get("owner_user_id") or "") == user_id
        ]
        return dashboard(owned, signed_in=True, viewer_id=user_id, surface=surface)

    def _welcome_cookie(self) -> str:
        return session_cookie("rugd_welcome", "dismissed", 60 * 60 * 24 * 365)

    def _dismiss_welcome(self, connection: Any) -> None:
        state = self._account_state(connection)
        user_id = str(state.get("user_id") or "")
        if state.get("active") and user_id:
            dismiss_welcome(connection, user_id)
            self._redirect("/")
            return
        self._redirect("/", extra_cookies=[self._welcome_cookie()])

    def _account_register(self, connection: Any, form: dict[str, str]) -> None:
        password = form.get("password") or ""
        if password != (form.get("password_confirm") or ""):
            self._html(
                register_page("Passwords do not match."),
                status=403,
            )
            return
        posted_role = (form.get("role") or "customer").strip()
        if posted_role != "customer":
            self._html(
                register_page("Self-registration creates a customer account."),
                status=403,
            )
            return
        try:
            register_account(
                connection,
                email=form.get("email") or "",
                password=password,
                base_url=self._public_base(),
            )
            session = open_account_session(
                connection,
                email=form.get("email") or "",
                password=password,
            )
        except (AccountError, ReviewError) as exc:
            self._html(register_page(str(exc)), status=403)
            return
        self._redirect(self._safe_next(form.get("next") or "", "/"), session["token"])

    def _create_reviewer_account(self, connection: Any, form: dict[str, str]) -> None:
        state = self._reviewer_session_state(connection)
        if not state.get("active") or state.get("role") != "reviewer":
            detail = (
                "A customer account cannot create a reviewer."
                if state.get("active") and state.get("role") == "customer"
                else "A signed-in reviewer is required to create a reviewer."
            )
            self._html(
                layout(
                    "Not allowed",
                    f"<h1>Not allowed</h1><p>{detail}</p>",
                ),
                status=403,
            )
            return
        password = form.get("password") or ""
        if password != (form.get("password_confirm") or ""):
            self._html(reviewer_accounts_page("Passwords do not match."), status=403)
            return
        try:
            create_reviewer_account(
                connection,
                email=form.get("email") or "",
                password=password,
                session=state,
            )
        except AccountError as exc:
            self._html(reviewer_accounts_page(str(exc)), status=403)
            return
        self._redirect("/reviewer/accounts")

    def _account_sign_in(self, connection: Any, form: dict[str, str]) -> None:
        try:
            session = open_account_session(
                connection,
                email=form.get("email") or "",
                password=form.get("password") or "",
            )
        except ReviewError as exc:
            self._html(login_page(self._safe_next(form.get("next") or "", "/"), str(exc)), status=403)
            return
        default = "/reviewer" if session.get("role") == "reviewer" else "/"
        spec = objective_by_id(form.get("objective") or "")
        if spec is not None and session.get("user_id"):
            assessment_id = self._open_objective(connection, spec, str(session["user_id"]))
            self._redirect(f"/assessments/{assessment_id}#adviser", session["token"])
            return
        self._redirect(self._safe_next(form.get("next") or "", default), session["token"])

    def _account_sign_out(self, connection: Any, form: dict[str, str]) -> None:
        close_reviewer_session(connection, self._cookies().get(SESSION_COOKIE, ""))
        self._redirect(self._safe_next(form.get("next") or "", "/"), clear_session=True)

    def _reviewer_session_state(self, connection: Any) -> dict[str, Any]:
        return reviewer_session_state(connection, self._cookies().get(SESSION_COOKIE, ""))

    def _account_state(self, connection: Any) -> dict[str, Any]:
        return self._reviewer_session_state(connection)

    def _start_objective(self, connection: Any, form: dict[str, str]) -> None:
        spec = objective_by_id(form.get("objective") or "")
        if spec is None:
            self._redirect("/")
            return
        state = self._account_state(connection)
        user_id = str(state.get("user_id") or "")
        if not state.get("active") or not user_id:
            self._html(login_page("/", objective=spec["id"]))
            return
        assessment_id = self._open_objective(connection, spec, user_id)
        self._redirect(f"/assessments/{assessment_id}#adviser")

    def _open_objective(self, connection: Any, spec: dict[str, str], user_id: str) -> str:
        assessment_id = create_assessment(
            connection,
            business_name="New draft",
            purpose=spec["purpose"],
            tier="explore",
            pilot_label="Customer draft. Not a completed assessment.",
            owner_user_id=user_id,
            venture_path=spec["venture_path"],
        )
        record = get_assessment(connection, assessment_id)
        assert record is not None
        profile = dict(record["profile"])
        profile["customer_objective"] = spec["id"]
        start_conversation(profile, spec["label"])
        save_profile(connection, assessment_id, profile)
        return assessment_id

    def _adviser_turn(
        self,
        connection: Any,
        record: dict[str, Any],
        parts: list[str],
        form: dict[str, str],
    ) -> None:
        if record.get("read_only"):
            self._html(
                layout(
                    "Not allowed",
                    "<h1>Not allowed</h1><p>The official baseline cannot be changed from the adviser.</p>",
                ),
                status=403,
            )
            return
        profile = dict(record["profile"])
        step = parts[3] if len(parts) > 3 else "message"
        if step == "apply":
            if form.get("decision") == "discard":
                discard_proposal(profile)
            else:
                apply_proposal(profile)
        else:
            receive_answer(profile, form.get("message") or "")
            analyst = get_analyst()
            if getattr(analyst, "uses_network", False):
                try:
                    lines = analyst.reply(
                        record,
                        record.get("result") if isinstance(record.get("result"), dict) else None,
                        form.get("message") or "",
                    )
                    note_provider_reply(profile, lines)
                except Exception:
                    note_provider_failure(profile)
        profile["human_review_approved"] = False
        save_profile(connection, record["id"], profile)
        self._redirect(f"/assessments/{record['id']}#adviser")

    def _assistant_post(self, connection: Any, record: dict[str, Any], form: dict[str, str]) -> None:
        question = (form.get("starter") or form.get("question") or "").strip()[:500]
        stored = record.get("result") if isinstance(record.get("result"), dict) else None
        lines = answer(record, stored, question)
        self._html(assistant_page(record, lines, question))

    def _save_notification_preferences(self, connection: Any, form: dict[str, str]) -> None:
        state = self._account_state(connection)
        user_id = str(state.get("user_id") or "")
        if not state.get("active") or not user_id:
            self._html(
                layout(
                    "Not allowed",
                    "<h1>Not allowed</h1><p>Sign in to store email preferences. "
                    "This does not approve an assessment.</p>",
                ),
                status=403,
            )
            return
        save_notification_preferences(connection, user_id, preferences_from_form(form))
        self._redirect("/settings")

    def _query_value(self, name: str) -> str:
        query = parse_qs(urlparse(self.path).query)
        return (query.get(name) or [""])[-1]

    def _safe_next(self, target: str, default: str) -> str:
        if (
            not target.startswith("/")
            or target.startswith("//")
            or "\\" in target
            or ":" in target
        ):
            return default
        return target

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
        self._bytes(self._with_verification_banner(page).encode("utf-8"), "text/html; charset=utf-8", status=status)

    def _with_verification_banner(self, page: str) -> str:
        if 'id="email-unverified"' in page or "<main>" not in page:
            return page
        connection = getattr(self, "_request_connection", None)
        if connection is None:
            return page
        state = self._account_state(connection)
        user_id = str(state.get("user_id") or "")
        if not state.get("active") or not user_id:
            return page
        user = get_user_by_id(connection, user_id)
        if user is None or user["email_verified"]:
            return page
        return page.replace("<main>", "<main>\n" + verification_banner(), 1)

    def _bytes(
        self,
        payload: bytes,
        content_type: str,
        status: int = 200,
        disposition: str | None = None,
    ) -> None:
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(payload)

    def _security_headers(self) -> None:
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)

    def _redirect(
        self,
        target: str,
        session_token: str | None = None,
        clear_session: bool = False,
        extra_cookies: list[str] | None = None,
    ) -> None:
        self.send_response(303)
        self._security_headers()
        self.send_header("Location", target)
        if session_token:
            self.send_header(
                "Set-Cookie",
                session_cookie(SESSION_COOKIE, session_token, SESSION_LIFETIME_SECONDS),
            )
        elif clear_session:
            self.send_header(
                "Set-Cookie",
                session_cookie(SESSION_COOKIE, "", 0),
            )
        for cookie in extra_cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def _download_disposition(record: dict[str, Any], result: dict[str, Any], kind: str, extension: str) -> str:
    raw_name = str(record.get("business_name") or "assessment")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", raw_name).strip("-") or "assessment"
    stamp = _download_stamp(record, result)
    filename = f"{slug}-{stamp}-{kind}.{extension}"
    return f'attachment; filename="{filename}"'


def _market_disposition(industry: str, geographic_market: str) -> str:
    raw = f"{industry or 'market'}-{geographic_market or 'selection'}"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-") or "market"
    return f'attachment; filename="{slug}-{_today()}-market.json"'


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _download_stamp(record: dict[str, Any], result: dict[str, Any]) -> str:
    candidates = []
    for source in (result.get("intake"), record.get("intake")):
        if isinstance(source, dict):
            candidates.append(source.get("as_of_date"))
    candidates.extend((record.get("updated_at"), record.get("created_at")))
    for value in candidates:
        text = str(value or "")[:10]
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return text
    return "undated"


def make_server(db_path, port: int = 8765, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    AppHandler.db_path = db_path
    server = ThreadingHTTPServer((host, port), AppHandler)
    server.auth_limiter = AttemptLimiter()  # type: ignore[attr-defined]
    return server


def main() -> None:
    account_mail.echo = True
    secret_error = production_secret_error()
    if secret_error:
        raise SystemExit(secret_error)
    server = make_server(database_path(DEFAULT_DB), port=bind_port(), host=bind_host())
    host, port = server.server_address
    print(f"RUGD Analyze is running at http://{host}:{port}")
    if bind_host() == "127.0.0.1":
        print("Press Ctrl+C to stop. This server is local only.")
    else:
        print("RUGD_ENV=production. The host terminates HTTPS. This build remains pilot-grade.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.server_close()
