"""HTML pages for the local RUGD Analyze prototype."""

from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import urlencode

from app import APP_VERSION
from app.analyst import get_analyst
from app.analysis import ENGINE_PURPOSES, UNSUPPORTED_PURPOSES
from app.store import (
    HYPOTHETICAL_DEMO_LABEL,
    RESTAURANT_ID,
    RESTAURANT_VERIFIED_ID,
    is_named_pilot,
    named_pilot_is_empty,
)
from app.market import (
    DEMONSTRATION_GEOGRAPHIES,
    DEMONSTRATION_INDUSTRIES,
    PUBLIC_GEOGRAPHIES,
    PUBLIC_INDUSTRIES,
    assessment_implications,
    load_market,
    market_framework,
)

_SURFACE_NOTE = (
    '<div class="banner">Local prototype. Not production security. '
    "This screen does not grant investor-ready status.</div>"
)

NAV = (
    ("/", "Dashboard"),
    ("/explore", "Explore"),
    ("/analyze", "Analyze"),
    ("/validate", "Validate (demonstration)"),
    ("/partner", "Partner (demonstration)"),
    ("/assessments", "My Assessments"),
    ("/market", "Market Intelligence (demonstration)"),
    ("/reports", "Reports"),
    ("/settings", "Settings"),
)


def layout(title: str, body: str, *, printable: bool = False) -> str:
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
details {{ margin: 0.8rem 0; }}
summary {{ cursor: pointer; font-family: "Segoe UI", sans-serif; }}
.bar-track {{ background: var(--stone); height: 0.7rem; margin: 0.25rem 0 0.7rem; }}
.bar {{ background: var(--bronze); height: 0.7rem; }}
@media print {{
  header, nav, .no-print {{ display: none !important; }}
  body, main {{ background: white; color: black; max-width: none; }}
  .limitations, .card, h1, h2, ul, table, p, .banner {{ visibility: visible; }}
  a {{ color: black; text-decoration: none; }}
}}
body.print-view {{ background: white; }}
body.print-view header {{ display: none; }}
</style>
</head>
<body{" class=\"print-view\"" if printable else ""}>
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
    items = "".join(_history_card(item) for item in records)
    if not items:
        items = "<p>No assessments are saved.</p>"
    body = f"""
<h1>Customer dashboard</h1>
{_SURFACE_NOTE}
<p class="muted">Local test profile. This prototype has no accounts and no production security.</p>
<div class="card">
<p>Working now: Explore intake, Analyze through the 0.1 engine, reports, and the audit.</p>
<p>Demonstration only: Market Intelligence, Validate review requests, and the Partner dashboard. Partner monitoring is not running.</p>
</div>
<p><a class="button" href="/assessments/new">Start a new assessment</a>
<a class="button" href="/assessments/export">Export all drafts</a></p>
{_draft_empty_state(records)}
<div class="card">
<p><strong>Next recommended step:</strong> {escape(_next_step(records))}</p>
<p class="muted">This indicator does not change a flag, a recommendation, or investor readiness.</p>
</div>
<h2>Assessment history</h2>
<p class="muted">Only the RUGD Intelligence assessment is the official baseline. Bunny Hive and Small Town Pub are empty named-pilot drafts until someone enters evidence. A draft is not a completed assessment, and it is not approved or investor-ready.</p>
{items}
"""
    return layout("Dashboard", body)


def _history_card(item: dict[str, Any]) -> str:
    from app.analysis import build_view_summary

    result = item.get("result") or {}
    if item.get("read_only"):
        kind = "Official baseline"
        progress = "Progress: official baseline stored. This list does not treat it as approved or investor-ready."
    elif item.get("hypothetical"):
        kind = HYPOTHETICAL_DEMO_LABEL
        progress = _draft_progress(item, result)
    elif item.get("id") == RESTAURANT_VERIFIED_ID:
        kind = "Verified-demand demonstration — not a real assessment"
        progress = _draft_progress(item, result) + " Not the official baseline and not investor-ready."
    elif is_named_pilot(item):
        kind = (
            "Empty named-pilot draft"
            if named_pilot_is_empty(item)
            else "Named-pilot draft. Not a completed assessment."
        )
        progress = _draft_progress(item, result) + " Not a completed assessment and not the official baseline."
    else:
        kind = "Draft"
        progress = _draft_progress(item, result)
    if result.get("engine_ran"):
        summary = build_view_summary(result)
        recommendation = summary.get("recommendation")
        demand = summary.get("insufficient_demand_evidence")
        readiness = summary.get("investor_readiness")
        review = summary.get("human_review_status")
    else:
        recommendation = "not run"
        demand = "not run"
        readiness = "not run"
        review = "pending"
    assessment_id = escape(item["id"])
    return f"""
<div class="card">
<p><strong>{escape(item['business_name'])}</strong> · {escape(kind)} · {escape(item['tier'])}</p>
<p class="muted">{escape(item['pilot_label'])}</p>
<p>{escape(progress)}</p>
<p><strong>Recommendation:</strong> {escape(str(recommendation))}</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> {escape(str(demand))}</p>
<p><strong>Investor readiness:</strong> {escape(str(readiness))}</p>
<p><strong>Human review status:</strong> {escape(str(review))}</p>
<p><a class="button" href="/assessments/{assessment_id}">Continue</a>
<a class="button" href="/assessments/{assessment_id}/results">View results</a>
<a class="button" href="/assessments/{assessment_id}/export">Export draft as JSON</a></p>
</div>
"""


def _next_step(records: list[dict[str, Any]]) -> str:
    drafts = [item for item in records if not item.get("read_only")]
    if not drafts:
        return "Start a new assessment. The official baseline is not a customer draft."
    for item in drafts:
        flags = (item.get("result") or {}).get("blocking_flags") or []
        if "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
            return _next_step_for(item)
    for item in drafts:
        if not (item.get("result") or {}).get("engine_ran"):
            return _next_step_for(item)
    for item in drafts:
        flags = (item.get("result") or {}).get("blocking_flags") or []
        if flags:
            return _next_step_for(item)
    return _next_step_for(drafts[0])


