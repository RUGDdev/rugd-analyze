"""HTML pages for the local RUGD Analyze prototype."""

from __future__ import annotations

from html import escape
from typing import Any

from app import APP_VERSION
from app.analysis import ENGINE_PURPOSES, UNSUPPORTED_PURPOSES
from app.store import is_named_pilot, named_pilot_is_empty
from app.market import (
    DEMONSTRATION_GEOGRAPHIES,
    DEMONSTRATION_INDUSTRIES,
    assessment_implications,
    market_framework,
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
details {{ margin: 0.8rem 0; }}
summary {{ cursor: pointer; font-family: "Segoe UI", sans-serif; }}
.bar-track {{ background: var(--stone); height: 0.7rem; margin: 0.25rem 0 0.7rem; }}
.bar {{ background: var(--bronze); height: 0.7rem; }}
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
    items = "".join(_history_card(item) for item in records) or "<p>No assessments are saved.</p>"
    body = f"""
<h1>Customer dashboard</h1>
<p class="muted">Local test profile. This prototype has no accounts and no production security.</p>
<div class="card">
<p>Working now: Explore intake, Analyze through the 0.1 engine, reports, and the audit.</p>
<p>Demonstration only: Market Intelligence, Validate review requests, and the Partner dashboard. Partner monitoring is not running.</p>
</div>
<p><a class="button" href="/assessments/new">Start a new assessment</a></p>
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
        kind = "Hypothetical draft"
        progress = _draft_progress(item, result)
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
<a class="button" href="/assessments/{assessment_id}/results">View results</a></p>
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
        banner += '<div class="banner">Hypothetical demonstration. Figures are not verified market research.</div>'
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
    startup_missing = _missing_labels(profile, _STARTUP_REQUIRED)
    monthly_missing = _missing_labels(profile, _MONTHLY_REQUIRED)
    if startup_missing:
        startup_note = (
            "Missing required startup fields: "
            + ", ".join(startup_missing)
            + ". The startup cost build is not calculated until these are saved. "
            "Blank fields are not replaced with invented values."
        )
    else:
        startup_note = (
            "Required startup fields are filled. They remain user-supplied assumptions, not verified data."
        )
    if monthly_missing:
        monthly_note = (
            "Missing monthly fields: "
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
        body = f"<h1>Analyze</h1><div class=\"banner\">{escape(result.get('message', 'Analyze did not run.'))}</div>"
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
    links = f"""
<p><a class="button" href="/assessments/{escape(record['id'])}/report">Open report</a>
<a class="button" href="/assessments/{escape(record['id'])}/audit/html">HTML audit view</a>
<a class="button" href="/assessments/{escape(record['id'])}/audit">Inspect audit</a></p>
"""
    body = f"""
<h1>Results for {escape(record['business_name'])}</h1>
<div class="banner">{escape(standing)}</div>
{links}
<div class="card">
{_view_summary_block(result)}
<p class="muted">Engine {escape(str(result.get('model_version')))}. Service tier on this file: {escape(record['tier'])}. Figures below are deterministic engine outputs.</p>
</div>
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
<h2>Limitations</h2>
<p>This is a prototype. Demonstration data is not real market research. Reviewer authentication remains prototype-grade.</p>
"""


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


def market_page(
    records: list[dict[str, Any]] | None = None,
    industry: str | None = None,
    geographic_market: str | None = None,
) -> str:
    records = records or []
    snapshot = market_framework(industry, geographic_market)
    implications = "".join(f"<li>{escape(line)}</li>" for line in assessment_implications(records, industry, geographic_market))
    industry_options = _demo_options(DEMONSTRATION_INDUSTRIES, snapshot["industry"])
    geography_options = _demo_options(DEMONSTRATION_GEOGRAPHIES, snapshot["geographic_market"])
    body = f"""
<h1>Market Intelligence</h1>
<div class="banner">Demonstration only. This page does not load a live market feed.</div>
<form method="get" action="/market">
<label>Demonstration industry</label>
<select name="industry">{industry_options}</select>
<label>Demonstration geographic market</label>
<select name="geographic_market">{geography_options}</select>
<button type="submit">Show demonstration selection</button>
</form>
<p class="muted">The choices are labels for this demonstration. They are not a dataset and they do not describe a real market.</p>
{_market_block(snapshot)}
<h2>Implications for this assessment</h2>
<ul>{implications}</ul>
<p class="muted">The same demonstration snapshot is available on Partner. Neither view loads Census, BLS, or BEA data.</p>
"""
    return layout("Market Intelligence", body)


def _demo_options(choices: tuple[str, ...], current: str) -> str:
    return "".join(
        f'<option value="{escape(choice)}"{" selected" if choice == current else ""}>{escape(choice)}</option>'
        for choice in choices
    )


def audit_html_page(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    events: list[dict[str, Any]] | None = None,
) -> str:
    """Read-only audit view. This page has no control that can change the assessment."""
    from app.analysis import build_view_summary

    result = result or {}
    events = events or []
    if not result.get("engine_ran"):
        body = f"""
<h1>Audit view</h1>
<div class="banner">Audit view. Read only. Draft. This page cannot change flags, approval, readiness, or the recommendation.</div>
<p>{escape(result.get('message') or 'Analyze did not run.')}</p>
"""
        return layout("Audit view", body)
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
    body = f"""
<h1>Audit view for {escape(record['business_name'])}</h1>
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
<p><a href="/assessments/{escape(record['id'])}/audit">JSON audit</a>
<a href="/assessments/{escape(record['id'])}/results">Results</a></p>
"""
    return layout("Audit view", body)


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
<h1>Partner</h1>
<div class="banner">Demonstration dashboard. Recurring monitoring is not active. Recurring monitoring has not been implemented.</div>
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
    return layout("Reports", f"<h1>Reports</h1><ul>{items}</ul><p class=\"muted\">Reports are drafts unless the existing gate and an authorized review say otherwise. This prototype does not write the official 0.1 output files.</p>")


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
