"""HTML pages for the local RUGD Analyze prototype."""

from __future__ import annotations

from html import escape
from typing import Any

from app import APP_VERSION
from app.analysis import ENGINE_PURPOSES, UNSUPPORTED_PURPOSES
from app.market import market_framework

NAV = (
    ("/", "Dashboard"),
    ("/explore", "Explore"),
    ("/analyze", "Analyze"),
    ("/validate", "Validate"),
    ("/partner", "Partner"),
    ("/assessments", "My Assessments"),
    ("/market", "Market Intelligence"),
    ("/reports", "Reports"),
    ("/settings", "Settings"),
)


def layout(title: str, body: str) -> str:
    links = "".join(
        f'<a href="{href}">{escape(label)}</a>' for href, label in NAV
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — RUGD Analyze</title>
<style>
:root {{
  --ink: #263746; --bronze: #A88958; --ivory: #F5F2EB; --stone: #E8E5DF;
  --gold: #E9D8B7; --slate: #27323B;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Georgia, "Times New Roman", serif; background: var(--ivory); color: var(--ink); }}
header {{ background: var(--slate); color: var(--ivory); padding: 1.2rem 1.5rem 0.6rem; }}
header p {{ margin: 0.2rem 0 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; font-family: "Segoe UI", sans-serif; font-size: 0.78rem; color: var(--gold); }}
nav {{ display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; padding-bottom: 0.8rem; font-family: "Segoe UI", sans-serif; }}
nav a {{ color: var(--ivory); text-decoration: none; border-bottom: 1px solid transparent; }}
nav a:hover {{ border-bottom-color: var(--bronze); }}
main {{ max-width: 980px; margin: 0 auto; padding: 1.5rem; }}
h1, h2 {{ font-weight: normal; }}
.banner {{ background: var(--gold); border-left: 4px solid var(--bronze); padding: 0.8rem 1rem; margin: 1rem 0; }}
.card {{ background: white; border: 1px solid var(--stone); padding: 1rem 1.1rem; margin: 0.8rem 0; }}
label {{ display: block; margin: 0.7rem 0 0.2rem; font-family: "Segoe UI", sans-serif; font-size: 0.92rem; }}
input, select, textarea {{ width: 100%; padding: 0.45rem; border: 1px solid var(--stone); background: var(--ivory); color: var(--ink); font: inherit; }}
button, .button {{ background: var(--ink); color: var(--ivory); border: 0; padding: 0.55rem 0.9rem; font-family: "Segoe UI", sans-serif; text-decoration: none; display: inline-block; margin: 0.3rem 0.4rem 0.3rem 0; }}
.muted {{ color: #5c6b76; font-family: "Segoe UI", sans-serif; font-size: 0.92rem; }}
table {{ width: 100%; border-collapse: collapse; font-family: "Segoe UI", sans-serif; }}
td, th {{ text-align: left; padding: 0.35rem 0.2rem; border-bottom: 1px solid var(--stone); }}
.flag {{ color: #7a2e2e; }}
pre {{ white-space: pre-wrap; font-family: Consolas, monospace; font-size: 0.86rem; }}
</style>
</head>
<body>
<header>
<strong>RUGD</strong>
<p>Analyze {escape(APP_VERSION)} · local prototype · not investor-approved</p>
<nav>{links}</nav>
</header>
<main>
{body}
</main>
</body>
</html>"""


def dashboard(records: list[dict[str, Any]]) -> str:
    items = "".join(
        f"<li><a href=\"/assessments/{escape(item['id'])}\">{escape(item['business_name'])}</a> "
        f"<span class=\"muted\">{escape(item['tier'])} · {escape(item['pilot_label'])}</span></li>"
        for item in records
    )
    body = f"""
<h1>Customer dashboard</h1>
<p class="muted">Local test profile. This prototype has no accounts and no production security.</p>
<div class="card">
<p>Working now: Explore intake, Analyze through the 0.1 engine, reports, and the audit.</p>
<p>Demonstration only: Market Intelligence, Validate review requests, and the Partner dashboard. Partner monitoring is not running.</p>
</div>
<p><a class="button" href="/assessments/new">Start a new assessment</a></p>
<h2>Assessment history</h2>
<ul>{items}</ul>
"""
    return layout("Dashboard", body)


def assessment_form(record: dict[str, Any], notice: str = "") -> str:
    profile = record["profile"]
    locked = "disabled" if record["read_only"] else ""
    purposes = []
    for key, label in {**ENGINE_PURPOSES, **UNSUPPORTED_PURPOSES}.items():
        selected = "selected" if profile.get("purpose") == key else ""
        purposes.append(f'<option value="{escape(key)}" {selected}>{escape(label)}</option>')
    tiers = []
    for key in ("explore", "analyze", "validate", "partner"):
        selected = "selected" if record["tier"] == key else ""
        tiers.append(f'<option value="{escape(key)}" {selected}>{escape(key.title())}</option>')
    banner = f'<div class="banner">{escape(record["pilot_label"])}</div>'
    if record["hypothetical"]:
        banner += '<div class="banner">Hypothetical demonstration. Figures are not verified market research.</div>'
    if notice:
        banner += f'<div class="banner">{escape(notice)}</div>'
    fields = _fields(profile, locked)
    action = "" if record["read_only"] else f"""
<form method="post" action="/assessments/{escape(record['id'])}/save">
{fields}
<label>Service tier</label>
<select name="tier">{''.join(tiers)}</select>
<label>Assessment purpose</label>
<select name="purpose">{''.join(purposes)}</select>
<button type="submit">Save draft</button>
<button type="submit" formaction="/assessments/{escape(record['id'])}/analyze">Run Analyze</button>
</form>
"""
    if record["read_only"]:
        action = f"""
{fields}
<p class="muted">Saving is disabled. You can still run the engine on the stored baseline.</p>
<form method="post" action="/assessments/{escape(record['id'])}/analyze">
<button type="submit">Run Analyze on the baseline</button>
</form>
"""
    body = f"""
<h1>{escape(record['business_name'])}</h1>
{banner}
<p class="muted">Tier {escape(record['tier'])}. Changing tier does not change a recommendation. Entered answers stay user-supplied assumptions.</p>
{action}
<p><a href="/assessments/{escape(record['id'])}/analyst">Open the Demonstration Analyst</a></p>
"""
    return layout(record["business_name"], body)


def _fields(profile: dict[str, Any], locked: str) -> str:
    def text(name: str, label: str, *, area: bool = False) -> str:
        value = escape(str(profile.get(name) or ""))
        control = (
            f'<textarea name="{name}" {locked}>{value}</textarea>'
            if area
            else f'<input name="{name}" value="{value}" {locked}>'
        )
        return f"<label>{escape(label)}</label>{control}"

    def choice(name: str, label: str) -> str:
        current = str(profile.get(name) or "")
        options = ['<option value="">Not answered</option>']
        for value, caption in (("yes", "Yes"), ("no", "No")):
            selected = "selected" if current == value else ""
            options.append(f'<option value="{value}" {selected}>{caption}</option>')
        return f"<label>{escape(label)}</label><select name=\"{name}\" {locked}>{''.join(options)}</select>"

    measured = "checked" if profile.get("inputs_are_measured") is True else ""
    return "".join(
        [
            text("business_name", "Business name"),
            text("concept", "Business concept", area=True),
            text("industry", "Industry"),
            text("market", "Geographic market"),
            text("stage", "Development stage"),
            text("products", "Products and services", area=True),
            text("customers", "Target customers", area=True),
            text("competition", "Competition", area=True),
            choice("demand_evidence", "Is there demand evidence? A yes here is still only a user-supplied assumption."),
            _verified_demand_fields(profile, locked),
            choice("operator_capacity_adequate", "Is operator capacity adequate?"),
            choice("unresolved_regulatory_or_liability", "Is there an unresolved regulatory or liability issue?"),
            choice("extraction_without_reinvestment", "Do stewardship indicators show extraction without reinvestment?"),
            "<h2>Startup capital</h2>",
            "<p class=\"muted\">The primary revenue path remains seats × occupancy × average ticket. Blank fields are not filled with invented values.</p>",
            text("construction_cost", "Construction cost"),
            text("equipment", "Equipment"),
            text("soft_costs", "Soft costs"),
            text("preopening_working_capital", "Pre-opening working capital"),
            text("contingency_pct", "Contingency percentage (0.10 = 10%)"),
            text("debt_share", "Debt share"),
            text("annual_interest_rate", "Annual interest rate"),
            text("amortization_years", "Amortization years"),
            text("seats", "Seats"),
            text("average_ticket", "Average ticket"),
            text("weekday_occupancy", "Weekday occupancy"),
            text("weekend_occupancy", "Weekend occupancy"),
            text("operating_days", "Operating days"),
            text("annual_fixed_costs", "Annual fixed costs"),
            text("contribution_margin", "Contribution margin"),
            text("downside_multiplier", "Downside occupancy multiplier"),
            "<h2>Monthly engine</h2>",
            text("initial_capital", "Initial capital"),
            text("monthly_fixed_costs", "Monthly fixed costs"),
            text("gross_margin_pct", "Gross margin"),
            text("projected_monthly_revenue_base", "Projected monthly base revenue"),
            f'<label><input type="checkbox" name="inputs_are_measured" value="true" {measured} {locked}> These monthly figures are measured</label>',
            text("evidence_notes", "Evidence notes", area=True),
        ]
    )


def _verified_demand_fields(profile: dict[str, Any], locked: str) -> str:
    source = str(profile.get("verified_record_source") or "")
    claim = str(profile.get("verified_demand_evidence") or "")
    source_options = [
        ("", "Not a verified record"),
        ("verified", "verified"),
    ]
    claim_options = [
        ("", "Not recorded"),
        ("true", "true"),
        ("false", "false"),
    ]

    def options(current: str, choices: list[tuple[str, str]]) -> str:
        rendered = []
        for value, caption in choices:
            selected = "selected" if current == value else ""
            rendered.append(f'<option value="{escape(value)}" {selected}>{escape(caption)}</option>')
        return "".join(rendered)

    revenue = escape(str(profile.get("verified_revenue_trailing_12m") or ""))
    rationale = escape(str(profile.get("verified_demand_rationale") or ""))
    return f"""
<h2>Verified demand record</h2>
<p class="muted">Separate from the customer question above. These fields are applied only when the source is verified and a rationale is present. A customer yes, a hypothetical demonstration, and an AI interpretation cannot clear INSUFFICIENT_DEMAND_EVIDENCE. This record does not approve the assessment.</p>
<label>Source for this record</label>
<select name="verified_record_source" {locked}>{options(source, source_options)}</select>
<label>Verified trailing revenue (revenue_trailing_12m)</label>
<input name="verified_revenue_trailing_12m" value="{revenue}" {locked}>
<label>Verified demand_evidence</label>
<select name="verified_demand_evidence" {locked}>{options(claim, claim_options)}</select>
<label>Rationale for the verified record</label>
<textarea name="verified_demand_rationale" {locked}>{rationale}</textarea>
"""


def results_page(record: dict[str, Any], result: dict[str, Any]) -> str:
    if not result.get("engine_ran"):
        body = f"<h1>Analyze</h1><div class=\"banner\">{escape(result.get('message', 'Analyze did not run.'))}</div>"
        return layout("Analyze", body)
    flags = "".join(f"<li class=\"flag\">{escape(flag)}</li>" for flag in result.get("blocking_flags") or []) or "<li>None</li>"
    gaps = "".join(f"<li>{escape(flag)}</li>" for flag in result.get("gap_flags") or []) or "<li>None</li>"
    missing = "".join(f"<li>{escape(item)}</li>" for item in result.get("missing") or []) or "<li>None listed</li>"
    financial = _financial_table(result.get("financial"))
    projection = f"<pre>{escape(result.get('projection_text') or '')}</pre>"
    body = f"""
<h1>Draft results for {escape(record['business_name'])}</h1>
<div class="banner">Draft recommendation. Human review is pending. This is not a final or investor-ready result.</div>
<div class="card">
{_view_summary_block(result)}
<p class="muted">Engine {escape(str(result.get('model_version')))}. Service tier on this file: {escape(record['tier'])}.</p>
</div>
<h2>Demand evidence</h2>
{_demand_status(result.get("demand") or {})}
<h2>Recommend-against flags</h2><ul>{flags}</ul>
<h2>Evidence gaps</h2><ul>{gaps}</ul>
<h2>Missing information</h2><ul>{missing}</ul>
<h2>Monthly engine</h2>{financial}
<h2>Startup capital views</h2>{projection}
<p><a class="button" href="/assessments/{escape(record['id'])}/report">Open report</a>
<a class="button" href="/assessments/{escape(record['id'])}/audit">Inspect audit</a></p>
"""
    return layout("Results", body)


def _view_summary_block(result: dict[str, Any]) -> str:
    from app.analysis import build_view_summary

    summary = build_view_summary(result)
    provenance = "".join(
        f"<li>{escape(str(row.get('field')))}: {escape(str(row.get('provenance')))}</li>"
        for row in summary.get("demand_provenance") or []
    ) or "<li>placeholder</li>"
    approved = "true" if summary["human_review_approved"] else "false"
    return f"""
<p><strong>Recommendation:</strong> {escape(str(summary.get('recommendation')))}</p>
<p><strong>Score:</strong> {escape(result.get('score_line', ''))}</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> {escape(str(summary.get('insufficient_demand_evidence')))}</p>
<p><strong>Investor readiness:</strong> {escape(str(summary.get('investor_readiness')))}</p>
<p><strong>Human review status:</strong> {escape(str(summary.get('human_review_status')))}</p>
<p><strong>human_review_approved:</strong> {approved}</p>
<p><strong>Demand evidence provenance:</strong></p>
<ul>{provenance}</ul>
"""


def _demand_status(demand: dict[str, Any]) -> str:
    status = str(demand.get("status") or "uncleared")
    captions = {
        "cleared": "Verified support met the documented rule. INSUFFICIENT_DEMAND_EVIDENCE is not active.",
        "unverified": "A customer claim is on file. DEMAND_EVIDENCE_UNVERIFIED remains, and the blocking flag is not cleared.",
        "uncleared": "INSUFFICIENT_DEMAND_EVIDENCE is active.",
    }
    caption = captions.get(status, captions["uncleared"])
    evidence = escape(str(demand.get("evidence") or ""))
    return f"""
<div class="card">
<p><strong>Status:</strong> {escape(status)}</p>
<p>{escape(caption)}</p>
<p>{evidence}</p>
<p class="muted">Clearing or leaving this flag does not mark the result investor-ready.</p>
</div>
"""


def _financial_table(financial: dict[str, Any] | None) -> str:
    if not financial:
        return "<p>Insufficient verified information to calculate.</p>"
    rows = ""
    for key in (
        "base_monthly_contribution",
        "base_monthly_cash_flow",
        "downside_monthly_cash_flow",
        "break_even_monthly_revenue",
        "months_to_break_even_base",
    ):
        rows += f"<tr><td>{escape(key)}</td><td>{escape(str(financial.get(key)))}</td></tr>"
    return f"<table>{rows}</table>"


def analyst_page(record: dict[str, Any], lines: list[str]) -> str:
    items = "".join(f"<li>{escape(line)}</li>" for line in lines)
    body = f"""
<h1>Demonstration Analyst</h1>
<div class="banner">Demonstration Analyst. No external AI service is connected. This explanation cannot change engine results, flags, approval, or investor readiness.</div>
<ul>{items}</ul>
"""
    return layout("Demonstration Analyst", body)


def market_page() -> str:
    body = f"""
<h1>Market Intelligence</h1>
{_market_block(market_framework())}
<p class="muted">The same demonstration snapshot is available on Partner. Neither view loads Census, BLS, or BEA data.</p>
"""
    return layout("Market Intelligence", body)


def validate_page(record: dict[str, Any] | None) -> str:
    if record is None:
        body = "<h1>Validate</h1><p>Open an assessment from My Assessments to request a review.</p>"
        return layout("Validate", body)
    requested = "A review has been requested." if record["review_requested"] else "No review has been requested."
    body = f"""
<h1>Validate</h1>
<div class="banner">Prototype only. Customers can request review. This screen cannot set human_review_approved.</div>
<p>{escape(record['business_name'])}: {escape(requested)}</p>
<p><strong>Human review status:</strong> pending</p>
<p>Human review status stays pending on this customer screen. Requesting a review does not approve it. Investor readiness stays on the existing gate.</p>
<form method="post" action="/assessments/{escape(record['id'])}/review-request">
<button type="submit">Request review</button>
</form>
"""
    return layout("Validate", body)


def reviewer_page(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    session: dict[str, Any] | None = None,
) -> str:
    result = result or {}
    flags = ", ".join(result.get("blocking_flags") or []) or "none loaded"
    readiness = result.get("readiness_status") or "not loaded"
    approved = "true" if record.get("human_review_approved") else "false"
    signed_in = bool(session and session.get("role") == "reviewer")
    if signed_in:
        auth_state = (
            f"signed in as {session.get('reviewer_identity')} "
            f"({session.get('authentication_method')})"
        )
    else:
        auth_state = "not signed in"
    if record.get("read_only"):
        control = "<p>The official baseline cannot be approved from this prototype.</p>"
    elif not signed_in:
        control = _reviewer_sign_in_form(f"/reviewer/assessments/{record['id']}")
    else:
        control = f"""
<form method="post" action="/reviewer/assessments/{escape(record['id'])}/approve">
<button type="submit">Record reviewer approval</button>
</form>
"""
    body = f"""
<h1>Reviewer control</h1>
<div class="banner">Reviewer control. Not a customer feature. Prototype-grade local session. This is not production authentication.</div>
<p><strong>Authentication state:</strong> {escape(auth_state)}</p>
<p>Assessment: {escape(record['business_name'])} ({escape(record['id'])})</p>
<p><strong>Recommendation:</strong> {escape(str(result.get('recommendation') or 'not loaded'))}</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE and other blocking flags:</strong> {escape(flags)}</p>
<p><strong>Investor readiness:</strong> {escape(str(readiness))}</p>
<p><strong>human_review_approved:</strong> {approved}</p>
<p class="muted">Recording approval does not clear demand evidence, change the recommendation, or grant investor-ready.</p>
{control}
"""
    return layout("Reviewer control", body)


def reviewer_home(session: dict[str, Any] | None) -> str:
    signed_in = bool(session and session.get("role") == "reviewer")
    state = (
        f"signed in as {session.get('reviewer_identity')} ({session.get('authentication_method')})"
        if signed_in
        else "not signed in"
    )
    form = "" if signed_in else _reviewer_sign_in_form("/reviewer")
    return layout(
        "Reviewer",
        f"""
<h1>Reviewer</h1>
<div class="banner">Prototype-grade local session. Not a customer feature. Not production authentication.</div>
<p><strong>Authentication state:</strong> {escape(state)}</p>
{form}
<p class="muted">Open a saved assessment reviewer screen after signing in.</p>
""",
    )


def _reviewer_sign_in_form(next_path: str) -> str:
    return f"""
<form method="post" action="/reviewer/session">
<input type="hidden" name="next" value="{escape(next_path)}">
<label>Reviewer identity</label>
<input name="reviewer_identity" value="Local prototype reviewer">
<label>Prototype passphrase</label>
<input name="reviewer_passphrase" type="password">
<button type="submit">Sign in as reviewer</button>
</form>
<p class="muted">Prototype sign-in. Not a customer feature. Not production authentication.</p>
"""


def partner_page() -> str:
    body = f"""
<h1>Partner</h1>
<div class="banner">Demonstration dashboard. Recurring monitoring has not been implemented.</div>
<div class="card">
<p>Partner is the planned tier for an established business that needs ongoing intelligence. A startup feasibility assessment is not required to enter this tier later.</p>
<p>No scheduled market, financial, or risk monitor is running.</p>
</div>
{_market_block(market_framework())}
"""
    return layout("Partner", body)


def _market_block(snapshot: dict[str, Any]) -> str:
    examples = "".join(f"<li>{escape(item)}</li>" for item in snapshot["synthetic_examples"])
    observations = snapshot["observations"] or ["No live observations are loaded."]
    loaded = "".join(f"<li>{escape(str(item))}</li>" for item in observations)
    return f"""
<div class="banner">{escape(snapshot['label'])}</div>
<div class="card">
<p><strong>Industry:</strong> {escape(str(snapshot['industry']))}. Shown as an example only.</p>
<p><strong>Geographic market:</strong> {escape(str(snapshot['geographic_market']))}. No Census, BLS, or BEA feed is connected.</p>
<p>Live feed connected: false. Monitoring active: false. Source dataset: none.</p>
<ul>{loaded}</ul>
</div>
<h2>Synthetic examples</h2>
<ul>{examples}</ul>
"""


def reports_page(records: list[dict[str, Any]]) -> str:
    items = "".join(
        f"<li><a href=\"/assessments/{escape(item['id'])}/report\">{escape(item['business_name'])} report</a> · "
        f"<a href=\"/assessments/{escape(item['id'])}/audit\">audit</a></li>"
        for item in records
    )
    return layout("Reports", f"<h1>Reports</h1><ul>{items}</ul><p class=\"muted\">Reports are drafts unless the existing gate and an authorized review say otherwise. This prototype does not write the official 0.1 output files.</p>")


def settings_page() -> str:
    body = """
<h1>Settings</h1>
<p>This copy runs on 127.0.0.1 for a local pilot. It has no customer accounts, no password store, and no payment processing.</p>
<p>LongArc / DVT is not connected. The Webflow site is not connected.</p>
<p>Authoritative calculations remain in the 0.1 Python engine.</p>
"""
    return layout("Settings", body)


def new_assessment_page() -> str:
    options = []
    for key, label in {**ENGINE_PURPOSES, **UNSUPPORTED_PURPOSES}.items():
        options.append(f'<option value="{escape(key)}">{escape(label)}</option>')
    body = f"""
<h1>New assessment</h1>
<p class="muted">Explore collects a draft. It is not a completed feasibility study.</p>
<form method="post" action="/assessments">
<label>Business name</label>
<input name="business_name" required>
<label>Purpose</label>
<select name="purpose">{''.join(options)}</select>
<label>Starting tier</label>
<select name="tier">
<option value="explore">Explore</option>
<option value="analyze">Analyze</option>
</select>
<button type="submit">Create draft</button>
</form>
<h2>Named pilots</h2>
<p class="muted">Bunny Hive and Small Town Pub do not have completed assessments. These buttons create empty drafts.</p>
<form method="post" action="/assessments"><input type="hidden" name="business_name" value="Bunny Hive"><input type="hidden" name="purpose" value="startup_feasibility"><input type="hidden" name="tier" value="explore"><button type="submit">Start Bunny Hive draft</button></form>
<form method="post" action="/assessments"><input type="hidden" name="business_name" value="Small Town Pub"><input type="hidden" name="purpose" value="startup_feasibility"><input type="hidden" name="tier" value="explore"><button type="submit">Start Small Town Pub draft</button></form>
"""
    return layout("New assessment", body)


def explore_page(records: list[dict[str, Any]]) -> str:
    return layout(
        "Explore",
        """
<h1>Explore</h1>
<div class="banner">Explore is an intake and gap check. It is not a completed feasibility study.</div>
<p>Use a saved draft to clarify the concept, capital assumptions, and missing evidence. Run Analyze only when you want the deterministic engine.</p>
<p><a class="button" href="/assessments/new">Start an Explore draft</a></p>
"""
        + "<ul>"
        + "".join(
            f"<li><a href=\"/assessments/{escape(item['id'])}\">{escape(item['business_name'])}</a></li>"
            for item in records
        )
        + "</ul>",
    )


def analyze_index(records: list[dict[str, Any]]) -> str:
    items = "".join(
        f"<li><a href=\"/assessments/{escape(item['id'])}/results\">{escape(item['business_name'])}</a></li>"
        for item in records
    )
    return layout("Analyze", f"<h1>Analyze</h1><p>Results come from the 0.1 deterministic engine.</p><ul>{items}</ul>")