def _next_step_for(record: dict[str, Any]) -> str:
    """Guidance for one open draft. Reading the record does not change it."""
    name = record.get("business_name") or "this draft"
    if record.get("read_only"):
        return (
            f"{name} is the official baseline. INSUFFICIENT_DEMAND_EVIDENCE is present. "
            "This note does not clear the flag."
        )
    result = record.get("result") or {}
    flags = result.get("blocking_flags") or []
    if "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
        return (
            f"Continue {name}. INSUFFICIENT_DEMAND_EVIDENCE is present. "
            "This note does not clear the flag."
        )
    if flags:
        return (
            f"Continue {name}. Recommend-against flag {flags[0]} is still active. "
            "This note does not clear it."
        )
    profile = record.get("profile") or {}
    if (
        not record.get("hypothetical")
        and _verified_demand_ready(profile)
        and not result.get("engine_ran")
    ):
        return (
            f"Continue {name}. A verified demand record is entered. Analyze has not been run. "
            "This note does not clear a flag."
        )
    if not str(profile.get("demand_evidence") or "").strip():
        return (
            f"Continue {name}. The next missing required item is demand evidence. "
            "This note does not clear a flag."
        )
    missing = _missing_labels(profile, _STARTUP_REQUIRED)
    if missing:
        return (
            f"Continue {name}. The next missing required item is {missing[0]}. "
            "This note does not change the recommendation."
        )
    monthly = _missing_labels(profile, _MONTHLY_REQUIRED)
    if monthly:
        return (
            f"Continue {name}. The next missing required item is {monthly[0]}. "
            "This note does not change the recommendation."
        )
    if not result.get("engine_ran"):
        return f"Continue {name}. Analyze has not been run. This note does not change the recommendation."
    return f"Review {name}. This note does not change a flag or a recommendation."


def _draft_empty_state(records: list[dict[str, Any]]) -> str:
    drafts = [item for item in records if not item.get("read_only")]
    if drafts:
        return ""
    if not records:
        return """
<div class="card">
<h2>No drafts yet</h2>
<p>No assessments are saved. Start a new assessment when you are ready. Blank fields stay blank until you enter them. Nothing is copied from the official baseline.</p>
</div>
"""
    return """
<div class="card">
<h2>No drafts yet</h2>
<p>No customer drafts are saved. The official baseline is listed separately and is not a customer draft. Starting a draft does not copy baseline figures into blank fields.</p>
</div>
"""


def _verified_demand_ready(profile: dict[str, Any]) -> bool:
    source = str(profile.get("verified_record_source") or "").strip()
    rationale = str(profile.get("verified_demand_rationale") or "").strip()
    claim = str(profile.get("verified_demand_evidence") or "").strip().lower()
    return source == "verified" and bool(rationale) and claim == "true"


def _draft_progress(item: dict[str, Any], result: dict[str, Any]) -> str:
    filled = _filled_count(item.get("profile") or {}, _STARTUP_REQUIRED)
    total = len(_STARTUP_REQUIRED)
    if result.get("engine_ran"):
        state = "engine result saved"
    else:
        state = "saved draft, engine result not run"
    return (
        f"Progress: {state}. Required startup fields filled: {filled} of {total}. "
        "Not an approved or investor-ready result."
    )


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
        banner += (
            '<div class="banner">Hypothetical demonstration — not a real assessment. '
            "These figures are not verified market research.</div>"
        )
    if record.get("id") == RESTAURANT_ID:
        banner += (
            f'<p><a href="/assessments/{RESTAURANT_VERIFIED_ID}">'
            "Open the verified-demand demonstration</a></p>"
        )
    elif record.get("id") == RESTAURANT_VERIFIED_ID:
        banner += (
            '<div class="banner">Verified-demand demonstration — not a real assessment. '
            "The verified record can clear INSUFFICIENT_DEMAND_EVIDENCE under the documented rule. "
            "It does not approve the assessment or make it investor-ready.</div>"
            f'<p><a href="/assessments/{RESTAURANT_ID}">Open the unanswered hypothetical draft</a></p>'
        )
    if is_named_pilot(record):
        empty = " Empty named-pilot draft." if named_pilot_is_empty(record) else ""
        banner += (
            "<div class=\"banner\">Named-pilot draft. Not a completed assessment. "
            "Only the RUGD Intelligence assessment is the official baseline."
            f"{empty}</div>"
        )
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
<div class="card">
<p><strong>Guidance. Not a decision.</strong></p>
<p><strong>Next recommended step:</strong> {escape(_next_step_for(record))}</p>
<p class="muted">This note does not clear a flag, change the recommendation, or mark the assessment investor-ready.</p>
</div>
{_intake_status(record)}
<p class="muted">Tier {escape(record['tier'])}. Changing tier does not change a recommendation. Entered answers stay user-supplied assumptions.</p>
{action}
<p><a href="/assessments/{escape(record['id'])}/analyst">Open the Demonstration Analyst</a>
<a href="/assessments/{escape(record['id'])}/export">Export draft as JSON</a></p>
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
    startup_missing = _missing_labels(profile, _STARTUP_REQUIRED)
    monthly_missing = _missing_labels(profile, _MONTHLY_REQUIRED)
    if startup_missing:
        startup_note = (
            "This draft is incomplete. Missing required startup fields: "
            + ", ".join(startup_missing)
            + ". The startup cost build is not calculated until these values are saved. "
            "Blank fields stay blank. Nothing has been filled in for you."
        )
    else:
        startup_note = (
            "Required startup fields are filled. They remain user-supplied assumptions, not verified data."
        )
    if monthly_missing:
        monthly_note = (
            "This draft is incomplete. Missing monthly fields: "
            + ", ".join(monthly_missing)
            + ". Results will say Insufficient verified information to calculate. "
            "No monthly figure is invented."
        )
    else:
        monthly_note = (
            "Monthly fields are filled. Leave “These monthly figures are measured” unchecked "
            "when they are unmeasured placeholders."
        )
    return f"""
<div class="card">
<p><strong>User-supplied assumptions.</strong> Answers on this form are not verified data.</p>
<p><strong>Verified data.</strong> Only the separate verified demand record is applied, and only when its source is verified and a rationale is present.</p>
<p><strong>Unmeasured placeholders.</strong> A blank required field stays blank. A number already shown in a worksheet field is the stored assumption, not a silent substitution.</p>
<p>{escape(startup_note)}</p>
<p>{escape(monthly_note)}</p>
</div>
<details open>
<summary>Concept</summary>
{text("business_name", "Business name")}
{text("concept", "Business concept", area=True)}
{text("industry", "Industry")}
{text("market", "Geographic market")}
{text("stage", "Development stage")}
{text("products", "Products and services", area=True)}
{text("customers", "Target customers", area=True)}
{text("competition", "Competition", area=True)}
</details>
<details open>
<summary>Demand evidence</summary>
{choice("demand_evidence", "Is there demand evidence? A yes here is still only a user-supplied assumption.")}
{_verified_demand_fields(profile, locked)}
{choice("operator_capacity_adequate", "Is operator capacity adequate?")}
{choice("unresolved_regulatory_or_liability", "Is there an unresolved regulatory or liability issue?")}
{choice("extraction_without_reinvestment", "Do stewardship indicators show extraction without reinvestment?")}
</details>
<details open>
<summary>Startup capital</summary>
<p class="muted">The primary revenue path remains seats × occupancy × average ticket. Required fields are construction cost, seats, average ticket, weekday occupancy, weekend occupancy, operating days, and contribution margin.</p>
{text("construction_cost", "Construction cost")}
{text("seats", "Seats")}
{text("average_ticket", "Average ticket")}
{text("weekday_occupancy", "Weekday occupancy")}
{text("weekend_occupancy", "Weekend occupancy")}
{text("operating_days", "Operating days")}
{text("contribution_margin", "Contribution margin")}
</details>
<details>
<summary>Optional startup worksheet lines</summary>
<p class="muted">Values already in these fields are stored with the draft. They are user-supplied worksheet assumptions, not verified data.</p>
{text("equipment", "Equipment")}
{text("soft_costs", "Soft costs")}
{text("preopening_working_capital", "Pre-opening working capital")}
{text("contingency_pct", "Contingency percentage (0.10 = 10%)")}
{text("debt_share", "Debt share")}
{text("annual_interest_rate", "Annual interest rate")}
{text("amortization_years", "Amortization years")}
{text("annual_fixed_costs", "Annual fixed costs")}
{text("downside_multiplier", "Downside occupancy multiplier")}
</details>
<details>
<summary>Monthly engine</summary>
<p class="muted">All four monthly fields are required before the monthly engine calculates. Unchecked measured status keeps the figures unmeasured.</p>
{text("initial_capital", "Initial capital")}
{text("monthly_fixed_costs", "Monthly fixed costs")}
{text("gross_margin_pct", "Gross margin")}
{text("projected_monthly_revenue_base", "Projected monthly base revenue")}
<label><input type="checkbox" name="inputs_are_measured" value="true" {measured} {locked}> These monthly figures are measured</label>
</details>
{text("evidence_notes", "Evidence notes", area=True)}
"""


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
        body = _results_not_run(record, result)
        return layout("Analyze", body)
    flags = "".join(f"<li class=\"flag\">{escape(flag)}</li>" for flag in result.get("blocking_flags") or []) or "<li>None</li>"
    gaps = "".join(f"<li>{escape(flag)}</li>" for flag in result.get("gap_flags") or []) or "<li>None</li>"
    missing = "".join(f"<li>{escape(item)}</li>" for item in result.get("missing") or []) or "<li>None listed</li>"
    financial = _financial_table(result.get("financial"))
    projection = _projection_view(result)
    summary_approved = (result.get("human_review_approved") is True and result.get("human_review_status") == "approved")
    if summary_approved:
        standing = (
            "Reviewer approval is recorded. Approval does not clear flags and does not by itself "
            "mark this result investor-ready."
        )
    else:
        standing = "Draft recommendation. Human review is pending. This is not a final or investor-ready result."
    links = _output_links(record)
    body = f"""
<h1>Results for {escape(record['business_name'])}</h1>
{_pilot_banner(record)}
{_SURFACE_NOTE}
<div class="banner">{escape(standing)}</div>
{links}
<div class="card">
{_view_summary_block(result)}
<p class="muted">Engine {escape(str(result.get('model_version')))}. Service tier on this file: {escape(record['tier'])}. Authoritative financial numbers below come only from the 0.1 engine.</p>
</div>
{_analyst_panel(record, result)}
{_LIMITATIONS}
<h2>Demand evidence</h2>
{_demand_status(result.get("demand") or {})}
<h2>Recommend-against flags</h2><ul>{flags}</ul>
<h2>Evidence gaps</h2><ul>{gaps}</ul>
<h2>Missing information</h2><ul>{missing}</ul>
<h2>Monthly base and downside</h2>{financial}
<h2>Sources and uses, scenarios, and DSCR</h2>
{projection}
{links}
"""
    return layout("Results", body)


_LIMITATIONS = """
<section class="limitations">
<h2>Limitations</h2>
<p>This is a prototype. Demonstration data is not real market research. Reviewer authentication remains prototype-grade.</p>
</section>
"""


def _output_links(record: dict[str, Any]) -> str:
    assessment_id = escape(record["id"])
    return f"""
<p class="no-print"><a class="button" href="/assessments/{assessment_id}/report">Open report</a>
<a class="button" href="/assessments/{assessment_id}/report/download">Download Markdown report</a>
<a class="button" href="/assessments/{assessment_id}/audit/html">HTML audit view</a>
<a class="button" href="/assessments/{assessment_id}/audit/print">Print-friendly audit</a>
<a class="button" href="/assessments/{assessment_id}/audit">Inspect audit</a>
<a class="button" href="/assessments/{assessment_id}/audit/download">Download JSON audit</a></p>
"""


def _results_not_run(record: dict[str, Any], result: dict[str, Any]) -> str:
    profile = record.get("profile") or {}
    startup_missing = _missing_labels(profile, _STARTUP_REQUIRED)
    monthly_missing = _missing_labels(profile, _MONTHLY_REQUIRED)
    message = str(result.get("message") or "Analyze has not been run.")
    details = ""
    if startup_missing:
        details += (
            "<p>Missing required startup fields: "
            + escape(", ".join(startup_missing))
            + ". Blank fields stay blank.</p>"
        )
    if monthly_missing:
        details += (
            "<p>Missing monthly fields: "
            + escape(", ".join(monthly_missing))
            + ". Insufficient verified information to calculate until those values are saved. "
            "No monthly figure is invented.</p>"
        )
    baseline = ""
    if record.get("read_only"):
        baseline = """
<div class="card">
<p>Stored official baseline status. This page did not run Analyze and did not fill missing fields.</p>
<p><strong>Recommendation:</strong> do-not-proceed</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> present</p>
<p><strong>Investor readiness:</strong> internal</p>
<p><strong>Human review status:</strong> pending</p>
<p><strong>Demand evidence provenance:</strong> placeholder until Analyze records verified, user, or placeholder.</p>
</div>
"""
    return f"""
<h1>Analyze has not been run</h1>
{_pilot_banner(record)}
{_SURFACE_NOTE}
<div class="banner">{escape(message)} This page did not run the engine and did not fill any blank fields.</div>
{details}
{baseline}
<p><a class="button" href="/assessments/{escape(record['id'])}">Return to the draft</a>
<a class="button" href="/assessments/{escape(record['id'])}/export">Export draft as JSON</a></p>
"""


def _pilot_banner(record: dict[str, Any]) -> str:
    label = str(record.get("pilot_label") or "").strip()
    if not label:
        return ""
    return f'<div class="banner">{escape(label)}</div>'


def _intake_status(record: dict[str, Any]) -> str:
    result = record.get("result") or {}
    if result.get("engine_ran"):
        return f"<div class=\"card\">{_view_summary_block(result)}</div>"
    return """
<div class="card">
<p><strong>Recommendation:</strong> not run</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> not run</p>
<p><strong>Investor readiness:</strong> not run</p>
<p><strong>Human review status:</strong> pending</p>
<p><strong>human_review_approved:</strong> false</p>
<p><strong>Demand evidence provenance:</strong> placeholder until Analyze records verified, user, or placeholder.</p>
</div>
"""


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


_STARTUP_REQUIRED = (
    ("construction_cost", "Construction cost"),
    ("seats", "Seats"),
    ("average_ticket", "Average ticket"),
    ("weekday_occupancy", "Weekday occupancy"),
    ("weekend_occupancy", "Weekend occupancy"),
    ("operating_days", "Operating days"),
    ("contribution_margin", "Contribution margin"),
)
_MONTHLY_REQUIRED = (
    ("initial_capital", "Initial capital"),
    ("monthly_fixed_costs", "Monthly fixed costs"),
    ("gross_margin_pct", "Gross margin"),
    ("projected_monthly_revenue_base", "Projected monthly base revenue"),
)


def _missing_labels(profile: dict[str, Any], fields: tuple[tuple[str, str], ...]) -> list[str]:
    return [label for key, label in fields if not str(profile.get(key) or "").strip()]


def _filled_count(profile: dict[str, Any], fields: tuple[tuple[str, str], ...]) -> int:
    return len(fields) - len(_missing_labels(profile, fields))


def _projection_view(result: dict[str, Any]) -> str:
    projection = result.get("projection") or {}
    engine_text = f"<details><summary>Engine text</summary><pre>{escape(result.get('projection_text') or '')}</pre></details>"
    if not projection.get("calculated"):
        note = str(projection.get("note") or result.get("projection_text") or "")
        return (
            "<p>No sources-and-uses table is shown. The engine did not calculate the startup cost build.</p>"
            "<p>Missing startup inputs were not filled.</p>"
            f"<p>{escape(note)}</p>{engine_text}"
        )
    uses = (projection.get("sources_and_uses") or {}).get("uses") or {}
    sources = (projection.get("sources_and_uses") or {}).get("sources") or {}
    views = projection.get("views") or {}
    base = views.get("base") or {}
    downside = views.get("downside") or {}
    break_even = views.get("break_even") or {}
    use_rows = "".join(
        f"<tr><td>{escape(key)}</td><td>{escape(_amount_text(uses.get(key)))}</td></tr>"
        for key in (
            "construction_cost",
            "equipment",
            "soft_costs",
            "preopening_working_capital",
            "contingency",
            "total_project_cost",
        )
    )
    source_rows = "".join(
        f"<tr><td>{escape(key)}</td><td>{escape(_amount_text(sources.get(key)))}</td></tr>"
        for key in ("debt", "equity", "total_sources", "annual_debt_service")
    )
    scenario = f"""
<table>
<tr><th>Scenario</th><th>Revenue</th><th>Cash flow before debt service</th><th>DSCR</th></tr>
<tr><td>Base</td><td>{escape(_plain_number(base.get('revenue')))}</td><td>{escape(_plain_number(base.get('cash_flow_before_debt_service')))}</td><td>{escape(_dscr_label(base.get('dscr')))}</td></tr>
<tr><td>Downside</td><td>{escape(_plain_number(downside.get('revenue')))}</td><td>{escape(_plain_number(downside.get('cash_flow_before_debt_service')))}</td><td>{escape(_dscr_label(downside.get('dscr')))}</td></tr>
</table>
<p>Break-even revenue from the engine: {escape(_plain_number(break_even.get('revenue')))}</p>
{_revenue_bars(base.get('revenue'), downside.get('revenue'))}
"""
    return f"""
<h3>Sources and uses</h3>
<table><tr><th>Use</th><th>Amount</th></tr>{use_rows}</table>
<table><tr><th>Source</th><th>Amount</th></tr>{source_rows}</table>
<h3>Base and downside</h3>
{scenario}
{engine_text}
"""


def _amount_text(value: Any) -> str:
    if isinstance(value, dict):
        amount = value.get("amount")
        label = value.get("evidence_label") or ""
        if amount is None:
            return "not defined"
        return f"{amount} ({label})" if label else str(amount)
    if value is None:
        return "not defined"
    return str(value)


def _plain_number(value: Any) -> str:
    if value is None:
        return "not defined"
    return str(value)


def _dscr_label(value: Any) -> str:
    if value is None:
        return "undefined"
    return str(value)


def _revenue_bars(base: Any, downside: Any) -> str:
    if isinstance(base, bool) or isinstance(downside, bool):
        return ""
    if not isinstance(base, (int, float)) or not isinstance(downside, (int, float)):
        return ""
    span = max(abs(base), abs(downside))
    if span == 0:
        return ""
    base_width = round(abs(base) / span * 100)
    downside_width = round(abs(downside) / span * 100)
    return f"""
<p>Base revenue and downside revenue from the engine.</p>
<p>Base {escape(str(base))}</p>
<div class="bar-track"><div class="bar" style="width: {base_width}%"></div></div>
<p>Downside {escape(str(downside))}</p>
<div class="bar-track"><div class="bar" style="width: {downside_width}%"></div></div>
"""


def _financial_table(financial: dict[str, Any] | None) -> str:
    if not financial:
        return (
            "<p>Insufficient verified information to calculate.</p>"
            "<p>Monthly contribution, cash flow, and break-even were not calculated. "
            "Missing monthly inputs were not filled.</p>"
        )
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
    label = lines[0] if lines else "Demonstration Analyst"
    body = f"""
<h1>Analyst</h1>
<div class="banner">{escape(label)}</div>
<p class="muted">Optional explanation. The analyst cannot alter authoritative results, clear flags, set human_review_approved, or change investor readiness.</p>
<ul>{items}</ul>
<p><a href="/assessments/{escape(record['id'])}/results">Return to results</a></p>
"""
    return layout("Analyst", body)


def _analyst_panel(record: dict[str, Any], result: dict[str, Any]) -> str:
    analyst = get_analyst()
    note = (
        "Optional explanation. The analyst cannot alter authoritative results, "
        "clear flags, set human_review_approved, or change investor readiness."
    )
    href = f"/assessments/{escape(record['id'])}/analyst"
    if getattr(analyst, "uses_network", False):
        body = (
            f"<p>{escape(analyst.label)}</p><p>{note}</p>"
            f"<p><a href=\"{href}\">Open the optional analyst explanation</a></p>"
        )
    else:
        lines = analyst.explain(record, result)
        items = "".join(f"<li>{escape(line)}</li>" for line in lines)
        shown = lines[0] if lines else analyst.label
        body = (
            f"<p>{escape(shown)}</p><p>{note}</p><ul>{items}</ul>"
            f"<p><a href=\"{href}\">Open the analyst page</a></p>"
        )
    return f"<div class=\"card\"><h2>Analyst</h2>{body}</div>"


def market_page(
    records: list[dict[str, Any]] | None = None,
    industry: str | None = None,
    geographic_market: str | None = None,
    provider: Any | None = None,
) -> str:
    records = records or []
    if provider is None or getattr(provider, "name", None) == "synthetic":
        return _synthetic_market_page(records, industry, geographic_market)
    view = load_market(industry, geographic_market, provider)
    if view["status"] == "public":
        return _public_market_page(records, industry, geographic_market, view)
    return _fallback_market_page(records, industry, geographic_market, view)


def _synthetic_market_page(
    records: list[dict[str, Any]],
    industry: str | None,
    geographic_market: str | None,
) -> str:
    snapshot = market_framework(industry, geographic_market)
    implications = "".join(
        f"<li>{escape(line)}</li>" for line in assessment_implications(records, industry, geographic_market)
    )
    industry_options = _demo_options(DEMONSTRATION_INDUSTRIES, snapshot["industry"])
    geography_options = _demo_options(DEMONSTRATION_GEOGRAPHIES, snapshot["geographic_market"])
    body = f"""
<h1>Market Intelligence (demonstration)</h1>
{_SURFACE_NOTE}
<div class="banner">Demonstration only. This page does not load a live market feed. Not live monitoring.</div>
<form method="get" action="/market">
<label>Demonstration industry</label>
<select name="industry">{industry_options}</select>
<label>Demonstration geographic market</label>
<select name="geographic_market">{geography_options}</select>
<button type="submit">Show demonstration selection</button>
</form>
<p class="muted">The choices are labels for this demonstration. They are not a dataset and they do not describe a real market.</p>
{_market_summary(_synthetic_view(snapshot), snapshot["industry"], snapshot["geographic_market"])}
{_market_block(snapshot)}
<h2>Implications for this assessment</h2>
<ul>{implications}</ul>
<p class="muted">The same demonstration snapshot is available on Partner. Neither view loads Census, BLS, or BEA data.</p>
"""
    return layout("Market Intelligence", body)


def _public_market_page(
    records: list[dict[str, Any]],
    industry: str | None,
    geographic_market: str | None,
    view: dict[str, Any],
) -> str:
    industry_options = _demo_options(PUBLIC_INDUSTRIES, str(industry or "Not selected"))
    geography_options = _demo_options(PUBLIC_GEOGRAPHIES, str(geographic_market or "Not selected"))
    cards = _observation_cards(view["observations"])
    partial = _partial_synthetic(view)
    notes = []
    for record in records:
        if record.get("read_only"):
            continue
        profile = record.get("profile") or {}
        notes.append(
            f"{record.get('business_name')} lists industry {profile.get('industry') or 'not entered'} "
            f"and stage {profile.get('stage') or 'not entered'}. "
            "No market fact is supplied for that industry or stage."
        )
    if not notes:
        notes.append("No customer draft has an industry and stage to reference. No market fact is invented.")
    notes.append(
        "These public figures do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag."
    )
    implications = "".join(f"<li>{escape(line)}</li>" for line in notes)
    body = f"""
<h1>Market Intelligence</h1>
{_SURFACE_NOTE}
<div class="banner">{escape(view['label'])}</div>
<form method="get" action="/market">
<label>Industry</label>
<select name="industry">{industry_options}</select>
<label>Geographic coverage</label>
<select name="geographic_market">{geography_options}</select>
<button type="submit">Request public observations</button>
</form>
<p class="muted">Optional public extract. {_active_provider(view)} Live feed connected: false. Monitoring active: false. This request does not change an assessment.</p>
<p class="muted">{_YEAR_NOTE}</p>
{_market_summary(view, industry, geographic_market)}
{cards}
{partial}
<h2>Implications for this assessment</h2>
<ul>{implications}</ul>
"""
    return layout("Market Intelligence", body)


def _fallback_market_page(
    records: list[dict[str, Any]],
    industry: str | None,
    geographic_market: str | None,
    view: dict[str, Any],
) -> str:
    snapshot = view["snapshot"]
    implications = "".join(
        f"<li>{escape(line)}</li>" for line in assessment_implications(records, industry, geographic_market)
    )
    industry_options = _demo_options(PUBLIC_INDUSTRIES, str(industry or snapshot["industry"]))
    geography_options = _demo_options(PUBLIC_GEOGRAPHIES, str(geographic_market or snapshot["geographic_market"]))
    body = f"""
<h1>Market Intelligence (demonstration)</h1>
{_SURFACE_NOTE}
<div class="banner">{escape(view['label'])}</div>
<form method="get" action="/market">
<label>Industry</label>
<select name="industry">{industry_options}</select>
<label>Geographic coverage</label>
<select name="geographic_market">{geography_options}</select>
<button type="submit">Request public observations</button>
</form>
<p class="muted">{_active_provider(view)} A mapped industry and geography can request the public extract. Any other selection stays on the synthetic snapshot.</p>
<p class="muted">{_YEAR_NOTE}</p>
{_market_summary(view, industry, geographic_market)}
{_market_block(snapshot)}
<h2>Implications for this assessment</h2>
<ul>{implications}</ul>
<p class="muted">These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag.</p>
"""
    return layout("Market Intelligence", body)


_YEAR_NOTE = (
    "The year is controlled by an environment variable. "
    "MARKET_YEAR selects the QCEW file. ACS_YEAR selects the ACS vintage. "
    "Each defaults to 2024 when it is not set. This is prototype behavior."
)


def _synthetic_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "synthetic",
        "provider_name": "synthetic",
        "year": "",
        "observations": [],
        "snapshot": snapshot,
        "partial_notes": [],
    }


def _market_summary(view: dict[str, Any], industry: str | None, geographic_market: str | None) -> str:
    rows = []
    for item in view.get("observations") or []:
        rows.append(
            "<li>"
            f"<strong>{escape(str(item.get('measure') or ''))}:</strong> {escape(str(item.get('value') or ''))}. "
            f"Source: {escape(str(item.get('source') or ''))}. "
            f"Geographic coverage: {escape(str(item.get('geographic_coverage') or ''))}. "
            f"Measurement period: {escape(str(item.get('measurement_period') or ''))}."
            "</li>"
        )
    if view.get("status") != "public" or view.get("partial_notes"):
        for example in (view.get("snapshot") or {}).get("synthetic_examples") or []:
            rows.append(f"<li>{escape(str(example))}</li>")
    if not rows:
        rows.append("<li>No observations are loaded.</li>")
    query = urlencode(
        {
            "industry": str(industry or ""),
            "geographic_market": str(geographic_market or ""),
        }
    )
    return (
        "<h2>Combined summary</h2>"
        f"<p>{_active_provider(view)}</p>"
        f"<ul>{''.join(rows)}</ul>"
        "<p>These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag.</p>"
        f"<p><a href=\"/market/export?{query}\">Download market observations (JSON)</a></p>"
    )


def _active_provider(view: dict[str, Any]) -> str:
    if str(view.get("provider_name") or "") == "synthetic":
        return "Active provider: Demonstration snapshot. No public provider is active."
    active = view.get("active_providers") or []
    if active:
        return "Active providers: " + "; ".join(escape(str(item)) for item in active) + "."
    name = str(view.get("provider_name") or "")
    year = str(view.get("year") or "")
    labels = {
        "bls-qcew": "BLS Quarterly Census of Employment and Wages",
        "census-acs": "U.S. Census Bureau, American Community Survey 5-year estimates",
    }
    label = labels.get(name, name or "public market provider")
    return f"Active provider: {escape(label)}. Year: {escape(year or 'not set')}."


def _observation_cards(observations: list[dict[str, str]]) -> str:
    groups: list[tuple[str, list[dict[str, str]]]] = []
    for item in observations:
        if not groups or groups[-1][0] != item["source"]:
            groups.append((item["source"], []))
        groups[-1][1].append(item)
    cards = []
    for _source, rows in groups:
        first = rows[0]
        cards.append(
            "<div class=\"card\">"
            f"<p><strong>Source:</strong> {escape(first['source'])}</p>"
            f"<p><strong>Geographic coverage:</strong> {escape(first['geographic_coverage'])}</p>"
            f"<p><strong>Classification:</strong> {escape(first['industry_classification'])}</p>"
            f"<p><strong>Measurement period:</strong> {escape(first['measurement_period'])}</p>"
            f"<p><strong>Retrieval date:</strong> {escape(first['retrieval_date'])}</p>"
            f"<p><strong>Limitations:</strong> {escape(first['limitations'])}</p>"
            f"<ul>{_measure_items(rows)}</ul>"
            "</div>"
        )
    return "".join(cards)


def _partial_synthetic(view: dict[str, Any]) -> str:
    notes = view.get("partial_notes") or []
    if not notes:
        return ""
    snapshot = view["snapshot"]
    examples = "".join(f"<li>{escape(item)}</li>" for item in snapshot["synthetic_examples"])
    reasons = "".join(f"<li>{escape(str(note))}</li>" for note in notes)
    return (
        "<div class=\"banner\">Fallback for the unavailable metrics: synthetic snapshot. Synthetic example only.</div>"
        f"<ul>{reasons}</ul>"
        "<h2>Synthetic examples</h2>"
        f"<ul>{examples}</ul>"
        "<p class=\"muted\">These synthetic examples do not clear INSUFFICIENT_DEMAND_EVIDENCE "
        "or any other recommend-against flag.</p>"
    )


def _measure_items(observations: list[dict[str, str]]) -> str:
    items = []
    for item in observations:
        items.append(
            "<li>"
            f"<strong>{escape(item['measure'])}:</strong> {escape(item['value'])}. "
            f"Source: {escape(item['source'])}. "
            f"Geographic coverage: {escape(item['geographic_coverage'])}. "
            f"Classification: {escape(item['industry_classification'])}. "
            f"Measurement period: {escape(item['measurement_period'])}. "
            f"Retrieval date: {escape(item['retrieval_date'])}."
            "</li>"
        )
    return "".join(items)


def _demo_options(choices: tuple[str, ...], current: str) -> str:
    return "".join(
        f'<option value="{escape(choice)}"{" selected" if choice == current else ""}>{escape(choice)}</option>'
        for choice in choices
    )


def audit_html_page(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    events: list[dict[str, Any]] | None = None,
    *,
    printable: bool = False,
) -> str:
    """Read-only audit view. This page has no control that can change the assessment."""
    from app.analysis import build_view_summary

    result = result or {}
    events = events or []
    if not result.get("engine_ran"):
        body = f"""
<h1>Audit view</h1>
{_pilot_banner(record)}
{_SURFACE_NOTE}
<div class="banner">Audit view. Read only. Draft. This page cannot change flags, approval, readiness, or the recommendation. Not an investor-ready result.</div>
<p>{escape(result.get('message') or 'Analyze did not run.')}</p>
{_LIMITATIONS}
<h2>Reviewer events</h2>
<p>No reviewer events are recorded.</p>
{_output_links(record)}
"""
        return layout("Audit view", body, printable=printable)
    summary = build_view_summary(result)
    if summary.get("human_review_approved"):
        standing = (
            "Reviewer approval is recorded. Investor readiness stays on the existing gate. "
            "Approval does not clear recommend-against flags and does not by itself mark this assessment investor-ready."
        )
    else:
        standing = "Draft. Human review is pending. This is not an approved or investor-ready result."
    blocking = "".join(f"<li class=\"flag\">{escape(flag)}</li>" for flag in result.get("blocking_flags") or []) or "<li>None</li>"
    gaps = "".join(f"<li>{escape(flag)}</li>" for flag in result.get("gap_flags") or []) or "<li>None</li>"
    provenance = "".join(
        f"<li>{escape(str(row.get('field')))}: {escape(str(row.get('provenance')))}</li>"
        for row in summary.get("demand_provenance") or []
    ) or "<li>placeholder</li>"
    if events:
        rows = "".join(
            "<tr>"
            f"<td>{escape(str(item.get('action')))}</td>"
            f"<td>{escape(str(item.get('recorded_at') or ''))}</td>"
            f"<td>{escape(str(item.get('session_id') or ''))}</td>"
            f"<td>{escape(str(item.get('reviewer_identity') or ''))}</td>"
            "</tr>"
            for item in events
        )
        event_table = (
            "<table><tr><th>Action</th><th>Timestamp</th><th>Session hash</th><th>Reviewer</th></tr>"
            f"{rows}</table>"
        )
    else:
        event_table = "<p>No reviewer events are recorded.</p>"
    print_note = (
        '<p class="no-print">Print-friendly audit. Use the browser print dialog to save a PDF. This view does not change the assessment.</p>'
        if printable
        else ""
    )
    body = f"""
<h1>Audit view for {escape(record['business_name'])}</h1>
{print_note}
{_pilot_banner(record)}
{_SURFACE_NOTE}
<div class="banner">Audit view. Read only. {escape(standing)} This page cannot change flags, approval, readiness, or the recommendation.</div>
<div class="card">
<p><strong>Recommendation:</strong> {escape(str(summary.get('recommendation')))}</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> {escape(str(summary.get('insufficient_demand_evidence')))}</p>
<p><strong>Investor readiness:</strong> {escape(str(summary.get('investor_readiness')))}</p>
<p><strong>Human review status:</strong> {escape(str(summary.get('human_review_status')))}</p>
<p><strong>human_review_approved:</strong> {"true" if summary.get("human_review_approved") else "false"}</p>
</div>
<h2>Recommend-against flags</h2><ul>{blocking}</ul>
<h2>Evidence gaps</h2><ul>{gaps}</ul>
<h2>Demand evidence provenance</h2>
<ul>{provenance}</ul>
{_LIMITATIONS}
<h2>Reviewer events</h2>
<p class="muted">Reviewer authentication remains prototype-grade. Not a customer feature. Not production authentication. Session values below are short hashes, not raw tokens.</p>
{event_table}
{_output_links(record)}
"""
    return layout("Audit view", body, printable=printable)


def validate_page(record: dict[str, Any] | None) -> str:
    if record is None:
        body = (
            "<h1>Validate (demonstration)</h1>"
            f"{_SURFACE_NOTE}"
            "<div class=\"banner\">Demonstration only. Customers can request review. "
            "This screen cannot set human_review_approved. Not live monitoring.</div>"
            "<p>Open an assessment from My Assessments to request a review.</p>"
        )
        return layout("Validate", body)
    requested = "A review has been requested." if record["review_requested"] else "No review has been requested."
    body = f"""
<h1>Validate (demonstration)</h1>
{_SURFACE_NOTE}
<div class="banner">Demonstration only. Customers can request review. This screen cannot set human_review_approved. Not live monitoring.</div>
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
    activity: dict[str, Any] | None = None,
) -> str:
    result = result or {}
    flags = ", ".join(result.get("blocking_flags") or []) or "none loaded"
    readiness = result.get("readiness_status") or "not loaded"
    approved = "true" if record.get("human_review_approved") else "false"
    auth_state, signed_in, expired, status_word = _session_status(session)
    next_path = f"/reviewer/assessments/{record['id']}"
    if record.get("read_only"):
        control = "<p>The official baseline cannot be approved from this prototype.</p>"
        if signed_in or expired:
            control += _reviewer_sign_out_form(next_path)
    elif signed_in:
        control = f"""
<form method="post" action="/reviewer/assessments/{escape(record['id'])}/approve">
<button type="submit">Record reviewer approval</button>
</form>
{_reviewer_sign_out_form(next_path)}
"""
    else:
        control = _reviewer_sign_in_form(next_path)
        if expired:
            control += _reviewer_sign_out_form(next_path)
    body = f"""
<h1>Reviewer control</h1>
<div class="banner">Reviewer control. Not a customer feature. Prototype-grade local session. This is not production authentication.</div>
<p><strong>Authentication state:</strong> {escape(auth_state)}</p>
{_session_activity_block(activity, status_word)}
<p>Assessment: {escape(record['business_name'])} ({escape(record['id'])})</p>
<p><strong>Recommendation:</strong> {escape(str(result.get('recommendation') or 'not loaded'))}</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE and other blocking flags:</strong> {escape(flags)}</p>
<p><strong>Investor readiness:</strong> {escape(str(readiness))}</p>
<p><strong>human_review_approved:</strong> {approved}</p>
<p class="muted">Recording approval does not clear demand evidence, change the recommendation, or grant investor-ready.</p>
<p><a href="/assessments/{escape(record['id'])}/audit/html">HTML audit view</a></p>
{control}
"""
    return layout("Reviewer control", body)


def reviewer_home(
    session: dict[str, Any] | None,
    activity: dict[str, Any] | None = None,
) -> str:
    state, signed_in, expired, status_word = _session_status(session)
    form = "" if signed_in else _reviewer_sign_in_form("/reviewer")
    if signed_in or expired:
        form += _reviewer_sign_out_form("/reviewer")
    return layout(
        "Reviewer",
        f"""
<h1>Reviewer</h1>
<div class="banner">Prototype-grade local session. Not a customer feature. Not production authentication.</div>
<p><strong>Authentication state:</strong> {escape(state)}</p>
{_session_activity_block(activity, status_word)}
{form}
<p class="muted">Open a saved assessment reviewer screen after signing in.</p>
""",
    )


def _session_activity_block(activity: dict[str, Any] | None, status_word: str) -> str:
    activity = activity or {}
    last_sign_in = activity.get("last_sign_in") or "none recorded"
    last_sign_out = activity.get("last_sign_out") or "none recorded"
    return f"""
<p class="muted">Prototype session activity. Not a customer feature. Not production authentication.</p>
<p><strong>Last sign-in:</strong> {escape(str(last_sign_in))}</p>
<p><strong>Last sign-out:</strong> {escape(str(last_sign_out))}</p>
<p><strong>Current session status:</strong> {escape(status_word)}</p>
"""


def _session_status(session: dict[str, Any] | None) -> tuple[str, bool, bool, str]:
    session = session or {}
    state_name = str(session.get("state") or "")
    signed_in = bool(session.get("active")) and state_name != "expired"
    expired = state_name == "expired"
    if signed_in:
        label = (
            f"signed in as {session.get('reviewer_identity')} "
            f"({session.get('authentication_method')}). "
            f"Remaining lifetime: {_format_remaining(session.get('remaining_seconds'))}."
        )
        return label, True, False, "signed in"
    if expired:
        return "expired", False, True, "expired"
    return "signed out", False, False, "signed out"


def _format_remaining(seconds: Any) -> str:
    try:
        remaining = max(0, int(seconds))
    except (TypeError, ValueError):
        return "unknown"
    hours, leftover = divmod(remaining, 3600)
    minutes = leftover // 60
    if hours and minutes:
        return f"{hours} hours {minutes} minutes"
    if hours:
        return f"{hours} hours"
    return f"{minutes} minutes"


def _reviewer_sign_out_form(next_path: str) -> str:
    return f"""
<form method="post" action="/reviewer/session/sign-out">
<input type="hidden" name="next" value="{escape(next_path)}">
<button type="submit">Sign out</button>
</form>
<p class="muted">Prototype sign-out. Not a customer feature. Not production authentication.</p>
"""


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
<h1>Partner (demonstration)</h1>
{_SURFACE_NOTE}
<div class="banner">Demonstration dashboard. Recurring monitoring is not active. Recurring monitoring has not been implemented. Not live monitoring.</div>
<div class="card">
<p>Partner is the planned tier for an established business that needs ongoing intelligence. A startup feasibility assessment is not required to enter this tier later.</p>
<p>No scheduled market, financial, or risk monitor is running. Monitoring active: false.</p>
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
        f"<a href=\"/assessments/{escape(item['id'])}/audit/html\">HTML audit view</a> · "
        f"<a href=\"/assessments/{escape(item['id'])}/audit\">audit</a></li>"
        for item in records
    )
    return layout(
        "Reports",
        f"<h1>Reports</h1>{_SURFACE_NOTE}<ul>{items}</ul>"
        "<p class=\"muted\">Reports are drafts. A report is not investor-ready unless the existing gate "
        "and an authorized review say otherwise. This prototype does not write the official 0.1 output files. "
        "Authoritative financial numbers in a report come only from the 0.1 engine.</p>",
    )


def settings_page() -> str:
    body = """
<h1>Settings</h1>
<p>This copy runs on 127.0.0.1 for a local pilot. It has no customer accounts, no password store, and no payment processing.</p>
<p>LongArc / DVT is not connected. The Webflow site is not connected.</p>
<p>Only the RUGD Intelligence assessment is the official baseline. Bunny Hive and Small Town Pub stay empty named-pilot drafts until evidence is entered. They are not completed assessments.</p>
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
<p class="muted">Only the RUGD Intelligence assessment is the official baseline. Bunny Hive and Small Town Pub do not have completed assessments. These buttons create empty drafts. Their names are not used by the scoring engine.</p>
<form method="post" action="/assessments"><input type="hidden" name="business_name" value="Bunny Hive"><input type="hidden" name="purpose" value="startup_feasibility"><input type="hidden" name="tier" value="explore"><button type="submit">Start Bunny Hive draft</button></form>
<form method="post" action="/assessments"><input type="hidden" name="business_name" value="Small Town Pub"><input type="hidden" name="purpose" value="startup_feasibility"><input type="hidden" name="tier" value="explore"><button type="submit">Start Small Town Pub draft</button></form>
"""
    return layout("New assessment", body)


def explore_page(records: list[dict[str, Any]]) -> str:
    return layout(
        "Explore",
        """
<h1>Explore</h1>
"""
        + _SURFACE_NOTE
        + """
<div class="banner">Explore is an intake and gap check. It is not a completed feasibility study. It does not clear a flag.</div>
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
    return layout(
        "Analyze",
        f"<h1>Analyze</h1>{_SURFACE_NOTE}"
        "<p>Results come from the 0.1 deterministic engine. Authoritative financial numbers come only from the 0.1 engine. "
        "This list does not mark a draft or the official baseline investor-ready.</p>"
        f"<ul>{items}</ul>",
    )
