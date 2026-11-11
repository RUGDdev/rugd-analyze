"""HTML pages for the local RUGD Analyze prototype."""

from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import urlencode

from app import APP_VERSION
from app.analyst import ASSISTANCE_LABEL, STARTER_QUESTIONS, agent_workflow, get_analyst
from app.adviser_flow import THEMES
from app.analysis import ENGINE_PURPOSES, UNSUPPORTED_PURPOSES
from app.objectives import OBJECTIVES, objective_label
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
    _for_tier,
    _tier_name,
    assessment_implications,
    load_market,
    market_framework,
)
from app.suggestions import SUGGESTION_NOTE, catalog_json, suggestions_for

_SURFACE_NOTE = (
    '<div class="banner">Local prototype. Not production security. '
    "This screen does not grant investor-ready status.</div>"
)

NAV = (
    ("/", "Dashboard", "See saved drafts and the next recommended step."),
    ("/explore", "Explore", "Start or continue an intake and save a draft."),
    ("/analyze", "Analyze", "Run the engine on a saved draft and read the result."),
    (
        "/validate",
        "Validate (demonstration)",
        "Request a human review in this demonstration. It cannot approve an assessment.",
    ),
    (
        "/partner",
        "Partner (demonstration)",
        "Open the partner dashboard. Monitoring is not running.",
    ),
    ("/assessments", "My Assessments", "Open, export, or start one of your drafts."),
    (
        "/market",
        "Market Intelligence (demonstration)",
        "Read a market snapshot for a place and an industry.",
    ),
    (
        "/market-pulse",
        "Market Pulse (demonstration)",
        "See example monitoring cards. Monitoring is not active.",
    ),
    ("/reports", "Reports", "Open a research brief or the audit of a saved result."),
    ("/login", "Login", "Sign in with a local email and password."),
    ("/register", "Register", "Create a local customer account."),
    ("/logout", "Log out", "End this local session."),
    ("/settings", "Settings", "Update this local account and its email preferences."),
)


_TITLE_ACTIVE = {
    "Dashboard": "/",
    "Explore": "/explore",
    "Analyze": "/analyze",
    "Results": "/analyze",
    "Analyst": "/analyze",
    "Validate": "/validate",
    "Partner": "/partner",
    "Market Intelligence": "/market",
    "Market Pulse": "/market-pulse",
    "Reports": "/reports",
    "Research Brief": "/reports",
    "Audit view": "/reports",
    "Settings": "/settings",
    "Login": "/login",
    "Forgot password": "/login",
    "Reset password": "/login",
    "Verify email": "/login",
    "Read-only share": "",
    "Advisor Summary": "/analyze",
    "Assistant": "/analyze",
    "Register": "/register",
    "Log out": "/logout",
    "New assessment": "/assessments",
    "Reviewer": "",
    "Reviewer control": "",
    "Reviewer accounts": "",
}


def layout(title: str, body: str, *, printable: bool = False, active: str = "") -> str:
    if active == "none":
        current = ""
    else:
        current = active or _TITLE_ACTIVE.get(title, "/assessments")
    links = []
    for href, label, tip in NAV:
        marker = ' class="active" aria-current="page"' if href == current else ""
        links.append(
            f'<a href="{href}"{marker}>{escape(label)}'
            f'<span class="nav-tip">{escape(tip)}</span></a>'
        )
    nav = "".join(links)
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
body {{ margin: 0; font-family: "Segoe UI", Calibri, sans-serif; background: var(--ivory); color: var(--ink); line-height: 1.45; }}
.shell {{ display: flex; min-height: 100vh; align-items: stretch; }}
.sidebar {{ position: relative; z-index: 2; width: 16.5rem; flex: 0 0 16.5rem; background: var(--slate); color: var(--ivory); padding: 0 0 1.5rem; overflow: visible; }}
.brand {{ display: block; background: var(--ivory); padding: 0.85rem 0.9rem 0.4rem; }}
.brand img {{ display: block; width: 100%; height: auto; }}
.brand-meta {{ margin: 0.75rem 1rem 1rem; color: var(--gold); font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; }}
nav {{ display: flex; flex-direction: column; gap: 0.15rem; padding: 0 0.75rem; }}
nav a {{ position: relative; color: var(--ivory); text-decoration: none; padding: 0.55rem 0.7rem; border-left: 3px solid transparent; }}
nav a:hover {{ background: #324656; }}
nav a.active {{ background: #324656; color: var(--gold); border-left-color: var(--bronze); }}
.nav-tip {{ display: none; position: absolute; z-index: 3; left: calc(100% + 0.35rem); top: 0.15rem; width: 14rem; background: var(--ivory); color: var(--ink); border-left: 3px solid var(--bronze); padding: 0.5rem 0.65rem; font-size: 0.82rem; line-height: 1.35; box-shadow: 0 2px 8px rgba(38, 55, 70, 0.18); pointer-events: none; }}
nav a:hover .nav-tip, nav a:focus-visible .nav-tip {{ display: block; }}
.workspace {{ position: relative; z-index: 1; flex: 1; min-width: 0; }}
main {{ max-width: 980px; margin: 0 auto; padding: 2rem 1.75rem 3rem; }}
h1 {{ font-weight: 600; font-size: 2rem; letter-spacing: -0.02em; margin: 0 0 0.6rem; }}
h2 {{ font-weight: 600; font-size: 1.35rem; margin-top: 1.6rem; padding-bottom: 0.25rem; border-bottom: 1px solid var(--stone); }}
h3 {{ font-weight: 600; }}
.banner {{ background: var(--gold); border-left: 4px solid var(--bronze); padding: 0.85rem 1rem; margin: 1rem 0; }}
.card {{ background: white; border: 1px solid var(--stone); padding: 1.15rem 1.3rem; margin: 1rem 0; }}
.assessment-card .card-title {{ font-size: 1.45rem; margin: 0 0 0.2rem; border: 0; padding: 0; }}
.card-meta, .card-updated {{ margin: 0.25rem 0; }}
.status-line {{ font-size: 1.05rem; margin: 0.55rem 0 0.2rem; }}
.badges {{ margin: 0.45rem 0; }}
.badge {{ display: inline-block; background: var(--slate); color: var(--ivory); padding: 0.18rem 0.55rem; margin: 0 0.35rem 0.25rem 0; font-size: 0.82rem; letter-spacing: 0.01em; }}
.badge-blocked {{ background: #7a2e2e; }}
.badge-open {{ background: var(--bronze); color: var(--slate); }}
.card-action {{ margin-top: 0.7rem; }}
.empty-state {{ border-left: 4px solid var(--bronze); }}
.button.primary {{ padding: 0.72rem 1.15rem; font-weight: 600; }}
details.plain {{ margin: 0.35rem 0 0.75rem; }}
details.plain summary {{ cursor: pointer; }}
.assistant-reply {{ background: white; border-left: 4px solid var(--bronze); padding: 0.75rem 1rem; margin: 0.6rem 0; }}
label {{ display: block; margin: 0.7rem 0 0.2rem; font-size: 0.92rem; }}
input, select, textarea {{ width: 100%; padding: 0.5rem; border: 1px solid var(--stone); background: white; color: var(--ink); font: inherit; }}
button, .button {{ background: var(--ink); color: var(--ivory); border: 0; padding: 0.55rem 0.9rem; text-decoration: none; display: inline-block; margin: 0.35rem 0.45rem 0.35rem 0; }}
button:hover, .button:hover {{ background: var(--bronze); color: var(--slate); }}
button.chip, .chip {{ width: auto; background: white; color: var(--ink); border: 1px solid var(--bronze); font-size: 0.88rem; font-weight: 400; padding: 0.28rem 0.65rem; margin: 0.2rem 0.4rem 0.2rem 0; }}
button.chip:hover {{ background: var(--gold); color: var(--ink); }}
.field-suggest {{ position: relative; }}
.suggest {{ display: none; position: absolute; z-index: 5; left: 0; right: 0; top: 100%; background: white; border: 1px solid var(--stone); border-left: 4px solid var(--bronze); padding: 0.35rem 0.75rem 0.55rem; box-shadow: 0 2px 8px rgba(38, 55, 70, 0.16); }}
.field-suggest:hover > .suggest, .field-suggest:focus-within > .suggest {{ display: block; }}
.field-suggest.is-closed > .suggest, .field-suggest.is-closed:hover > .suggest, .field-suggest.is-closed:focus-within > .suggest {{ display: none; }}
.suggest-note {{ color: #5c6b76; font-size: 0.86rem; margin: 0.35rem 0 0.6rem; }}
.muted {{ color: #5c6b76; font-size: 0.92rem; }}
table {{ width: 100%; border-collapse: collapse; background: white; margin: 0.6rem 0 1rem; }}
th {{ text-align: left; padding: 0.5rem 0.55rem; background: var(--slate); color: var(--ivory); font-weight: 600; }}
td {{ text-align: left; padding: 0.45rem 0.55rem; border-bottom: 1px solid var(--stone); }}
tr:nth-child(even) td {{ background: #faf8f4; }}
.flag {{ color: #7a2e2e; font-weight: 650; }}
pre {{ white-space: pre-wrap; font-family: Consolas, monospace; font-size: 0.86rem; background: white; border: 1px solid var(--stone); padding: 0.8rem; }}
details {{ margin: 0.8rem 0; }}
summary {{ cursor: pointer; }}
.bar-track {{ background: var(--stone); height: 0.7rem; margin: 0.25rem 0 0.7rem; }}
.bar {{ background: var(--bronze); height: 0.7rem; }}
.journey {{ display: flex; gap: 0.4rem; list-style: none; padding: 0; margin: 0.9rem 0 0.35rem; counter-reset: rugd-step; }}
.journey li {{ flex: 1; background: white; border: 1px solid var(--stone); border-top: 4px solid var(--stone); padding: 0.55rem 0.6rem; font-weight: 600; text-align: center; }}
.journey li::before {{ counter-increment: rugd-step; content: counter(rugd-step) ". "; color: var(--bronze); }}
.journey li.done {{ border-top-color: var(--bronze); color: var(--slate); }}
.journey li.current {{ border-top-color: var(--bronze); background: var(--gold); color: var(--ink); }}
.agent-flow {{ display: flex; gap: 0.4rem; list-style: none; padding: 0; margin: 0.6rem 0; flex-wrap: wrap; }}
.agent-flow li {{ flex: 1; min-width: 7.5rem; background: white; border: 1px solid var(--stone); border-top: 4px solid var(--stone); padding: 0.45rem 0.5rem; font-weight: 600; text-align: center; }}
.agent-flow li.done {{ border-top-color: var(--bronze); color: var(--slate); }}
.agent-flow li.current {{ border-top-color: var(--bronze); background: var(--gold); color: var(--ink); }}
.journey.card-journey {{ margin: 0.35rem 0 0.7rem; }}
.journey.card-journey li {{ padding: 0.35rem 0.4rem; font-size: 0.82rem; }}
.glance {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; margin: 0 0 1rem; }}
.glance p {{ background: white; border: 1px solid var(--stone); border-top: 4px solid var(--bronze); margin: 0; padding: 0.65rem 0.75rem; }}
.start-here {{ margin: 0.4rem 0 1rem; padding-left: 1.2rem; }}
.start-here li {{ margin: 0.35rem 0; }}
.nudge {{ border-left: 4px solid var(--bronze); }}
.nudge[hidden] {{ display: none; }}
.objectives {{ list-style: none; padding: 0; margin: 0.4rem 0 0; }}
.objectives li {{ margin: 0.45rem 0; }}
.objectives button {{ width: 100%; text-align: left; }}
.adviser-log {{ list-style: none; padding: 0; margin: 0.4rem 0; }}
.adviser-log li {{ background: white; border: 1px solid var(--stone); border-left: 4px solid var(--bronze); padding: 0.55rem 0.7rem; margin: 0.35rem 0; }}
.adviser-log .you {{ border-left-color: var(--slate); }}
.figure-notes {{ margin-top: 0; }}
#results-lead, #advisor-sheet, #market-provenance {{ border-top: 4px solid var(--bronze); }}
#results-lead {{ padding: 1.25rem 1.4rem 1.4rem; }}
.figure-block {{ background: var(--ivory); border: 1px solid var(--stone); padding: 0.15rem 1rem 0.4rem; margin-top: 1rem; }}
#your-next-step {{ border-left: 4px solid var(--bronze); }}
.advisor-page h2 {{ margin-top: 1.15rem; }}
.advisor-page .card {{ margin: 0.65rem 0; }}
@media (max-width: 800px) {{
  .shell {{ flex-direction: column; }}
  .sidebar {{ width: 100%; flex-basis: auto; }}
  nav {{ flex-direction: row; flex-wrap: wrap; }}
  .nav-tip {{ left: 0; top: calc(100% + 0.2rem); width: 12.5rem; }}
  main {{ padding: 1.25rem 1rem 2rem; }}
  .glance {{ grid-template-columns: 1fr; }}
}}
@media print {{
  .sidebar, nav, .no-print {{ display: none !important; }}
  body, main, .workspace {{ background: white; color: black; max-width: none; }}
  .limitations, .card, h1, h2, ul, table, p, .banner {{ visibility: visible; }}
  a {{ color: black; text-decoration: none; }}
  th {{ color: black; background: white; }}
}}
body.print-view {{ background: white; }}
body.print-view .sidebar {{ display: none; }}
</style>
</head>
<body{" class=\"print-view\"" if printable else ""}>
<div class="shell">
<aside class="sidebar">
<a class="brand" href="/"><img src="/static/rugd-logo.png" alt="RUGD Intelligence"></a>
<p class="brand-meta">Analyze {escape(APP_VERSION)} · local prototype · not investor-approved</p>
<nav>{nav}</nav>
</aside>
<div class="workspace">
<main>
{body}
</main>
</div>
</div>
</body>
</html>"""


def _continue_intake(record: dict[str, Any]) -> str:
    """Primary link to this draft's Explore intake. Editing does not clear a flag."""
    assessment_id = escape(str(record.get("id") or ""))
    href = f"/assessments/{assessment_id}#intake"
    analyzed = bool((record.get("result") or {}).get("engine_ran"))
    label = "Edit Intake" if analyzed else "Continue Intake"
    if analyzed:
        note = (
            "Editing the intake does not clear a recommend-against flag, "
            "change the stored recommendation, or set human_review_approved."
        )
    else:
        note = (
            "Opening the intake does not clear a recommend-against flag "
            "or set human_review_approved."
        )
    return (
        f'<p><a class="button" href="{href}">{label}</a></p>'
        f'<p class="muted">{note}</p>'
    )


def _plain(key: str) -> str:
    from app.plain import term_note

    return term_note(key)


def _section_welcome(title: str, first: str, second: str, *, demonstration: str = "") -> str:
    label = f'<p class="muted">{escape(demonstration)}</p>' if demonstration else ""
    return (
        '<header class="card" id="section-welcome">'
        f"<h1>{escape(title)}</h1>{label}"
        f"<p>{escape(first)}</p><p>{escape(second)}</p>"
        "</header>"
    )


def _guest_dashboard() -> str:
    body = f"""
<div class="banner" id="guest-welcome">
<h1>Welcome to RUGD Intelligence</h1>
<p>RUGD Intelligence helps you write down a business idea, see which evidence is still missing, and read the engine result after you run Analyze.</p>
<p>This is a local pilot prototype. It does not grant investor-ready status. No feasibility score is calculated.</p>
<p><a class="button" href="/login">Log in</a>
<a class="button" href="/register">Register</a></p>
</div>
{_objective_chooser()}
{_SURFACE_NOTE}
<p class="muted">Sign in to see your own assessments. This screen does not list anyone else's drafts.</p>
"""
    return layout("Dashboard", body)


def _pilot_purpose() -> str:
    """States the review purpose. It does not change a stored result."""
    return """
<section class="card" id="pilot-purpose">
<h2>What this review is for</h2>
<p>This screen is for a pilot review of a draft. It shows the hard evidence gate, the stored engine result when one exists, and where a market figure comes from.</p>
<p>A hard recommend-against flag keeps the recommendation at do-not-proceed. An indicative number, a market figure, and an assistant reply cannot clear that flag or grant investor-ready status.</p>
<p class="muted">This local prototype is not a billing system, a live market feed, or a pitch deck.</p>
</section>
"""


def _draft_market_context(record: dict[str, Any]) -> str:
    """Name the entered industry. Do not invent a market figure or clear a flag."""
    profile = record.get("profile") or {}
    industry = str(profile.get("industry") or "not entered")
    geography = str(profile.get("market") or "not entered")
    snapshot = market_framework(industry, geography)
    examples = "".join(f"<li>{escape(line)}</li>" for line in snapshot["synthetic_examples"])
    return f"""
<section class="card" id="draft-market-context">
<h2>Market context for this draft</h2>
<p><strong>Industry entered:</strong> {escape(industry)}. <strong>Geography entered:</strong> {escape(geography)}.</p>
<p>{escape(str(snapshot.get('label') or ''))} Live feed connected: false. Optional public extracts for BLS QCEW, ACS, County Business Patterns, BEA Regional, and LAUS are requested on Market Intelligence. They are not loaded on this page.</p>
<ul>{examples}</ul>
<p>These figures do not clear a recommend-against flag and do not grant investor-ready status.</p>
</section>
"""


def dashboard(
    records: list[dict[str, Any]],
    *,
    signed_in: bool = False,
    viewer_id: str = "",
    surface: str = "home",
) -> str:
    """Home page. A signed-out visitor sees no assessment data."""
    if not signed_in:
        return _guest_dashboard()
    owned = [
        item
        for item in records
        if viewer_id and str(item.get("owner_user_id") or "") == viewer_id
    ]
    items = "".join(_history_card(item) for item in owned)
    empty = ""
    step = ""
    focus = _focus_record(owned)
    if focus is not None:
        step = _your_next_step(focus)
    else:
        empty = """
<div class="card empty-state" id="your-assessments-empty">
<h2>No assessments yet</h2>
<p>You have not created an assessment. Blank fields stay blank until you enter them. Nothing is copied from the official baseline.</p>
<p><strong>What to do first:</strong> Choose Start a new assessment. Say whether this is a startup idea or an existing business. Save the draft, then fill the blank required fields.</p>
<p><a class="button primary" href="/assessments/new">Start a new assessment</a></p>
</div>
"""
    if surface == "assessments":
        heading = _section_welcome(
            "Welcome to RUGD My Assessments",
            "This page lists the assessments this account created.",
            "You can continue a draft or open a stored result. The list does not grant investor-ready status.",
        )
        title = "My Assessments"
    else:
        heading = "<h1>Your assessments</h1>"
        title = "Dashboard"
    body = f"""
{heading}
<p>This page is the home for this account. Each card shows the stage, the stored status, and one primary action.</p>
{_objective_chooser()}
{_SURFACE_NOTE}
{_pilot_purpose()}
<p class="muted">These are the assessments this account created. This list does not grant investor-ready status. An indicative assessment is shown after Analyze. It does not override engine flags or human review. No feasibility score is calculated. An owner can create a read-only share. The shared page cannot edit or approve the assessment.</p>
<p><a class="button primary" href="/assessments/new">Start a new assessment</a></p>
{empty}
{step}
{items}
<div class="card">
<h2>Words you will see</h2>
<p>The precise term stays in the heading. The sentence next to it is the plain meaning. Learn more keeps the tighter definition.</p>
{_plain("recommendation")}
{_plain("insufficient_demand_evidence")}
{_plain("investor_readiness")}
</div>
{_module_guide()}
"""
    return layout(title, body)


def _history_card(item: dict[str, Any]) -> str:
    result = item.get("result") if isinstance(item.get("result"), dict) else {}
    result = result or {}
    assessment_id = escape(str(item.get("id") or ""))
    if result.get("engine_ran"):
        action = (
            f'<a class="button primary" href="/assessments/{assessment_id}/results">View Results</a>'
        )
        gate = _gate_line(result)
    else:
        action = f'<a class="button primary" href="/assessments/{assessment_id}#intake">Continue Intake</a>'
        gate = ""
    kind = _card_kind(item)
    kind_line = f'<p class="muted">{escape(kind)}</p>' if kind else ""
    return f"""
<article class="card assessment-card">
<h2 class="card-title">{escape(str(item.get("business_name") or "Untitled"))}</h2>
{kind_line}
<p class="card-meta"><strong>Business stage:</strong> {escape(_stage_label(item))}</p>
{_card_journey(item)}
{gate}
<p class="status-line">{escape(_engine_status_line(result))}</p>
<p class="card-updated"><strong>Last updated:</strong> {escape(str(item.get("updated_at") or "not recorded"))}</p>
<p class="card-action">{action}</p>
<p><a href="/assessments/{assessment_id}#assistant">Ask about this assessment</a></p>
<p class="muted">This card does not grant investor-ready status.</p>
</article>
"""


def _card_kind(item: dict[str, Any]) -> str:
    if item.get("read_only"):
        return "Official baseline. Not a completed customer study."
    if item.get("hypothetical"):
        return HYPOTHETICAL_DEMO_LABEL
    if item.get("id") == RESTAURANT_VERIFIED_ID:
        return "Verified-demand demonstration — not a real assessment"
    if is_named_pilot(item):
        if named_pilot_is_empty(item):
            return "Empty named-pilot draft. Not a completed assessment."
        return "Named-pilot draft. Not a completed assessment."
    return ""


def _stage_label(item: dict[str, Any]) -> str:
    profile = item.get("profile") or {}
    path = "Existing or expanding business" if venture_path_of(item) == "existing" else "Startup idea"
    stage = str(profile.get("stage") or "").strip()
    if stage:
        return f"{path} · {stage}"
    return path


def _gate_line(result: dict[str, Any]) -> str:
    from app.indicative_score import indicative_score

    score = indicative_score(result)
    status = str(score.get("gate_status") or "")
    band = str(score.get("band") or "")
    tone = "blocked" if status == "Blocked" else "open" if status == "Open" else "plain"
    return (
        f'<p class="badges"><span class="badge badge-{tone}">Gate {escape(status)}</span>'
        f'<span class="badge">Band {escape(band)}</span></p>'
        f"<p><strong>Gate status:</strong> {escape(status)}. "
        f"<strong>Band:</strong> {escape(band)}.</p>"
        + _gate_gloss(status, band)
        + "<p class=\"muted\">Indicative assessment — market validity, financial viability, and "
        "stewardship readiness. Does not override engine flags or human review.</p>"
    )


def _engine_status_line(result: dict[str, Any]) -> str:
    """One sentence from stored engine output. Missing figures stay unstated."""
    if not result.get("engine_ran"):
        return "Analyze has not been run."
    flags = [str(flag) for flag in result.get("blocking_flags") or []]
    if "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
        return "Demand evidence missing."
    if _base_dscr_present(result):
        return "Base case DSCR available."
    if flags:
        return f"Recommend-against flag {flags[0]} is active."
    recommendation = str(result.get("recommendation") or "").strip()
    if recommendation:
        return f"Stored recommendation: {recommendation}."
    return "An engine result is stored."


def _base_dscr_present(result: dict[str, Any]) -> bool:
    projection = result.get("projection") if isinstance(result.get("projection"), dict) else {}
    views = projection.get("views") if isinstance(projection, dict) else {}
    base = views.get("base") if isinstance(views, dict) else {}
    value = base.get("dscr") if isinstance(base, dict) else None
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _draft_label(record: dict[str, Any] | None) -> str:
    """A visible draft mark when the file is not an approved review."""
    if (record or {}).get("human_review_approved") is True:
        return ""
    return "Draft. "


def _gate_gloss(status: str, band: str) -> str:
    """Everyday words beside the stored gate and band. They do not change either."""
    status_words = {
        "Blocked": "In everyday words: a hard gate is still closed, so the recommendation stays do-not-proceed.",
        "Open": "In everyday words: no hard recommend-against flag is forcing this gate closed. Open is not investor-ready.",
    }
    band_words = {
        "Blocked": "In everyday words: this band follows the closed gate. The number does not override it.",
        "Strong": "In everyday words: the indicative number is in the strong range. It does not clear a flag.",
        "Conditional": "In everyday words: the indicative number is in the middle range. It does not clear a flag.",
        "Weak": "In everyday words: the indicative number is in the low range. It does not clear a flag.",
    }
    status_line = status_words.get(
        status,
        "In everyday words: this gate reads the stored result. It does not change it.",
    )
    band_line = band_words.get(
        band,
        "In everyday words: this band is a label on the indicative number. It does not grant investor-ready status.",
    )
    return f'<p class="muted">{escape(status_line)}</p><p class="muted">{escape(band_line)}</p>'


def _journey_items(current: str) -> str:
    steps = (("intake", "Intake"), ("analyze", "Analyze"), ("review", "Review"))
    order = [key for key, _label in steps]
    index = order.index(current) if current in order else 0
    items = []
    for position, (key, label) in enumerate(steps):
        if key == current:
            marker = ' class="current" aria-current="step"'
        elif position < index:
            marker = ' class="done"'
        else:
            marker = ""
        items.append(f"<li{marker}>{label}</li>")
    return "".join(items)


def _journey_progress(current: str) -> str:
    """Informational stages. The marker does not write a flag or a recommendation."""
    return (
        '<ol class="journey" id="journey-progress">'
        + _journey_items(current)
        + "</ol>"
        '<p class="muted">This progress indicator is informational. '
        "It does not change a flag or a recommendation.</p>"
    )


def _card_journey(record: dict[str, Any]) -> str:
    """A short progress mark on a dashboard card. It does not write a result."""
    return (
        '<ol class="journey card-journey" aria-label="Where this draft is">'
        + _journey_items(_journey_stage(record))
        + "</ol>"
    )


def _at_a_glance(record: dict[str, Any], result: dict[str, Any]) -> str:
    """Three stored facts before the long tables. No figure is invented."""
    from app.indicative_score import indicative_score

    score = indicative_score(result)
    recommendation = str(result.get("recommendation") or "not run")
    gate = str(score.get("gate_status") or "Not run")
    return f"""
<div class="glance" id="at-a-glance">
<p><strong>Recommendation</strong><br>{escape(recommendation)}</p>
<p><strong>Gate status</strong><br>{escape(gate)}</p>
<p><strong>Next</strong><br>{escape(_next_step_for(record))}</p>
</div>
<p class="muted">These three lines read the stored file. They do not change a flag or a recommendation.</p>
"""


def _advisor_glance(assessment: dict[str, Any], indicative: dict[str, Any]) -> str:
    """Three stored facts for the advisor page. This view does not save them."""
    recommendation = str(assessment.get("recommendation") or "not run")
    gate = str((indicative or {}).get("gate_status") or "Not run")
    readiness = str(assessment.get("readiness_status") or "not run")
    return f"""
<div class="glance" id="advisor-glance">
<p><strong>Recommendation</strong><br>{escape(recommendation)}</p>
<p><strong>Gate status</strong><br>{escape(gate)}</p>
<p><strong>Investor readiness</strong><br>{escape(readiness)}</p>
</div>
<p class="muted">These three lines read the stored file. They do not approve the assessment.</p>
"""


def _intake_start() -> str:
    """Numbered start for a long form. It does not fill a field."""
    return """
<ol class="start-here" id="intake-start">
<li><strong>Describe the business.</strong> Industry, stage, customers, and competition stay your assumptions.</li>
<li><strong>Enter the monthly figures you know.</strong> Leave a blank blank. This form does not invent a number.</li>
<li><strong>Save, then run Analyze.</strong> The engine writes the result. A suggestion does not clear a gate.</li>
</ol>
"""


def _journey_stage(record: dict[str, Any] | None, *, review_requested: bool = False) -> str:
    record = record or {}
    if review_requested or record.get("review_requested"):
        return "review"
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    if (result or {}).get("engine_ran") or record.get("engine_ran"):
        return "analyze"
    return "intake"


def _your_next_step(record: dict[str, Any]) -> str:
    assessment_id = escape(str(record.get("id") or ""))
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    if (result or {}).get("engine_ran"):
        href = f"/assessments/{assessment_id}/results"
        label = "View Results"
    else:
        href = f"/assessments/{assessment_id}#intake"
        label = "Continue Intake"
    return f"""
<div class="card" id="your-next-step">
<h2>Your next step</h2>
<p><strong>Guidance. Not a decision.</strong></p>
<p><strong>Next recommended step:</strong> {escape(_next_step_for(record))}</p>
<p><a class="button" href="{href}">{label}</a></p>
<p class="muted">Completing this step does not clear a hard gate, change a recommendation, or mark the assessment investor-ready.</p>
</div>
"""


def _focus_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    drafts = [item for item in records if not item.get("read_only")]
    if not drafts:
        return None
    for item in drafts:
        flags = (item.get("result") or {}).get("blocking_flags") or []
        if "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
            return item
    for item in drafts:
        if not (item.get("result") or {}).get("engine_ran"):
            return item
    for item in drafts:
        flags = (item.get("result") or {}).get("blocking_flags") or []
        if flags:
            return item
    return drafts[0]


def _next_step(records: list[dict[str, Any]]) -> str:
    focus = _focus_record(records)
    if focus is None:
        return "Start a new assessment. The official baseline is not a customer draft."
    return _next_step_for(focus)


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
    path = venture_path_of(record)
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
    if path != "existing":
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


def _verified_demand_ready(profile: dict[str, Any]) -> bool:
    source = str(profile.get("verified_record_source") or "").strip()
    rationale = str(profile.get("verified_demand_rationale") or "").strip()
    claim = str(profile.get("verified_demand_evidence") or "").strip().lower()
    return source == "verified" and bool(rationale) and claim == "true"


def _guidance_section(
    depth: str,
    result: dict[str, Any] | None = None,
    notes: list[dict[str, Any]] | None = None,
    record: dict[str, Any] | None = None,
) -> str:
    from app.durable_value import guidance_for

    view = guidance_for(depth, result)
    intro = []
    prompts = []
    relevant = []
    other = []
    for pillar in view["pillars"]:
        title = escape(str(pillar["title"]))
        intro.append(
            f"<li><strong>{title}.</strong> Introductory question: "
            f"{escape(str(pillar['introductory_question']))}</li>"
        )
        prompts.append(
            f"<li><strong>{title}.</strong> Practical prompt: "
            f"{escape(str(pillar['practical_prompt']))}</li>"
        )
        if pillar["relevant"]:
            flags = ", ".join(str(flag) for flag in pillar["matched_flags"])
            relevant.append(
                f"<li><strong>{title}.</strong> Next to engine flag {escape(flags)}. "
                f"Practical prompt: {escape(str(pillar['practical_prompt']))}</li>"
            )
        else:
            other.append(
                f"<li><strong>{title}.</strong> Not next to a flag on this result. "
                f"Practical prompt: {escape(str(pillar['practical_prompt']))}</li>"
            )
    if depth == "explore":
        body = f"<h3>Introductory questions</h3><ul>{''.join(intro)}</ul>"
    elif depth == "analyze":
        if relevant:
            matched = f"<ul>{''.join(relevant)}</ul>"
        else:
            matched = "<p>No pillar is tied to a flag or gap on this result.</p>"
        body = (
            "<h3>Considerations next to flags and gaps</h3>"
            f"{matched}"
            "<h3>Other educational prompts</h3>"
            f"<ul>{''.join(other)}</ul>"
        )
    else:
        matched = ""
        if relevant:
            matched = (
                "<h3>Considerations next to flags and gaps</h3>"
                f"<ul>{''.join(relevant)}</ul>"
            )
        body = (
            "<p>Demonstration view. The questions and prompts below are the same educational content.</p>"
            f"<h3>Introductory questions</h3><ul>{''.join(intro)}</ul>"
            f"<h3>Practical prompts</h3><ul>{''.join(prompts)}</ul>"
            f"{matched}"
        )
    note_items = []
    for item in notes or []:
        note_items.append(
            f"<li><strong>{escape(str(item.get('pillar_title') or item.get('pillar_id')))}.</strong> "
            f"{escape(str(item.get('note') or ''))} Non-authoritative.</li>"
        )
    if note_items:
        stored = f"<ul>{''.join(note_items)}</ul>"
    elif record and record.get("read_only"):
        stored = "<p>The official baseline does not store educational notes.</p>"
    else:
        stored = "<p>No educational note is stored.</p>"
    form = ""
    if record and not record.get("read_only"):
        options = []
        for pillar in view["pillars"]:
            options.append(
                f'<option value="{escape(str(pillar["id"]))}">{escape(str(pillar["title"]))}</option>'
            )
        form = f"""
<form method="post" action="/assessments/{escape(str(record.get('id')))}/guidance">
<label>Pillar for an educational note</label>
<select name="pillar_id">{''.join(options)}</select>
<label>Educational note</label>
<textarea name="note"></textarea>
<button type="submit">Save educational note</button>
</form>
<p class="muted">Saving a note does not run the engine. It does not change the recommendation, flags, readiness, or human_review_approved.</p>
"""
    return f"""
<section>
<h2>Durable Value guidance</h2>
<p><strong>{escape(view['label'])}</strong></p>
<p>No score is calculated. These prompts do not change the recommendation, flags, readiness, or human_review_approved.</p>
{body}
<h3>Educational notes</h3>
<p>Optional notes stored on the assessment. Non-authoritative. They are not engine inputs.</p>
{stored}
{form}
</section>
"""


def _business_profile_card(record: dict[str, Any]) -> str:
    business = record.get("business_profile") or {}
    if not business:
        return """
<h2>Business profile</h2>
<p>No business profile is linked yet. Local prototype structure. It does not authenticate a user.</p>
"""
    linked = "".join(
        f"<li><a href=\"/assessments/{escape(str(item.get('id')))}\">{escape(str(item.get('business_name')))}</a>"
        f" · {escape(str(item.get('tier')))}</li>"
        for item in record.get("linked_assessments") or []
    ) or "<li>None</li>"
    if business.get("isolation") == "baseline":
        standing = (
            "<p>Official baseline profile. Isolated from drafts and named pilots. "
            "This profile cannot be linked to another assessment.</p>"
        )
    elif business.get("isolation") == "pilot":
        standing = (
            "<p>Named-pilot or demonstration profile. Isolated from the official baseline "
            "and from customer profiles.</p>"
        )
    else:
        standing = "<p>Local prototype business profile. It does not authenticate a user.</p>"
    form = ""
    if not record.get("read_only") and business.get("isolation") != "baseline":
        options = []
        for key in ("explore", "analyze", "validate", "partner"):
            selected = " selected" if record.get("tier") == key else ""
            options.append(f'<option value="{key}"{selected}>{key.title()}</option>')
        form = f"""
<form method="post" action="/assessments/{escape(str(record.get('id')))}/linked">
<label>Another assessment for this business</label>
<select name="tier">{''.join(options)}</select>
<input type="hidden" name="purpose" value="{escape(str(record.get('purpose') or ''))}">
<button type="submit">Start another assessment for this business</button>
</form>
<p class="muted">Identity, industry, geography, and stage are copied. Financial entries and evidence stay on the current draft. This does not change a recommendation.</p>
"""
    industry = str(business.get("industry") or "") or "not entered"
    geography = str(business.get("geography") or "") or "not entered"
    stage = str(business.get("stage") or "") or "not entered"
    path_label = (
        "Existing or expanding business"
        if venture_path_of(record) == "existing"
        else "Startup idea"
    )
    return f"""
<h2>Business profile</h2>
{standing}
<p><strong>Identity:</strong> {escape(str(business.get('display_name') or ''))}</p>
<p><strong>Onboarding path:</strong> {escape(path_label)}</p>
<p><strong>Industry:</strong> {escape(industry)}</p>
<p><strong>Geography:</strong> {escape(geography)}</p>
<p><strong>Stage:</strong> {escape(stage)}</p>
<p>Linked assessments</p>
<ul>{linked}</ul>
{form}
"""


def assessment_form(
    record: dict[str, Any], notice: str = "", notes: list[dict[str, Any]] | None = None
) -> str:
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
    path = venture_path_of(record)
    if path == "existing":
        banner += (
            '<div class="banner">Existing or expanding business. This shorter intake skips '
            "startup-only cost-build questions and still collects the monthly engine inputs. "
            "This choice does not clear a flag or grant investor-ready status.</div>"
        )
    fields = _fields(profile, locked, path)
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
{_SURFACE_NOTE}
{banner}
{_explore_workspace(record)}
{_journey_progress(_journey_stage(record))}
{_adviser_nudge(record, "intake")}
{_your_next_step(record)}
{_continue_intake(record)}
<div class="card">
<h2>What this means</h2>
<p><strong>What to do next:</strong> Fill the blank required fields, save the draft, then run Analyze. The engine writes the result. This page does not invent a number.</p>
{_plain("insufficient_demand_evidence")}
{_plain("investor_readiness")}
</div>
{_assistant_panel(record, surface="intake")}
{_evidence_checklist(record, record.get("result"), notes, return_to="draft")}
{_intake_status(record)}
{_business_profile_card(record)}
<p class="muted">Tier {escape(record['tier'])}. Changing tier does not change a recommendation. Entered answers stay user-supplied assumptions.</p>
<h2 id="intake">Explore intake</h2>
{_intake_start()}
{action}
<p><a href="/assessments/{escape(record['id'])}/analyst">Open the Demonstration Analyst</a>
<a href="/assessments/{escape(record['id'])}/export">Export draft as JSON</a></p>
{_guidance_section("explore", notes=notes, record=record)}
"""
    return layout(record["business_name"], body)


def share_panel(
    record: dict[str, Any],
    links: list[dict[str, Any]],
    *,
    reveal_path: str = "",
    message: str = "",
) -> str:
    """Owner or reviewer controls. These forms are not part of the shared view."""
    notice = f"<p class=\"flag\">{escape(message)}</p>" if message else ""
    revealed = ""
    if reveal_path:
        revealed = (
            "<p><strong>Read-only link, shown once:</strong> "
            f"<a href=\"{escape(reveal_path)}\">{escape(reveal_path)}</a></p>"
            "<p class=\"muted\">This link cannot edit the assessment or approve it.</p>"
        )
    rows = []
    for item in links:
        expiry = item.get("expires_at") or "Until revoked"
        rows.append(
            "<li>"
            f"Created {escape(str(item.get('created_at') or ''))}. "
            f"Expires: {escape(str(expiry))}. "
            f"<form method=\"post\" action=\"/assessments/{escape(record['id'])}/share/{escape(item['id'])}/revoke\">"
            "<button type=\"submit\">Revoke</button></form>"
            "</li>"
        )
    listed = "".join(rows) or "<li>No active read-only link.</li>"
    return f"""
<section class="card">
<h2>Read-only share</h2>
{notice}
{revealed}
<p>An assessment owner or a reviewer can create a time-limited or revocable read-only link. The shared view has no edit controls and no approval controls.</p>
<form method="post" action="/assessments/{escape(record['id'])}/share">
<label>Link lifetime</label>
<select name="lifetime">
<option value="24h">24 hours</option>
<option value="7d" selected>7 days</option>
<option value="until-revoked">Until revoked</option>
</select>
<button type="submit">Create read-only link</button>
</form>
<ul>{listed}</ul>
</section>
"""


def shared_assessment_page(
    record: dict[str, Any],
    result: dict[str, Any] | None = None,
    notes: list[dict[str, Any]] | None = None,
    *,
    share_path: str = "",
) -> str:
    """A share link. No save, analyze, review-request, or approval control."""
    result = result or {}
    profile = record.get("profile") or {}
    industry = str(profile.get("industry") or "not entered")
    geography = str(profile.get("market") or "not entered")
    stage = str(profile.get("stage") or "not entered")
    snapshot = market_framework(industry, geography)
    examples = "".join(f"<li>{escape(line)}</li>" for line in snapshot["synthetic_examples"])
    if result.get("engine_ran"):
        standing = _view_summary_block(result)
        indicative = _indicative_block(result, notes)
    elif record.get("read_only"):
        standing = """
<p><strong>Recommendation:</strong> do-not-proceed</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> present</p>
<p><strong>Investor readiness:</strong> internal</p>
<p><strong>Human review status:</strong> pending</p>
<p><strong>human_review_approved:</strong> false</p>
<p><strong>Score:</strong> Not calculated — methodology pending approval.</p>
"""
        indicative = (
            "<p>Indicative assessment is shown after Analyze has been run. "
            "No feasibility score is calculated.</p>"
        )
    else:
        standing = """
<p><strong>Recommendation:</strong> not run</p>
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> not run</p>
<p><strong>Investor readiness:</strong> not run</p>
<p><strong>Human review status:</strong> pending</p>
<p><strong>human_review_approved:</strong> false</p>
<p><strong>Score:</strong> Not calculated — methodology pending approval.</p>
"""
        indicative = (
            "<p>Indicative assessment is shown after Analyze has been run. "
            "No feasibility score is calculated.</p>"
        )
    advisor_link = ""
    if share_path:
        advisor_link = (
            f'<p class="no-print"><a class="button" href="{escape(share_path)}/advisor">'
            "Open Advisor Summary</a></p>"
        )
    body = f"""
<h1>Read-only share for {escape(record['business_name'])}</h1>
{_pilot_banner(record)}
{_SURFACE_NOTE}
<div class="banner">{_draft_label(record)}Read-only share. This link cannot edit the assessment, request review, or approve it. It does not grant investor-ready status.</div>
{advisor_link}
<div class="card">
{standing}
<p class="muted">Authoritative figures come only from the 0.1 engine. This page does not run the engine.</p>
</div>
{indicative}
<h2>Market context</h2>
<p><strong>Industry:</strong> {escape(industry)}</p>
<p><strong>Geography:</strong> {escape(geography)}</p>
<p><strong>Stage:</strong> {escape(stage)}</p>
<p>{escape(snapshot['label'])} Live feed connected: false. Monitoring active: false.</p>
<ul>{examples}</ul>
<p>These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag.</p>
<h2>Audit summary</h2>
<div class="card">
{standing}
</div>
{_LIMITATIONS}
"""
    return layout("Read-only share", body)


def _fields(profile: dict[str, Any], locked: str, path: str = "startup") -> str:
    examples = suggestions_for(str(profile.get("industry") or ""), str(profile.get("stage") or ""))

    def text(name: str, label: str, *, area: bool = False) -> str:
        value = escape(str(profile.get(name) or ""))
        control = (
            f'<textarea name="{name}" {locked}>{value}</textarea>'
            if area
            else f'<input name="{name}" value="{value}" {locked}>'
        )
        return f"<label>{escape(label)}</label>{control}"

    def _suggested(name: str, label: str, *, area: bool = False) -> str:
        chips = []
        for example in examples.get(name) or []:
            shown = escape(example)
            if locked:
                chips.append(f'<span class="chip">{shown}</span>')
            else:
                chips.append(
                    f'<button type="button" class="chip" data-field="{escape(name)}" '
                    f'data-example="{shown}">{shown}</button>'
                )
        listing = "".join(chips)
        return (
            '<div class="field-suggest">'
            + text(name, label, area=area)
            + f'<div class="suggest" data-suggest="{escape(name)}">'
            + '<p class="muted">Examples only.</p>'
            + listing
            + "</div></div>"
        )

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
    if path == "existing":
        startup_note = (
            "This is an existing or expanding business. Startup-only cost-build questions "
            "are not on this path. The monthly engine inputs below are still required. "
            "Blank fields stay blank. Nothing has been filled in for you."
        )
    elif startup_missing:
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
    if path == "existing":
        capital = """
<p class="muted">Startup cost-build questions are not on this path. Construction cost, seats, occupancy, and the worksheet lines stay blank. The monthly engine still uses the four fields below.</p>
"""
    else:
        capital = f"""
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
"""
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
<p class="suggest-note" id="suggestion-note">{escape(SUGGESTION_NOTE)}</p>
{_suggested("stage", "Development stage")}
{_suggested("products", "Products and services", area=True)}
{_suggested("customers", "Target customers", area=True)}
{_suggested("competition", "Competition", area=True)}
{_suggestion_script(locked)}
</details>
<details id="demand-evidence" open>
<summary>Demand evidence</summary>
{choice("demand_evidence", "Is there demand evidence? A yes here is still only a user-supplied assumption.")}
{_verified_demand_fields(profile, locked)}
{choice("operator_capacity_adequate", "Is operator capacity adequate?")}
{choice("unresolved_regulatory_or_liability", "Is there an unresolved regulatory or liability issue?")}
{choice("extraction_without_reinvestment", "Do stewardship indicators show extraction without reinvestment?")}
</details>
{capital}
<details id="monthly-engine">
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


_SUGGESTION_SCRIPT = """
<script>
(function () {
  var catalogNode = document.getElementById("suggestion-catalog");
  if (!catalogNode) return;
  var catalog = JSON.parse(catalogNode.textContent);
  var fields = {
    stage: ["development_stages", "development_stages"],
    products: ["products_services", "fallback_products"],
    customers: ["target_customers", "fallback_customers"],
    competition: ["competition", "fallback_competition"]
  };
  var ranks = {name: 3, aliases: 2, keywords: 1};
  var allowed = {stage: true, products: true, customers: true, competition: true};

  function words(value) {
    var found = String(value || "").toLowerCase().match(/[a-z0-9]+/g);
    return found ? found.join(" ") : "";
  }
  function padded(value) {
    var text = words(value);
    return text ? " " + text + " " : "";
  }
  function matchIndustry(industry) {
    var haystack = padded(industry);
    if (!haystack) return null;
    var best = null;
    var bestScore = 0;
    (catalog.industries || []).forEach(function (record) {
      var groups = [
        ["name", [record.name]],
        ["aliases", record.aliases || []],
        ["keywords", record.keywords || []]
      ];
      groups.forEach(function (group) {
        group[1].forEach(function (phrase) {
          var needle = padded(phrase);
          if (needle && haystack.indexOf(needle) !== -1) {
            var score = needle.length * 10 + ranks[group[0]];
            if (score > bestScore) {
              best = record;
              bestScore = score;
            }
          }
        });
      });
    });
    return best;
  }
  function pick(record, pair) {
    var general = (catalog.general || {})[pair[1]] || [];
    var source = record && record[pair[0]];
    if (Object.prototype.toString.call(source) === "[object Array]" && source.length) return source;
    return general;
  }
  function render(box, examples) {
    var field = box.getAttribute("data-suggest");
    box.textContent = "";
    var note = document.createElement("p");
    note.className = "muted";
    note.textContent = "Examples only.";
    box.appendChild(note);
    examples.forEach(function (example) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "chip";
      button.setAttribute("data-field", field);
      button.setAttribute("data-example", example);
      button.textContent = example;
      box.appendChild(button);
    });
  }
  function refresh() {
    var industry = document.querySelector('[name="industry"]');
    var record = matchIndustry(industry ? industry.value : "");
    document.querySelectorAll("[data-suggest]").forEach(function (box) {
      var field = box.getAttribute("data-suggest");
      render(box, pick(record, fields[field]));
    });
  }
  document.addEventListener("click", function (event) {
    var chip = event.target.closest ? event.target.closest("button.chip") : null;
    if (!chip) return;
    var name = chip.getAttribute("data-field");
    if (!allowed[name]) return;
    var field = document.querySelector('[name="' + name + '"]');
    if (!field || field.disabled) return;
    field.value = chip.getAttribute("data-example") || "";
    var wrap = chip.closest ? chip.closest(".field-suggest") : null;
    if (wrap) wrap.classList.add("is-closed");
    field.blur();
    if (name === "stage") refresh();
  });
  document.addEventListener("mousedown", function (event) {
    var chip = event.target.closest ? event.target.closest("button.chip") : null;
    if (chip) event.preventDefault();
  });
  document.querySelectorAll(".field-suggest").forEach(function (wrap) {
    wrap.addEventListener("mouseleave", function () {
      wrap.classList.remove("is-closed");
    });
  });
  var industryField = document.querySelector('[name="industry"]');
  var stageField = document.querySelector('[name="stage"]');
  if (industryField) industryField.addEventListener("input", refresh);
  if (stageField) stageField.addEventListener("input", refresh);
  refresh();
})();
</script>
"""


def _suggestion_script(locked: str) -> str:
    if locked:
        return ""
    return (
        '<script type="application/json" id="suggestion-catalog">'
        + catalog_json()
        + "</script>"
        + _SUGGESTION_SCRIPT
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
<h2 id="verified-demand">Verified demand record</h2>
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


def results_page(
    record: dict[str, Any],
    result: dict[str, Any],
    notes: list[dict[str, Any]] | None = None,
) -> str:
    if not result.get("engine_ran"):
        body = _results_not_run(record, result, notes)
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
<p>This page shows the stored engine result, the hard gate, and the next step. It does not grant investor-ready status.</p>
{_pilot_banner(record)}
{_SURFACE_NOTE}
{_pilot_purpose()}
{_journey_progress(_journey_stage(record))}
<div class="banner">{escape(standing)}</div>
{_adviser_nudge(record, "results")}
<div class="card" id="results-lead">
{_at_a_glance(record, result)}
{_view_summary_block(result)}
{_indicative_block(result, notes)}
{_your_next_step(record)}
<p class="muted">Engine {escape(str(result.get('model_version')))}. Service tier on this file: {escape(record['tier'])}. Authoritative financial numbers below come only from the 0.1 engine.</p>
<div class="figure-block">
<h2>Key engine figures</h2>
<p>These are the stored engine figures. The sentence under a name explains it. The sentence does not change the number.</p>
<h2>Monthly base and downside</h2>{financial}
<h2>Sources and uses, scenarios, and DSCR</h2>
{_plain("sources_and_uses")}
{_plain("dscr")}
{projection}
</div>
</div>
{_draft_market_context(record)}
{links}
{_scenario_comparison(record, result)}
{_evidence_checklist(record, result, notes, return_to="results")}
{_assistant_panel(record, surface="results")}
{_analyst_panel(record, result)}
{_LIMITATIONS}
<h2>Demand evidence</h2>
{_demand_status(result.get("demand") or {})}
<h2>Recommend-against flags</h2>
{_plain("recommend_against")}
<ul>{flags}</ul>
<h2>Evidence gaps</h2><ul>{gaps}</ul>
<h2>Missing information</h2><ul>{missing}</ul>
{_guidance_section("explore" if str(record.get("tier")) == "explore" else "analyze", result, notes, record)}
{_tier_research(record, result)}
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
<a class="button" href="/assessments/{assessment_id}/audit/download">Download JSON audit</a>
<a class="button" href="/assessments/{assessment_id}/research">Download Research Package</a>
<a class="button" href="/assessments/{assessment_id}/research/markdown">Download research Markdown</a>
<a class="button" href="/assessments/{assessment_id}/research/brief">Research Brief</a>
<a class="button" href="/assessments/{assessment_id}/advisor">Advisor Summary</a>
<a class="button" href="/assessments/{assessment_id}/advisor/download">Download Advisor Package</a></p>
"""


def _results_not_run(
    record: dict[str, Any],
    result: dict[str, Any],
    notes: list[dict[str, Any]] | None = None,
) -> str:
    profile = record.get("profile") or {}
    startup_missing = _missing_labels(profile, _STARTUP_REQUIRED)
    monthly_missing = _missing_labels(profile, _MONTHLY_REQUIRED)
    message = str(result.get("message") or "Analyze has not been run.")
    details = ""
    if venture_path_of(record) != "existing" and startup_missing:
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
<p>This page says Analyze has not written a result yet. It does not invent a number and it does not grant investor-ready status.</p>
{_pilot_banner(record)}
{_SURFACE_NOTE}
{_pilot_purpose()}
{_draft_market_context(record)}
{_journey_progress("intake")}
{_adviser_nudge(record, "results")}
<div class="banner">{escape(message)} This page did not run the engine and did not fill any blank fields.</div>
{details}
{baseline}
{_evidence_checklist(record, result, notes, return_to="results")}
<div class="card">
<h2>What this means</h2>
<p><strong>What to do next:</strong> Return to the draft, fill the missing fields named above, save, and run Analyze. This page did not invent a number.</p>
</div>
{_assistant_panel(record, surface="results")}
<p class="muted">Scenario comparison is available after Analyze has been run. It does not change a recommendation or a hard gate.</p>
<p><a class="button" href="/assessments/{escape(record['id'])}">Return to the draft</a>
<a class="button" href="/assessments/{escape(record['id'])}/export">Export draft as JSON</a></p>
{_guidance_section("explore", notes=notes, record=record)}
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


def _indicative_block(result: dict[str, Any], notes: list[dict[str, Any]] | None = None) -> str:
    from app.indicative_score import indicative_score

    score = indicative_score(result, notes)
    components = score["components"]
    lines = []
    for key, item in (
        ("market_validity", components["market_validity"]),
        ("financial_viability", components["financial_viability"]),
        ("stewardship_readiness", components["stewardship_readiness"]),
    ):
        width = max(0, min(100, int(item["score"])))
        lines.append(
            "<li>"
            f"<strong>{escape(item['name'])}:</strong> {item['score']} of 100. "
            f"Weight {score['weights'][key]}."
            f'<div class="bar-track"><div class="bar" style="width: {width}%"></div></div>'
            "</li>"
        )
    rendered = "".join(lines)
    return f"""
<section class="indicative-score card">
<h2>Indicative assessment</h2>
<p><strong>{escape(score['label'])}</strong></p>
{_plain("indicative_score")}
<p><strong>Gate status:</strong> {escape(score['gate_status'])}</p>
<p><strong>Band:</strong> {escape(score['band'])}</p>
{_gate_gloss(str(score['gate_status']), str(score['band']))}
<p><strong>Gate recommendation:</strong> {escape(score['gate_recommendation'])}</p>
<ul>{rendered}</ul>
<p class="muted"><strong>Overall number (indicative only):</strong> {score['score']} of 100. This indicative number does not override a hard recommend-against flag and does not grant investor-ready status.</p>
<p>{escape(score['explanation'])}</p>
</section>
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
{_plain("recommendation")}
<p><strong>Score:</strong> {escape(result.get('score_line', ''))}</p>
{_plain("indicative_score")}
<p><strong>INSUFFICIENT_DEMAND_EVIDENCE:</strong> {escape(str(summary.get('insufficient_demand_evidence')))}</p>
{_plain("insufficient_demand_evidence")}
<p><strong>Investor readiness:</strong> {escape(str(summary.get('investor_readiness')))}</p>
{_plain("investor_readiness")}
<p><strong>Human review status:</strong> {escape(str(summary.get('human_review_status')))}</p>
<p><strong>human_review_approved:</strong> {approved}</p>
<p><strong>Demand evidence provenance:</strong></p>
<ul>{provenance}</ul>
"""


def _tier_research(record: dict[str, Any], result: dict[str, Any]) -> str:
    tier = str(record.get("tier") or "explore")
    if tier == "explore":
        return """
<h2>Research depth</h2>
<p>Explore lists the engine flags and missing fields above. Analyze adds Evidence Gaps, Key Assumptions, Risk Summary, and Suggested Next Research Steps. This note does not change a flag and it does not set human_review_approved.</p>
"""
    return _analyze_research(result, record)


def _analyze_research(result: dict[str, Any], record: dict[str, Any]) -> str:
    blocking = [str(flag) for flag in result.get("blocking_flags") or []]
    gap_flags = [str(flag) for flag in result.get("gap_flags") or []]
    missing = [str(item) for item in result.get("missing") or []]
    evidence = []
    if "INSUFFICIENT_DEMAND_EVIDENCE" in blocking:
        evidence.append(
            "INSUFFICIENT_DEMAND_EVIDENCE is an active engine flag. It is listed because the engine raised it."
        )
    evidence.extend(f"Engine gap flag: {flag}." for flag in gap_flags)
    evidence.extend(f"Engine missing field: {item}" for item in missing)
    if not evidence:
        evidence.append("The engine did not list a gap flag or a missing field on this result.")
    evidence_items = "".join(f"<li>{escape(line)}</li>" for line in evidence)
    assumptions = ((result.get("intake") or {}).get("assumptions") or [])
    if assumptions:
        assumption_items = "".join(
            "<li>"
            f"{escape(str(item.get('key') or 'assumption'))}: {escape(str(item.get('value')))}. "
            f"Source: {escape(str(item.get('source') or 'not recorded'))}. "
            f"{escape(str(item.get('rationale') or ''))}"
            "</li>"
            for item in assumptions
            if isinstance(item, dict)
        ) or "<li>No intake assumptions are attached to this result.</li>"
    else:
        assumption_items = "<li>No intake assumptions are attached to this result. None are invented.</li>"
    if blocking:
        risk_lines = [
            f"Active recommend-against flag: {flag}. The draft recommendation is {result.get('recommendation') or 'not loaded'}."
            for flag in blocking
        ]
    else:
        risk_lines = [
            "No recommend-against flag is active on this result. Gap flags remain unevaluated criteria."
        ]
    risk_lines.append(
        "This summary restates engine flags. It is not a new score and it does not clear a recommend-against flag."
    )
    risk_items = "".join(f"<li>{escape(line)}</li>" for line in risk_lines)
    steps = _research_steps(blocking, gap_flags, missing, record)
    step_items = "".join(f"<li>{escape(line)}</li>" for line in steps)
    return f"""
<h2>Evidence Gaps</h2>
<p>Derived from the engine flags and missing fields already on this result. No score is added.</p>
<ul>{evidence_items}</ul>
<h2>Key Assumptions</h2>
<p>These are the assumptions already stored on the intake. A customer entry is a user-supplied assumption, not verified data.</p>
<ul>{assumption_items}</ul>
<h2>Risk Summary</h2>
<ul>{risk_items}</ul>
<h2>Suggested Next Research Steps</h2>
<p>Each step restates an engine flag, a missing field, or the demonstration market snapshot. These steps are not a recommendation.</p>
<ul>{step_items}</ul>
"""


def _research_steps(
    blocking: list[str],
    gap_flags: list[str],
    missing: list[str],
    record: dict[str, Any],
) -> list[str]:
    from scoring.rules import NEXT_ACTIONS

    steps = []
    for flag in blocking + gap_flags:
        action = NEXT_ACTIONS.get(flag)
        if action:
            steps.append(f"{flag}: {action}")
        else:
            steps.append(f"The engine recorded {flag}. This page does not add a score for it.")
    for item in missing:
        steps.append(f"The engine listed this missing item: {item} This page does not fill it.")
    profile = record.get("profile") or {}
    snapshot = market_framework(profile.get("industry"), profile.get("market"))
    examples = snapshot.get("synthetic_examples") or []
    if examples:
        steps.append(
            "Market observation available on this page: "
            + " ".join(str(item) for item in examples)
            + " Live feed connected: false. These observations do not clear INSUFFICIENT_DEMAND_EVIDENCE."
        )
    else:
        steps.append(
            "No market observation is loaded. Live feed connected: false. No market fact is invented."
        )
    steps.append(
        "These steps do not set human_review_approved and do not change investor readiness."
    )
    return steps


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


def venture_path_of(record: dict[str, Any]) -> str:
    """Startup keeps the current Explore intake. Existing uses the shorter path."""
    business = record.get("business_profile") or {}
    profile = record.get("profile") or {}
    raw = str(business.get("venture_path") or profile.get("venture_path") or "startup")
    return raw if raw in {"startup", "existing"} else "startup"


def _missing_labels(profile: dict[str, Any], fields: tuple[tuple[str, str], ...]) -> list[str]:
    return [label for key, label in fields if not str(profile.get(key) or "").strip()]


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
<p class="muted">In everyday words: DSCR compares cash flow with debt service for that case. The number, when one is shown, comes from the engine. This sentence does not change it.</p>
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


def _scenario_comparison(record: dict[str, Any], result: dict[str, Any]) -> str:
    from app.scenarios import DISCLAIMER, METRIC_KEYS, METRIC_LABELS, blank_scenarios

    stored = record.get("scenarios") if isinstance(record.get("scenarios"), dict) else blank_scenarios()
    base = stored.get("base") if isinstance(stored.get("base"), dict) else None
    alternative = stored.get("alternative") if isinstance(stored.get("alternative"), dict) else None
    base_metrics = base.get("metrics") if base else {}
    alternative_metrics = alternative.get("metrics") if alternative else {}
    alternative_label = str(alternative.get("label")) if alternative else "Alternative"
    rows = []
    for key in METRIC_KEYS:
        left = _scenario_metric(base_metrics.get(key) if isinstance(base_metrics, dict) else None)
        right = _scenario_metric(
            alternative_metrics.get(key) if isinstance(alternative_metrics, dict) else None
        )
        if left == "not calculated" and right == "not calculated":
            continue
        rows.append(
            "<tr>"
            f"<td>{escape(METRIC_LABELS[key])}</td>"
            f"<td>{escape(left)}</td>"
            f"<td>{escape(right)}</td>"
            "</tr>"
        )
    if rows:
        table = (
            "<table>"
            f"<tr><th>Metric</th><th>Base</th><th>{escape(alternative_label)}</th></tr>"
            + "".join(rows)
            + "</table>"
        )
    elif base or alternative:
        table = "<p>The engine did not calculate a key metric for the saved cases.</p>"
    else:
        table = "<p>No Base case is saved.</p>"
    note = ""
    if alternative:
        note = f"<p class=\"muted\">{escape(str(alternative.get('note') or ''))}</p>"
    flags = [str(flag) for flag in result.get("blocking_flags") or []]
    if flags:
        gate_line = (
            "<p><strong>Official hard gates:</strong> "
            + escape(", ".join(flags))
            + ". This comparison did not clear them.</p>"
        )
    else:
        gate_line = "<p><strong>Official hard gates:</strong> none on this result. This comparison did not add or clear one.</p>"
    assessment_id = escape(str(record.get("id") or ""))
    return f"""
<section class="card" id="scenario-comparison">
<h2>Scenario comparison</h2>
<p>{escape(DISCLAIMER)}</p>
<p><strong>Official recommendation:</strong> {escape(str(result.get("recommendation") or "not loaded"))}. This comparison did not change it.</p>
{gate_line}
{table}
{note}
<form method="post" action="/assessments/{assessment_id}/scenarios">
<button type="submit" name="case" value="base">Save current result as Base</button>
<button type="submit" name="case" value="downside">Run Downside case</button>
<button type="submit" name="case" value="upside">Run Upside case</button>
</form>
<p class="muted">One alternative case is kept. Running Downside or Upside replaces the previous alternative. The official engine result stays in place.</p>
</section>
"""


def _scenario_metric(value: Any) -> str:
    if value is None:
        return "not calculated"
    return str(value)


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
    notes = {
        "base_monthly_contribution": "Money left in a typical month after the cost of what was sold, before fixed costs.",
        "base_monthly_cash_flow": "Cash left in a typical month after fixed costs.",
        "downside_monthly_cash_flow": "Cash left in a weaker month.",
        "break_even_monthly_revenue": "Monthly revenue the engine uses before that month covers its costs.",
        "months_to_break_even_base": "How many months the engine counts before the base case covers its costs.",
    }
    explained = "".join(
        f"<li><strong>{escape(key)}.</strong> {escape(sentence)} This sentence does not change the figure.</li>"
        for key, sentence in notes.items()
    )
    return f"<table>{rows}</table><ul class=\"figure-notes\">{explained}</ul>"


def assistant_page(record: dict[str, Any], lines: list[str], question: str = "") -> str:
    body = f"""
<h1>Ask about {escape(record['business_name'])}</h1>
{_SURFACE_NOTE}
<p class="muted">You asked: {escape(question or "a question about this assessment.")}</p>
{_assistant_panel(record, lines, surface="results" if (record.get("result") or {}).get("engine_ran") else "intake")}
<p><a class="button" href="/assessments/{escape(record['id'])}">Return to the draft</a>
<a class="button" href="/assessments/{escape(record['id'])}/results">Return to results</a></p>
"""
    return layout("Assistant", body)


def _objective_chooser() -> str:
    """Real starting choices. Each one posts to a workspace. None of them approve a file."""
    items = []
    for item in OBJECTIVES:
        items.append(
            "<li>"
            f'<form method="post" action="/start">'
            f'<input type="hidden" name="objective" value="{escape(item["id"])}">'
            f'<button type="submit">{escape(item["label"])}</button>'
            f'<p class="muted"><strong>{escape(item["availability"])}.</strong> {escape(item["note"])}</p>'
            "</form></li>"
        )
    return f"""
<section class="card" id="customer-objectives">
<h2>What would you like to accomplish with your business?</h2>
<p>Choose one. A signed-in account opens a workspace and keeps it. The choice does not grant investor-ready status and does not clear a flag.</p>
<ul class="objectives">{''.join(items)}</ul>
</section>
"""


def _explore_workspace(record: dict[str, Any]) -> str:
    """Conversation, approved notes, and the path into Analyze."""
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    objective = str((profile or {}).get("customer_objective") or "")
    if not objective or record.get("read_only"):
        return ""
    assessment_id = escape(str(record.get("id") or ""))
    messages = profile.get("adviser_messages") if isinstance(profile.get("adviser_messages"), list) else []
    rows = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = "you" if item.get("role") == "customer" else "adviser"
        who = "You" if role == "you" else "Adviser"
        rows.append(
            f'<li class="{role}"><strong>{who}:</strong> {escape(str(item.get("text") or ""))}</li>'
        )
    log = "".join(rows) or "<li>No messages yet.</li>"
    proposal = profile.get("adviser_proposal") if isinstance(profile.get("adviser_proposal"), dict) else None
    if proposal:
        decision = f"""
<form method="post" action="/assessments/{assessment_id}/adviser/apply">
<p><strong>Review before saving.</strong> {escape(str(proposal.get("label") or "Answer"))}: {escape(str(proposal.get("value") or ""))}</p>
<button type="submit" name="decision" value="save">Save this answer</button>
<button type="submit" name="decision" value="discard">Discard</button>
</form>
<p class="muted">Saving writes one user-supplied assumption. It does not clear a flag, run the engine, or set human_review_approved.</p>
"""
    else:
        decision = f"""
<form method="post" action="/assessments/{assessment_id}/adviser">
<label>Your reply</label>
<textarea name="message" maxlength="500" required></textarea>
<button type="submit">Send</button>
</form>
"""
    theme = THEMES.get(objective, ("Leave It Stronger", "This note is educational guidance, not a DVT evaluation and not a score."))
    saved_bits = []
    for key, label in (
        ("concept", "Business concept"),
        ("customers", "Target customers"),
        ("revenue_model", "Revenue model"),
        ("industry", "Industry"),
        ("market", "Geographic market"),
        ("competition", "Competition"),
    ):
        value = str(profile.get(key) or "").strip()
        saved_bits.append(f"<li><strong>{escape(label)}:</strong> {escape(value or 'not entered')}</li>")
    monthly = _missing_labels(profile, _MONTHLY_REQUIRED)
    monthly_line = (
        "Monthly fields still blank: " + ", ".join(monthly) + ". No figure is invented."
        if monthly
        else "The four monthly fields have text. They stay user-supplied until Analyze runs."
    )
    market_link = ""
    if objective == "research-market":
        market_link = '<p><a class="button" href="/market">Open Market Intelligence</a></p>'
    if objective == "monitor":
        market_link = '<p><a class="button" href="/market-pulse">Open Market Pulse</a></p><p class="muted">Monitoring is not active. This link does not retrieve a current finding.</p>'
    return f"""
<section class="card" id="adviser">
<h2>AI Business Adviser</h2>
<p>You chose {escape(objective_label(objective))}. {escape(ASSISTANCE_LABEL)}</p>
<p class="muted">Demonstration Adviser when ANALYST_PROVIDER is unset. A configured provider may add a reply. Neither one writes a field until you choose Save this answer. Streaming is not available in this local prototype.</p>
<ul class="adviser-log">{log}</ul>
{decision}
</section>
<section class="card" id="preliminary-assessment">
<h2>Preliminary notes</h2>
<p>These are the answers saved on this draft. They are not an engine result and they are not a feasibility score.</p>
<ul>{''.join(saved_bits)}</ul>
<p>{escape(monthly_line)}</p>
<p>Demand evidence stays missing until a verified record is saved on the intake. This page does not create that record.</p>
<p><strong>{escape(theme[0])}.</strong> {escape(theme[1])} Educational guidance — not a DVT evaluation. No pillar score is calculated.</p>
{market_link}
<p><a class="button primary" href="#monthly-engine">Continue to Analyze</a></p>
<p class="muted">Continue to Analyze moves you to the monthly fields. Run Analyze on this page when you want the engine to calculate. The adviser does not calculate a figure.</p>
</section>
"""


def _module_guide() -> str:
    """Name the modules a customer can open. It does not change a stored result."""
    return """
<details class="card" id="what-rugd-helps">
<summary>What can RUGD help with?</summary>
<h2>Available in this prototype</h2>
<ul>
<li>Explore intake for a startup idea or an existing business, including example phrases for the industry you type.</li>
<li>Analyze, which runs the deterministic engine. A hard recommend-against flag stays do-not-proceed.</li>
<li>An AI Business Adviser that explains the stored file. It cannot change a number, a flag, or an approval.</li>
<li>Advisor Summary, a read-only share, and optional public market extracts when one is requested. The source and the period stay visible.</li>
</ul>
<h2>Demonstration only</h2>
<ul>
<li>Validate can record a review request. It cannot approve an assessment.</li>
<li>Partner and Market Pulse are labeled demonstrations. Monitoring is not active.</li>
</ul>
<p class="muted">This guide does not grant investor-ready status.</p>
</details>
"""


def _adviser_nudge(record: dict[str, Any], surface: str) -> str:
    """One gap note. Dismissing it in the browser does not write the assessment."""
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    flags = [str(flag) for flag in (result or {}).get("blocking_flags") or []]
    assessment_id = str(record.get("id") or "")
    if surface == "results":
        demand_href = f"/assessments/{assessment_id}#verified-demand"
        monthly_href = f"/assessments/{assessment_id}#monthly-engine"
        intake_href = f"/assessments/{assessment_id}#intake"
    else:
        demand_href = "#verified-demand"
        monthly_href = "#monthly-engine"
        intake_href = "#intake"
    if "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
        text = "Demand evidence is still missing on this stored result. This note does not clear the flag."
        href, label = demand_href, "Open the verified demand record"
    else:
        monthly = _missing_labels(profile or {}, _MONTHLY_REQUIRED)
        if monthly:
            shown = ", ".join(monthly[:4])
            text = f"Monthly fields still blank: {shown}. This note does not invent a number."
            href, label = monthly_href, "Open the monthly fields"
        elif not (result or {}).get("engine_ran"):
            text = "Analyze has not been run. This note does not run the engine or fill a blank field."
            href, label = intake_href, "Open the intake"
        else:
            return ""
    key = escape(f"{assessment_id}:{surface}")
    return f"""
<aside class="card nudge" id="adviser-nudge" data-key="{key}">
<p><strong>A suggestion from the adviser.</strong> {escape(text)}</p>
<p><a class="button" href="{escape(href)}">{escape(label)}</a>
<button type="button" id="dismiss-nudge">Dismiss</button></p>
<p class="muted">Dismissing this note does not clear a flag or change a result.</p>
</aside>
<script>
(function () {{
  var node = document.getElementById("adviser-nudge");
  if (!node) return;
  var key = "rugd-nudge-" + (node.getAttribute("data-key") || "");
  try {{
    if (window.sessionStorage && sessionStorage.getItem(key) === "1") node.hidden = true;
  }} catch (err) {{}}
  var button = document.getElementById("dismiss-nudge");
  if (!button) return;
  button.addEventListener("click", function () {{
    node.hidden = true;
    try {{
      if (window.sessionStorage) sessionStorage.setItem(key, "1");
    }} catch (err) {{}}
  }});
}})();
</script>
"""


def _agent_workflow_card(record: dict[str, Any], surface: str) -> str:
    """Show the assistance stage. The card does not write a result."""
    flow = agent_workflow(record, surface=surface)
    order = [key for key, _label in flow["stages"]]
    index = order.index(flow["current"]) if flow["current"] in order else 0
    items = []
    for position, (key, label) in enumerate(flow["stages"]):
        if key == flow["current"]:
            marker = ' class="current" aria-current="step"'
        elif position < index:
            marker = ' class="done"'
        else:
            marker = ""
        items.append(f"<li{marker}>{escape(label)}</li>")
    assessment_id = escape(str(record.get("id") or ""))
    questions = "".join(
        f'<button type="submit" name="starter" value="{escape(question)}">{escape(question)}</button>'
        for question in flow["questions"]
    )
    return f"""
<section class="card" id="agent-workflow">
<h2>AI Business Adviser</h2>
<p>{escape(str(flow.get("welcome") or ""))}</p>
<p>Intake guidance, gap identification, results explanation, then a next-step recommendation. This workflow reads the stored file. It does not change a number, a flag, or an approval.</p>
<ol class="agent-flow">{''.join(items)}</ol>
<p><strong>Suggested next action:</strong> {escape(str(flow["action"]))}</p>
<p><a class="button" href="{escape(str(flow["href"]))}">{escape(str(flow["link_label"]))}</a></p>
<form method="post" action="/assessments/{assessment_id}/assistant">
{questions}
</form>
<p class="muted">{escape(ASSISTANCE_LABEL)}</p>
</section>
"""


def _assistant_panel(
    record: dict[str, Any],
    lines: list[str] | None = None,
    *,
    surface: str = "intake",
) -> str:
    assessment_id = escape(str(record.get("id") or ""))
    starters = "".join(
        f'<button type="submit" name="starter" value="{escape(question)}">{escape(question)}</button>'
        for question in STARTER_QUESTIONS
    )
    reply = ""
    if lines:
        items = "".join(f"<li>{escape(line)}</li>" for line in lines)
        reply = f'<div class="assistant-reply"><ul>{items}</ul></div>'
    else:
        reply = (
            '<p class="muted" id="assistant-empty">No question yet. '
            "Choose a starter or type a question about this assessment. "
            "The reply explains what is already stored, and it is not saved.</p>"
        )
    return _agent_workflow_card(record, surface) + f"""
<section class="card" id="assistant">
<h2>Ask about this assessment</h2>
<p>You can ask about this draft. The reply reads what is already stored. It does not change the assessment.</p>
<p>{escape(ASSISTANCE_LABEL)}</p>
<form method="post" action="/assessments/{assessment_id}/assistant">
<label>Your question</label>
<input name="question" maxlength="500">
<button type="submit">Ask</button>
<p class="muted">Start with one of these questions, or type your own.</p>
{starters}
</form>
{reply}
</section>
"""


def analyst_page(record: dict[str, Any], lines: list[str]) -> str:
    items = "".join(f"<li>{escape(line)}</li>" for line in lines)
    label = lines[0] if lines else "Demonstration Analyst"
    body = f"""
<h1>Analyst</h1>
{_SURFACE_NOTE}
<p class="muted">Service tier on this file: {escape(str(record.get('tier') or 'not recorded'))}. The analyst explanation is sourced commentary and is not authoritative.</p>
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
    tier: str | None = None,
) -> str:
    records = records or []
    selected = _tier_name(tier)
    if provider is None or getattr(provider, "name", None) == "synthetic":
        return _synthetic_market_page(records, industry, geographic_market, selected)
    view = load_market(industry, geographic_market, provider)
    view = {**view, "observations": _for_tier(list(view.get("observations") or []), selected)}
    if view["status"] == "public":
        return _public_market_page(records, industry, geographic_market, view, selected)
    return _fallback_market_page(records, industry, geographic_market, view, selected)


def _synthetic_market_page(
    records: list[dict[str, Any]],
    industry: str | None,
    geographic_market: str | None,
    tier: str,
) -> str:
    snapshot = market_framework(industry, geographic_market)
    implications = "".join(
        f"<li>{escape(line)}</li>" for line in assessment_implications(records, industry, geographic_market)
    )
    industry_options = _demo_options(DEMONSTRATION_INDUSTRIES, snapshot["industry"])
    geography_options = _demo_options(DEMONSTRATION_GEOGRAPHIES, snapshot["geographic_market"])
    view = _synthetic_view(snapshot)
    research = "" if tier == "explore" else _research_summary(view["observations"])
    shown = (
        f"<div class=\"banner\">{escape(snapshot['label'])}</div>"
        "<p>Live feed connected: false. Monitoring active: false. Source dataset: none.</p>"
        if tier == "explore"
        else _market_block(snapshot)
    )
    body = f"""
{_section_welcome(
    "Welcome to RUGD Market Intelligence",
    "This page shows a market snapshot for a place and an industry.",
    "The figures are a labeled demonstration unless a public extract was requested. They do not clear a flag.",
    demonstration="Market Intelligence (demonstration)",
)}
{_SURFACE_NOTE}
{_market_provenance_card(view)}
<div class="banner">Demonstration only. This page does not load a live market feed. Not live monitoring.</div>
{_plain("market_snapshot")}
<form method="get" action="/market">
<label>Demonstration industry</label>
<select name="industry">{industry_options}</select>
<label>Demonstration geographic market</label>
<select name="geographic_market">{geography_options}</select>
{_tier_select(tier)}
<button type="submit">Show demonstration selection</button>
</form>
<p class="muted">{_tier_note(tier)} The choices are labels for this demonstration. They are not a dataset and they do not describe a real market.</p>
{_market_summary(view, snapshot["industry"], snapshot["geographic_market"], tier)}
{research}
{shown}
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
    tier: str,
) -> str:
    industry_options = _demo_options(PUBLIC_INDUSTRIES, str(industry or "Not selected"))
    geography_options = _demo_options(PUBLIC_GEOGRAPHIES, str(geographic_market or "Not selected"))
    cards = "" if tier == "explore" else _observation_cards(view["observations"])
    research = "" if tier == "explore" else _research_summary(view["observations"])
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
{_section_welcome(
    "Welcome to RUGD Market Intelligence",
    "This page shows a market snapshot for a place and an industry.",
    "A public extract is shown only when one was requested. The figures do not clear a flag.",
)}
{_SURFACE_NOTE}
{_market_provenance_card(view)}
<div class="banner">{escape(view['label'])}</div>
{_plain("market_snapshot")}
<form method="get" action="/market">
<label>Industry</label>
<select name="industry">{industry_options}</select>
<label>Geographic coverage</label>
<select name="geographic_market">{geography_options}</select>
{_tier_select(tier)}
<button type="submit">Request public observations</button>
</form>
<p class="muted">{_tier_note(tier)} Optional public extract. {_active_provider(view)} Live feed connected: false. Monitoring active: false. This request does not change an assessment.</p>
<p class="muted">{_YEAR_NOTE}</p>
{_market_summary(view, industry, geographic_market, tier)}
{research}
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
    tier: str,
) -> str:
    snapshot = view["snapshot"]
    implications = "".join(
        f"<li>{escape(line)}</li>" for line in assessment_implications(records, industry, geographic_market)
    )
    industry_options = _demo_options(PUBLIC_INDUSTRIES, str(industry or snapshot["industry"]))
    geography_options = _demo_options(PUBLIC_GEOGRAPHIES, str(geographic_market or snapshot["geographic_market"]))
    body = f"""
{_section_welcome(
    "Welcome to RUGD Market Intelligence",
    "This page shows a market snapshot for a place and an industry.",
    "The figures are a labeled demonstration unless a public extract was requested. They do not clear a flag.",
    demonstration="Market Intelligence (demonstration)",
)}
{_SURFACE_NOTE}
{_market_provenance_card(view)}
<div class="banner">{escape(view['label'])}</div>
{_plain("market_snapshot")}
<form method="get" action="/market">
<label>Industry</label>
<select name="industry">{industry_options}</select>
<label>Geographic coverage</label>
<select name="geographic_market">{geography_options}</select>
{_tier_select(tier)}
<button type="submit">Request public observations</button>
</form>
<p class="muted">{_tier_note(tier)} {_active_provider(view)} A mapped industry and geography can request the public extract. Any other selection stays on the synthetic snapshot.</p>
<p class="muted">{_YEAR_NOTE}</p>
{_market_summary(view, industry, geographic_market, tier)}
{"" if tier == "explore" else _research_summary(view["observations"])}
{_market_block(snapshot)}
<h2>Implications for this assessment</h2>
<ul>{implications}</ul>
<p class="muted">These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag.</p>
"""
    return layout("Market Intelligence", body)


_YEAR_NOTE = (
    "The year is controlled by an environment variable. "
    "MARKET_YEAR selects the QCEW file. ACS_YEAR selects the ACS vintage. "
    "Each defaults to 2024 when it is not set. "
    "CBP_YEAR selects the County Business Patterns release and defaults to 2023. "
    "BEA_YEAR selects the Regional Economic Accounts year and defaults to 2024. "
    "A BEA request also needs BEA_USER_ID. The page does not show that id. "
    "LAUS_YEAR selects the unemployment annual average and defaults to 2024. "
    "This is prototype behavior."
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


def _market_provenance_card(view: dict[str, Any] | None = None) -> str:
    """Source, period, and limits sit above the figures. The card does not clear a flag."""
    view = view or {}
    observations = [item for item in view.get("observations") or [] if isinstance(item, dict)]
    first = observations[0] if observations else {}
    if str(view.get("status") or "") == "public" and first:
        source = str(first.get("source") or "Public extract")
        period = str(first.get("measurement_period") or "not recorded")
        limits = str(
            first.get("limitations")
            or "These figures do not clear a recommend-against flag."
        )
        extra = " Each figure below repeats its own source, period, and limits."
    else:
        source = "Synthetic demonstration. No Census, BLS, or BEA extract is loaded."
        period = "Not a public measurement period."
        limits = (
            "These figures do not clear a recommend-against flag "
            "and do not grant investor-ready status."
        )
        extra = ""
    return f"""
<section class="card" id="market-provenance">
<h2>Source, period, and limits</h2>
<p><strong>Source:</strong> {escape(source)}</p>
<p><strong>Period:</strong> {escape(period)}</p>
<p><strong>Limitations:</strong> {escape(limits)}{escape(extra)}</p>
</section>
"""


def _market_summary(
    view: dict[str, Any],
    industry: str | None,
    geographic_market: str | None,
    tier: str = "analyze",
) -> str:
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
        examples = list((view.get("snapshot") or {}).get("synthetic_examples") or [])
        if tier == "explore":
            examples = examples[:1]
        for example in examples:
            rows.append(f"<li>{escape(str(example))}</li>")
    if not rows:
        rows.append("<li>No observations are loaded.</li>")
    query = urlencode(
        {
            "industry": str(industry or ""),
            "geographic_market": str(geographic_market or ""),
            "tier": tier,
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
        "census-cbp": "U.S. Census Bureau, County Business Patterns",
        "bea-regional": "U.S. Bureau of Economic Analysis, Regional Economic Accounts",
        "bls-laus": "BLS Local Area Unemployment Statistics",
    }
    label = labels.get(name, name or "public market provider")
    return f"Active provider: {escape(label)}. Year: {escape(year or 'not set')}."


def _tier_select(tier: str) -> str:
    labels = (
        ("explore", "Explore (limited snapshot)"),
        ("analyze", "Analyze (full view and summary)"),
        ("validate", "Validate (extended metrics)"),
        ("partner", "Partner (extended metrics)"),
    )
    options = "".join(
        f'<option value="{key}"{" selected" if key == tier else ""}>{escape(label)}</option>'
        for key, label in labels
    )
    return f"<label>Market view</label><select name=\"tier\">{options}</select>"


def _tier_note(tier: str) -> str:
    notes = {
        "explore": (
            "Explore shows a limited snapshot: headline employment, population, median household income, "
            "establishment count, current-dollar GDP, personal income, and the unemployment rate "
            "when a public source published them."
        ),
        "analyze": (
            "Analyze shows the full current market view and the Market Research Summary. "
            "Extended trend and distribution metrics stay on Validate and Partner."
        ),
        "validate": "Validate shows the full view, the Market Research Summary, and extended metrics.",
        "partner": (
            "Partner shows the same market view as Validate, including extended metrics. "
            "Recurring monitoring is not active."
        ),
    }
    return notes.get(tier, notes["analyze"])


def _research_summary(observations: list[dict[str, str]]) -> str:
    groups: list[tuple[str, list[dict[str, str]]]] = []
    for item in observations:
        source = str(item.get("source") or "")
        if not groups or groups[-1][0] != source:
            groups.append((source, []))
        groups[-1][1].append(item)
    lines = []
    for source, rows in groups:
        parts = [
            f"{row.get('measure')} is {row.get('value')} ({row.get('measurement_period')})"
            for row in rows
        ]
        lines.append(f"From {source}: " + "; ".join(parts) + ".")
    for row in observations:
        measure = str(row.get("measure") or "")
        if "change" not in measure.lower() or str(row.get("value") or "") == "Not disclosed":
            continue
        direction = _trend_direction(str(row.get("value") or ""))
        if not direction:
            continue
        lines.append(
            f"Trend direction for {measure}: {direction}. "
            f"Source: {row.get('source')}. Measurement period: {row.get('measurement_period')}."
        )
    if not lines:
        lines.append(
            "No public observation is cited for this selection. Any examples on this page are a synthetic snapshot."
        )
    body = "".join(f"<p>{escape(line)}</p>" for line in lines)
    return (
        "<h2>Market Research Summary</h2>"
        "<p>This overview is derived from the cited public sources in this section. "
        "It is not a recommendation. It does not clear INSUFFICIENT_DEMAND_EVIDENCE "
        "or any other recommend-against flag, and it does not set human_review_approved.</p>"
        f"{body}"
    )


def _trend_direction(value: str) -> str:
    token = value.strip().split(" ", 1)[0].replace(",", "")
    try:
        number = float(token)
    except ValueError:
        return ""
    if number > 0:
        return "higher than the prior period"
    if number < 0:
        return "lower than the prior period"
    return "unchanged from the prior period"


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
    notes: list[dict[str, Any]] | None = None,
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
{_indicative_block(result, notes)}
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


def validate_page(
    record: dict[str, Any] | None, notes: list[dict[str, Any]] | None = None
) -> str:
    if record is None:
        body = (
            _section_welcome(
                "Welcome to RUGD Validate",
                "This page shows how a human review request looks.",
                "You can ask for a review. This demonstration cannot approve an assessment or set human_review_approved.",
                demonstration="Validate (demonstration)",
            )
            + _SURFACE_NOTE
            + "<div class=\"banner\">Demonstration only. Customers can request review. "
            "This screen cannot set human_review_approved. Not live monitoring.</div>"
            + "<p>Open an assessment from My Assessments to request a review.</p>"
            + f"{_review_package(None)}"
            + f"{_guidance_section('demonstration')}"
        )
        return layout("Validate", body)
    requested = "A review has been requested." if record["review_requested"] else "No review has been requested."
    body = f"""
{_section_welcome(
    "Welcome to RUGD Validate",
    "This page shows how a human review request looks.",
    "You can ask for a review. This demonstration cannot approve an assessment or set human_review_approved.",
    demonstration="Validate (demonstration)",
)}
{_SURFACE_NOTE}
<div class="banner">Demonstration only. Customers can request review. This screen cannot set human_review_approved. Not live monitoring. Prototype-grade review request.</div>
<p>{escape(record['business_name'])}: {escape(requested)}</p>
<p><strong>Human review status:</strong> pending</p>
<p>Human review status stays pending on this customer screen. Requesting a review does not approve it. Investor readiness stays on the existing gate.</p>
{_review_package(record)}
{_guidance_section("demonstration", (record or {}).get("result"), notes, record)}
<form method="post" action="/assessments/{escape(record['id'])}/review-request">
<button type="submit">Request review</button>
</form>
<p class="muted">Approval stays on the reviewer screen. This customer screen cannot set human_review_approved.</p>
"""
    return layout("Validate", body)


def _review_package(record: dict[str, Any] | None) -> str:
    result = (record or {}).get("result") or {}
    profile = (record or {}).get("profile") or {}
    blocking = [str(flag) for flag in result.get("blocking_flags") or []]
    gap_flags = [str(flag) for flag in result.get("gap_flags") or []]
    missing = [str(item) for item in result.get("missing") or []]
    flag_items = "".join(f"<li class=\"flag\">{escape(flag)}</li>" for flag in blocking) or "<li>None loaded</li>"
    gap_items = "".join(f"<li>{escape(flag)}</li>" for flag in gap_flags) or "<li>None listed</li>"
    missing_items = "".join(f"<li>{escape(item)}</li>" for item in missing) or "<li>None listed</li>"
    snapshot = market_framework(profile.get("industry"), profile.get("market"))
    examples = "".join(f"<li>{escape(str(item))}</li>" for item in snapshot.get("synthetic_examples") or [])
    return f"""
<h2>Review Package</h2>
<p>Prototype review package. Not an approval. This summary does not set human_review_approved and it does not clear a recommend-against flag.</p>
<h3>Current flags</h3>
<ul>{flag_items}</ul>
<h3>Market context</h3>
<p>{escape(str(snapshot.get('label')))} Industry: {escape(str(snapshot.get('industry')))}. Geographic market: {escape(str(snapshot.get('geographic_market')))}.</p>
<p>Live feed connected: false. Monitoring active: false. Source dataset: none.</p>
<ul>{examples}</ul>
<p>These observations do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag.</p>
<h3>Evidence gaps</h3>
<ul>{gap_items}</ul>
<ul>{missing_items}</ul>
<h3>Reviewer notes</h3>
<p>Reviewer notes placeholder. No reviewer note is stored. This placeholder is not an approval.</p>
"""


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
        if signed_in or expired or _has_account(session):
            control += _reviewer_sign_out_form(next_path)
    elif signed_in:
        control = f"""
<form method="post" action="/reviewer/assessments/{escape(record['id'])}/approve">
<button type="submit">Record reviewer approval</button>
</form>
{_reviewer_sign_out_form(next_path)}
"""
    elif _has_account(session):
        control = (
            "<p>This account cannot record approval. Customer role is not a reviewer.</p>"
            + _reviewer_sign_out_form(next_path)
        )
    else:
        control = _reviewer_sign_in_form(next_path)
        if expired:
            control += _reviewer_sign_out_form(next_path)
    body = f"""
<h1>Reviewer control</h1>
<div class="banner">Reviewer control. Not a customer feature. Prototype-grade local session. Local account required. This is not production authentication.</div>
{_SURFACE_NOTE}
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
    if signed_in:
        form = (
            '<p><a href="/reviewer/accounts">Create a reviewer account</a></p>'
            + _reviewer_sign_out_form("/reviewer")
        )
    elif _has_account(session):
        form = (
            "<p>This account cannot record approval. Customer role is not a reviewer.</p>"
            + _reviewer_sign_out_form("/reviewer")
        )
    else:
        form = _reviewer_sign_in_form("/reviewer")
        if expired:
            form += _reviewer_sign_out_form("/reviewer")
    return layout(
        "Reviewer",
        f"""
<h1>Reviewer</h1>
<div class="banner">Local account required. Not a customer feature. Not production authentication.</div>
{_SURFACE_NOTE}
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


def _has_account(session: dict[str, Any] | None) -> bool:
    session = session or {}
    return bool(session.get("active")) and str(session.get("role") or "") == "customer"


def _session_status(session: dict[str, Any] | None) -> tuple[str, bool, bool, str]:
    session = session or {}
    state_name = str(session.get("state") or "")
    role = str(session.get("role") or "")
    active = bool(session.get("active")) and state_name != "expired"
    expired = state_name == "expired"
    if active and role == "reviewer":
        label = (
            f"signed in as {session.get('reviewer_identity')} "
            f"({session.get('authentication_method')}, role reviewer). "
            f"Remaining lifetime: {_format_remaining(session.get('remaining_seconds'))}."
        )
        return label, True, False, "signed in"
    if active and role == "customer":
        label = (
            f"signed in as {session.get('reviewer_identity')} "
            f"({session.get('authentication_method')}, role customer). "
            "This account cannot approve."
        )
        return label, False, False, "signed in"
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
<form method="post" action="/logout">
<input type="hidden" name="next" value="{escape(next_path)}">
<button type="submit">Log out</button>
</form>
<p class="muted">Local sign-out. Not a customer approval control. Not production authentication.</p>
"""


def _reviewer_sign_in_form(next_path: str) -> str:
    return f"""
<form method="post" action="/login">
<input type="hidden" name="next" value="{escape(next_path)}">
<label>Email</label>
<input name="email" type="email" autocomplete="username" required>
<label>Password</label>
<input name="password" type="password" autocomplete="current-password" required>
<button type="submit">Log in</button>
</form>
<p class="muted"><a href="/register">Register</a>. Self-registration creates a customer account. It does not create a reviewer. Not production authentication.</p>
<p class="muted"><a href="/forgot-password">Forgot password</a></p>
"""


def login_page(next_path: str = "/", message: str = "", objective: str = "") -> str:
    from app.objectives import objective_by_id

    notice = f"<p class=\"flag\">{escape(message)}</p>" if message else ""
    spec = objective_by_id(objective)
    hidden = f'<input type="hidden" name="objective" value="{escape(spec["id"])}">' if spec else ""
    chosen = (
        f"<p>Sign in to open <strong>{escape(spec['label'])}</strong>. "
        "This does not grant investor-ready status.</p>"
        if spec
        else ""
    )
    body = f"""
<h1>Login</h1>
{_SURFACE_NOTE}
<div class="banner">Local pilot account. Not production authentication. This screen does not grant investor-ready status.</div>
{notice}
{chosen}
<form method="post" action="/login">
<input type="hidden" name="next" value="{escape(next_path)}">
{hidden}
<label>Email</label>
<input name="email" type="email" autocomplete="username" required>
<label>Password</label>
<input name="password" type="password" autocomplete="current-password" required>
<button type="submit">Log in</button>
</form>
<p class="muted"><a href="/register">Register a customer account</a>. Self-registration cannot create a reviewer.</p>
<p class="muted"><a href="/forgot-password">Forgot password</a></p>
"""
    return layout("Login", body)


def verification_banner() -> str:
    return """
<div class="card" id="email-unverified">
<div class="banner">Your email is not verified. You can keep using this account. Verification does not change your role and does not grant investor-ready status.</div>
<form method="post" action="/account/verification">
<button type="submit">Send verification email again</button>
</form>
</div>
"""


def forgot_password_page(message: str = "") -> str:
    notice = f"<p>{escape(message)}</p>" if message else ""
    body = f"""
<h1>Forgot password</h1>
{_SURFACE_NOTE}
<div class="banner">Local pilot account. Not production authentication. This screen does not grant investor-ready status.</div>
<p>Enter the email on the account. If it is registered, a reset link is sent. The link expires in one hour. It does not change your role.</p>
{notice}
<form method="post" action="/forgot-password">
<label>Email</label>
<input name="email" type="email" autocomplete="username" required>
<button type="submit">Send reset link</button>
</form>
<p class="muted"><a href="/login">Log in</a></p>
"""
    return layout("Forgot password", body)


def reset_password_page(token: str, message: str = "") -> str:
    notice = f"<p class=\"flag\">{escape(message)}</p>" if message else ""
    body = f"""
<h1>Reset password</h1>
{_SURFACE_NOTE}
<div class="banner">Local pilot account. Not production authentication. This screen does not grant investor-ready status.</div>
<p>Choose a new password. This does not change your role, approve an assessment, or grant investor-ready status.</p>
{notice}
<form method="post" action="/account/reset">
<input type="hidden" name="token" value="{escape(token)}">
<label>New password</label>
<input name="password" type="password" autocomplete="new-password" required>
<label>Confirm password</label>
<input name="password_confirm" type="password" autocomplete="new-password" required>
<button type="submit">Update password</button>
</form>
"""
    return layout("Reset password", body)


def verify_email_page(message: str) -> str:
    body = f"""
<h1>Verify email</h1>
{_SURFACE_NOTE}
<div class="banner">Local pilot account. Not production authentication. This screen does not grant investor-ready status.</div>
<p>{escape(message)}</p>
<p class="muted"><a href="/login">Log in</a></p>
"""
    return layout("Verify email", body)


def register_page(message: str = "") -> str:
    notice = f"<p class=\"flag\">{escape(message)}</p>" if message else ""
    body = f"""
<h1>Register</h1>
{_SURFACE_NOTE}
<div class="banner">Local pilot registration. Passwords are stored as a scrypt hash. This is not production authentication.</div>
<p>Self-registration creates a customer account. It does not create a reviewer, it does not change an existing role, and it does not grant investor-ready status. A customer account cannot set human_review_approved.</p>
{notice}
<form method="post" action="/register">
<label>Email</label>
<input name="email" type="email" autocomplete="username" required>
<label>Password</label>
<input name="password" type="password" autocomplete="new-password" required>
<label>Confirm password</label>
<input name="password_confirm" type="password" autocomplete="new-password" required>
<button type="submit">Create customer account</button>
</form>
<p class="muted"><a href="/login">Log in</a></p>
"""
    return layout("Register", body)


def reviewer_accounts_page(message: str = "") -> str:
    notice = f"<p class=\"flag\">{escape(message)}</p>" if message else ""
    body = f"""
<h1>Create a reviewer account</h1>
{_SURFACE_NOTE}
<div class="banner">Reviewer control. Not a customer feature. Not production authentication. This screen does not grant investor-ready status.</div>
<p>An existing reviewer can create another reviewer account. This does not change a customer account into a reviewer. It does not approve an assessment, clear a flag, or set human_review_approved.</p>
{notice}
<form method="post" action="/reviewer/accounts">
<label>Email</label>
<input name="email" type="email" autocomplete="username" required>
<label>Password</label>
<input name="password" type="password" autocomplete="new-password" required>
<label>Confirm password</label>
<input name="password_confirm" type="password" autocomplete="new-password" required>
<button type="submit">Create reviewer account</button>
</form>
"""
    return layout("Reviewer accounts", body)


def logout_page(session: dict[str, Any] | None = None) -> str:
    state, _signed_in, _expired, status_word = _session_status(session)
    body = f"""
<h1>Log out</h1>
{_SURFACE_NOTE}
<div class="banner">Local pilot session. Not production authentication. Logging out does not change an assessment.</div>
<p><strong>Authentication state:</strong> {escape(state)}</p>
<p><strong>Current session status:</strong> {escape(status_word)}</p>
<form method="post" action="/logout">
<input type="hidden" name="next" value="/">
<button type="submit">Log out</button>
</form>
"""
    return layout("Log out", body)


def partner_page() -> str:
    body = f"""
{_section_welcome(
    "Welcome to RUGD Partner",
    "This page shows the partner view for an established business.",
    "Monitoring is not running. This demonstration does not change a recommendation.",
    demonstration="Partner (demonstration)",
)}
{_SURFACE_NOTE}
<div class="banner">Demonstration dashboard. Recurring monitoring is not active. Recurring monitoring has not been implemented. Not live monitoring.</div>
<div class="card">
<p>Partner is the planned tier for an established business that needs ongoing intelligence. A startup feasibility assessment is not required to enter this tier later.</p>
<p>No scheduled market, financial, or risk monitor is running. Monitoring active: false.</p>
</div>
{_ongoing_intelligence(market_framework())}
{_market_pulse_section()}
{_guidance_section("demonstration")}
{_market_block(market_framework())}
"""
    return layout("Partner", body)


def market_pulse_page() -> str:
    body = f"""
{_section_welcome(
    "Welcome to RUGD Market Pulse",
    "This page shows example monitoring cards.",
    "Monitoring is not active. The cards do not change an assessment.",
    demonstration="Market Pulse (demonstration)",
)}
{_SURFACE_NOTE}
{_market_pulse_section()}
"""
    return layout("Market Pulse", body)


def _market_pulse_section() -> str:
    from app.market_pulse import market_pulse

    pulse = market_pulse()
    cards = {"internal": [], "external": []}
    for card in pulse["cards"]:
        pillars = "".join(
            f"<li>Educational pillar label: {escape(str(label))}. {escape(str(card['pillar_label_note']))}</li>"
            for label in card.get("pillar_labels") or []
        )
        side = str(card.get("side") or "external")
        cards.setdefault(side, []).append(
            f"""
<article class="card">
<h3>{escape(str(card.get('title') or ''))}</h3>
<p>{escape(side.title())} example.</p>
<p><strong>{escape(str(card.get('label') or pulse['label']))}</strong></p>
<p>{escape(str(card.get('example') or ''))}</p>
<ul>{pillars}</ul>
</article>
"""
        )
    questions = "".join(f"<li>{escape(str(question))}</li>" for question in pulse["questions"])
    internal = "".join(cards.get("internal") or []) or "<p>No internal example is loaded.</p>"
    external = "".join(cards.get("external") or []) or "<p>No external example is loaded.</p>"
    return f"""
<h2>Market Pulse</h2>
<div class="banner">{escape(str(pulse['label']))}</div>
<p>Monitoring active: false. Live feed connected: false. Scheduled jobs: none. Connectors: none. Notifications: none.</p>
<p>No scheduled job is running. No connector is configured. No notification is sent. Recurring monitoring is not active.</p>
<h3>Internal examples</h3>
{internal}
<h3>External examples</h3>
{external}
<h3>Actionable recommendation questions</h3>
<p>Static template. These questions are not answers. They are not a recommendation. They do not clear a recommend-against flag and they do not set human_review_approved.</p>
<ol>{questions}</ol>
"""


def _ongoing_intelligence(snapshot: dict[str, Any]) -> str:
    alerts = []
    actions = []
    for example in snapshot.get("synthetic_examples") or []:
        text = str(example)
        alerts.append(
            f"Hypothetical trend alert. {text} Inactive demonstration. Not a live alert."
        )
        actions.append(
            "Hypothetical management action: read this synthetic note before changing a plan. "
            f"{text} This is not a recommendation. It does not clear a flag and it does not set human_review_approved."
        )
    if not alerts:
        alerts.append("Hypothetical trend alert. No synthetic example is loaded. Monitoring is not active.")
        actions.append(
            "Hypothetical management action: do not treat an empty snapshot as a finding. Monitoring is not active."
        )
    alert_items = "".join(f"<li>{escape(item)}</li>" for item in alerts)
    action_items = "".join(f"<li>{escape(item)}</li>" for item in actions)
    return f"""
<h2>Ongoing Intelligence</h2>
<div class="banner">Ongoing Intelligence is a demonstration panel. Inactive. Recurring monitoring is not active. Recurring monitoring has not been implemented. Monitoring active: false.</div>
<h3>Sample trend alerts</h3>
<ul>{alert_items}</ul>
<h3>Hypothetical management actions</h3>
<ul>{action_items}</ul>
"""


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


def advisor_summary_page(
    package: dict[str, Any],
    *,
    printable: bool = False,
    link_base: str = "",
    active: str = "",
    review_requested: bool = False,
) -> str:
    """Render the advisor package. The package is already a copy and this view does not save it."""
    assessment = package.get("assessment") or {}
    indicative = package.get("indicative") or {}
    market = package.get("market_snapshot") or {}
    provenance = market.get("provenance") or {}
    durable = package.get("durable_value") or {}
    if indicative:
        components = indicative.get("components") or {}
        rows = []
        for key in ("market_validity", "financial_viability", "stewardship_readiness"):
            item = components.get(key) or {}
            width = max(0, min(100, int(item.get("score") or 0)))
            weight = (indicative.get("weights") or {}).get(key, "")
            rows.append(
                "<li>"
                f"<strong>{escape(str(item.get('name') or ''))}:</strong> {escape(str(item.get('score')))} of 100. "
                f"Weight {escape(str(weight))}."
                f'<div class="bar-track"><div class="bar" style="width: {width}%"></div></div>'
                "</li>"
            )
        score_block = f"""
<p><strong>{escape(str(indicative.get('label') or ''))}</strong></p>
<p><strong>Gate status:</strong> {escape(str(indicative.get('gate_status') or ''))}</p>
<p><strong>Band:</strong> {escape(str(indicative.get('band') or ''))}</p>
{_gate_gloss(str(indicative.get('gate_status') or ''), str(indicative.get('band') or ''))}
<p><strong>Gate recommendation:</strong> {escape(str(indicative.get('gate_recommendation') or ''))}</p>
<ul>{''.join(rows)}</ul>
<p class="muted"><strong>Overall number (indicative only):</strong> {escape(str(indicative.get('score')))} of 100</p>
"""
    else:
        score_block = """
<p><strong>Gate status:</strong> Not run</p>
<p><strong>Band:</strong> Not run</p>
<p>Indicative assessment is shown after Analyze has been run. No feasibility score is calculated.</p>
"""
    flags = package.get("key_flags") or []
    flag_list = "".join(f'<li class="flag">{escape(str(flag))}</li>' for flag in flags) or "<li>None</li>"
    examples = "".join(
        f"<li>{escape(str(line))}</li>" for line in market.get("synthetic_examples") or []
    ) or "<li>None</li>"
    note_rows = []
    for item in durable.get("notes") or []:
        note_rows.append(
            "<li>"
            f"<strong>{escape(str(item.get('pillar_title') or ''))}:</strong> "
            f"{escape(str(item.get('note') or ''))}"
            "</li>"
        )
    notes = "".join(note_rows) or "<li>No educational note is stored.</li>"
    downloads = ""
    if link_base and not printable:
        downloads = f"""
<p class="no-print"><a class="button" href="{escape(link_base)}/download">Download Advisor Package</a>
<a class="button" href="{escape(link_base)}/print">Printable Advisor Package</a></p>
"""
    share_note = ""
    if active == "none":
        share_note = (
            '<div class="banner">Read-only share. This Advisor Summary cannot edit the assessment, '
            "request review, or approve it. It does not grant investor-ready status.</div>"
        )
    body = f"""
<div class="advisor-page">
<h1>Advisor Summary</h1>
<p>This page is a one-page reading of the stored file for a pilot review. It cannot approve the assessment.</p>
{downloads}
{_SURFACE_NOTE}
{_pilot_purpose()}
{_journey_progress(_journey_stage(package.get("assessment") or {}, review_requested=review_requested))}
<div class="banner">{_draft_label(assessment)}{escape(str(package.get('prototype_disclaimer') or ''))}</div>
{share_note}
{_advisor_glance(assessment, indicative)}
<div class="card" id="advisor-sheet">
<p><strong>Business:</strong> {escape(str(assessment.get('business_name') or ''))}</p>
<p><strong>Stored recommendation:</strong> {escape(str(assessment.get('recommendation')))}</p>
<p><strong>Score:</strong> {escape(str(assessment.get('score_line') or ''))}</p>
<p><strong>Investor readiness:</strong> {escape(str(assessment.get('readiness_status')))}</p>
<p><strong>Human review status:</strong> {escape(str(assessment.get('human_review_status')))}</p>
<p><strong>human_review_approved:</strong> {"true" if assessment.get("human_review_approved") else "false"}</p>
<p class="muted">{escape(str(assessment.get('status_source') or ''))}</p>
</div>
<h2>Indicative assessment</h2>
{score_block}
<h2>Key flags</h2>
<ul>{flag_list}</ul>
<h2>Market snapshot</h2>
<section class="card" id="market-provenance">
<h2>Source, period, and limits</h2>
<p><strong>Source:</strong> {escape(str(provenance.get('source') or 'none'))}</p>
<p><strong>Period:</strong> {escape(str(provenance.get('measurement_period') or 'not recorded'))}</p>
<p><strong>Limitations:</strong> {escape(str(provenance.get('limitations') or 'These figures do not clear a recommend-against flag.'))}</p>
</section>
<p><strong>Industry:</strong> {escape(str(market.get('industry') or ''))}</p>
<p><strong>Geography:</strong> {escape(str(market.get('geography') or ''))}</p>
<p><strong>Stage:</strong> {escape(str(market.get('stage') or ''))}</p>
<p>{escape(str(market.get('label') or ''))} Live feed connected: false. Monitoring active: false.</p>
<ul>{examples}</ul>
<p>{escape(str(provenance.get('limitations') or ''))}</p>
<h2>Durable Value notes</h2>
<p><strong>{escape(str(durable.get('label') or ''))}</strong></p>
<ul>{notes}</ul>
<h2>Provenance</h2>
<p><strong>Status source:</strong> {escape(str(assessment.get('status_source') or ''))}</p>
<p><strong>Market source:</strong> {escape(str(provenance.get('source') or 'none'))}</p>
<p><strong>Geographic coverage:</strong> {escape(str(provenance.get('geographic_coverage') or ''))}</p>
<p><strong>Industry classification:</strong> {escape(str(provenance.get('industry_classification') or ''))}</p>
<p><strong>Measurement period:</strong> {escape(str(provenance.get('measurement_period') or ''))}</p>
<p><strong>Retrieval date:</strong> {escape(str(provenance.get('retrieval_date') or ''))}</p>
<p><strong>Limitations:</strong> {escape(str(provenance.get('limitations') or ''))}</p>
<p>Educational notes are not engine inputs. This view does not change the stored assessment.</p>
{_LIMITATIONS}
</div>
"""
    return layout("Advisor Summary", body, printable=printable, active=active)


def research_brief_page(package: dict[str, Any]) -> str:
    summary = package.get("assessment_summary") or {}
    engine = package.get("engine_results") or {}
    flags = package.get("flags") or {}
    market = package.get("market") or {}
    blocking = "".join(f"<li class=\"flag\">{escape(str(flag))}</li>" for flag in flags.get("blocking_flags") or []) or "<li>None listed</li>"
    gaps = "".join(f"<li>{escape(str(item))}</li>" for item in package.get("evidence_gaps") or []) or "<li>None listed</li>"
    observations = list(market.get("observations") or []) + list(market.get("synthetic_observations") or [])
    if observations:
        cited = []
        for item in observations:
            cited.append(
                "<li>"
                f"<strong>{escape(str(item.get('measure') or ''))}:</strong> {escape(str(item.get('value') or ''))}. "
                f"Source: {escape(str(item.get('source') or ''))}. "
                f"Geographic coverage: {escape(str(item.get('geographic_coverage') or ''))}. "
                f"Classification: {escape(str(item.get('industry_classification') or ''))}. "
                f"Measurement period: {escape(str(item.get('measurement_period') or ''))}. "
                f"Retrieval date: {escape(str(item.get('retrieval_date') or ''))}. "
                f"Limitations: {escape(str(item.get('limitations') or ''))}."
                "</li>"
            )
        market_list = "".join(cited)
    else:
        market_list = "<li>No market observation is attached. No market fact is invented.</li>"
    analyst = "".join(f"<li>{escape(str(line))}</li>" for line in package.get("analyst_explanation") or []) or "<li>Analyst explanation is not available.</li>"
    body = f"""
<h1>Research Brief</h1>
<p class="no-print">Print-friendly research brief. Use the browser print dialog. This view does not change the assessment.</p>
{_SURFACE_NOTE}
<div class="banner">{escape(str(package.get('prototype_disclaimer') or ''))}</div>
<p><strong>Business:</strong> {escape(str(summary.get('business_name') or ''))}</p>
<p><strong>Tier:</strong> {escape(str(package.get('tier') or ''))}. {escape(str(package.get('tier_disclaimer') or ''))}</p>
<h2>Assessment summary</h2>
<p><strong>Recommendation:</strong> {escape(str(summary.get('recommendation')))}</p>
<p><strong>Investor readiness:</strong> {escape(str(summary.get('readiness_status')))}</p>
<p><strong>Human review status:</strong> {escape(str(summary.get('human_review_status')))}</p>
<p><strong>human_review_approved:</strong> {"true" if summary.get("human_review_approved") else "false"}</p>
<p><strong>Score line:</strong> {escape(str(engine.get('score_line') or ''))}</p>
<h2>Flags</h2>
<ul>{blocking}</ul>
<h2>Evidence gaps</h2>
<ul>{gaps}</ul>
<h2>Market observations</h2>
<p>{escape(str(market.get('label') or 'No public market provider is attached.'))}</p>
<ul>{market_list}</ul>
<p>Source citations are the source, coverage, period, retrieval date, and limitations on each observation. These figures do not clear a recommend-against flag.</p>
<h2>Analyst explanation</h2>
<ul>{analyst}</ul>
<section class="limitations">
<h2>Limitations</h2>
<p>{escape(str(package.get('prototype_disclaimer') or ''))}</p>
<p>Customer-entered values remain user-supplied assumptions. This brief does not set human_review_approved and it does not change investor readiness.</p>
</section>
"""
    return layout("Research Brief", body, printable=True)


def reports_page(records: list[dict[str, Any]]) -> str:
    items = "".join(
        f"<li><a href=\"/assessments/{escape(item['id'])}/report\">{escape(item['business_name'])} report</a> · "
        f"<a href=\"/assessments/{escape(item['id'])}/audit/html\">HTML audit view</a> · "
        f"<a href=\"/assessments/{escape(item['id'])}/audit\">audit</a></li>"
        for item in records
    )
    return layout(
        "Reports",
        f"{_section_welcome('Welcome to RUGD Reports', 'This page opens a draft report or the audit of a saved result.', 'A report does not change the stored recommendation or grant investor-ready status.')}{_SURFACE_NOTE}"
        "<p class=\"muted\">Service tier is stored on each assessment. A report does not change that tier.</p>"
        f"<ul>{items}</ul>"
        "<p class=\"muted\">Reports are drafts. A report is not investor-ready unless the existing gate "
        "and an authorized review say otherwise. This prototype does not write the official 0.1 output files. "
        "Authoritative financial numbers in a report come only from the 0.1 engine.</p>",
    )


def settings_page(user: dict[str, Any] | None = None) -> str:
    from app.future import future_status
    from app.notifications import EVENTS

    rows = "".join(
        "<li>"
        f"<strong>{escape(item['title'])}:</strong> {escape(item['status'])}. {escape(item['message'])}"
        "</li>"
        for item in future_status()["decisions"]
    )
    if user is None:
        preferences = """
<section class="card">
<h2>Email preferences</h2>
<p>Sign in with a local account to store which notices this account receives.</p>
<p class="muted">The preference is stored on the account. With SMTP_HOST unset, a chosen notice is written to the server log. Verification and password-reset messages stay available. A notice does not approve an assessment, clear a recommend-against flag, change a role, or set human_review_approved.</p>
</section>
"""
    else:
        stored = user.get("notification_preferences") or {}
        boxes = []
        for key, label, detail in EVENTS:
            checked = " checked" if stored.get(key) else ""
            boxes.append(
                "<label>"
                f'<input type="checkbox" name="pref_{escape(key)}" value="1"{checked}> '
                f"<strong>{escape(label)}</strong>. {escape(detail)}"
                "</label>"
            )
        preferences = (
            "<section class=\"card\">"
            "<h2>Email preferences</h2>"
            "<p>Choose which notices this account receives for assessments it owns. "
            "The preference is stored here. With SMTP_HOST unset, a chosen notice is written to the server log. "
            "Verification and password-reset messages stay available.</p>"
            "<form method=\"post\" action=\"/settings/notifications\">"
            + "".join(boxes)
            + "<button type=\"submit\">Save email preferences</button>"
            "</form>"
            "<p class=\"muted\">A notice does not approve an assessment, clear a recommend-against flag, "
            "change a role, or set human_review_approved.</p>"
            "</section>"
        )
    body = f"""
<h1>Settings</h1>
<p>This page stores preferences for this local account. It does not approve an assessment or change a role.</p>
{_SURFACE_NOTE}
<p>Service tiers on this prototype: Explore, Analyze, Validate (demonstration), and Partner (demonstration). Changing tier does not change a recommendation.</p>
<p>Local runs use 127.0.0.1. RUGD_ENV=production listens for the Render host and marks the session cookie Secure. Local accounts use an email and a scrypt password hash. Self-registration creates a customer account. The first reviewer is created from the bootstrap environment variables, and later reviewers are created by a signed-in reviewer. A new account can log in before the email is verified, and the screen shows that the email is unverified. The verification link expires in 24 hours. A forgot-password link expires in one hour. Without SMTP_HOST, those messages are written to the server log. Neither link changes a role. The session cookie is HttpOnly and SameSite=Lax. It is marked Secure when RUGD_ENV=production or SECURE_COOKIES=true. A customer account cannot set human_review_approved or change its own role. This is not production authentication. There is no payment processing. Prototype warnings stay on. Business profiles are local records. They do not authenticate a user.</p>
{preferences}
<h2>Owner decisions not activated</h2>
<p>These seams are disabled. They do not authenticate a user, calculate a score, deploy the app, or create a charge.</p>
<ul>{rows}</ul>
<p>Educational guidance on the tier pages is not a DVT evaluation. LongArc / DVT is not connected. The Webflow site is not connected.</p>
<p>Market Pulse is a hypothetical demonstration. Monitoring is not active. No scheduled job or connector is configured. Account email preferences on this page are stored for the signed-in account. A chosen notice can be written to the server log. The notice does not approve an assessment or clear a flag.</p>
<p>Only the RUGD Intelligence assessment is the official baseline. Bunny Hive and Small Town Pub stay empty named-pilot drafts until evidence is entered. They are not completed assessments.</p>
<p>Authoritative calculations remain in the 0.1 Python engine.</p>
"""
    return layout("Settings", body)


def new_assessment_page(
    profiles: list[dict[str, Any]] | None = None, message: str = ""
) -> str:
    options = []
    for key, label in {**ENGINE_PURPOSES, **UNSUPPORTED_PURPOSES}.items():
        options.append(f'<option value="{escape(key)}">{escape(label)}</option>')
    notice = f'<div class="banner">{escape(message)}</div>' if message else ""
    body = f"""
<h1>New assessment</h1>
{_SURFACE_NOTE}
{notice}
<p class="muted">A startup idea opens the current Explore intake. An existing or expanding business opens a shorter intake. Explore collects a draft. It is not a completed feasibility study.</p>
<form method="post" action="/assessments">
<div class="card">
<label>Is this a startup idea or an existing or expanding business?</label>
<select name="venture_path" required>
<option value="">Choose one</option>
<option value="startup">A startup idea</option>
<option value="existing">An existing or expanding business</option>
</select>
<p class="muted">A startup idea uses the current Explore intake, including the startup cost build. An existing or expanding business skips those startup-only questions and still asks for the monthly engine inputs. The choice is saved on the business profile. If you select an existing customer profile, its saved path is used. This choice does not change a recommendation.</p>
</div>
<label>Business name</label>
<input name="business_name" required>
<label>Business profile</label>
<select name="business_profile_id">
<option value="">New business profile</option>
{''.join(
    f'<option value="{escape(str(item.get("id")))}">{escape(str(item.get("display_name") or "Untitled"))}</option>'
    for item in profiles or []
    if item.get("isolation") == "customer"
)}
</select>
<p class="muted">Choosing an existing profile copies identity, industry, geography, and stage. The official baseline and named pilots are not listed. This is local prototype structure and does not authenticate a user.</p>
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


def _evidence_checklist(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    notes: list[dict[str, Any]] | None,
    *,
    return_to: str,
) -> str:
    from app.checklist import build_checklist

    view = build_checklist(record, result, notes)
    rows = []
    for item in view["items"]:
        item_id = str(item["id"])
        checked = " checked" if item["status"] in {"noted", "recorded"} else ""
        rows.append(
            "<li>"
            f'<input type="hidden" name="known_{escape(item_id)}" value="1">'
            f'<label><input type="checkbox" name="check_{escape(item_id)}" value="1"{checked}> '
            f"{escape(str(item['title']))}</label>"
            f"<p>{escape(str(item.get('plain') or ''))}</p>"
            f"<p><strong>Checklist status:</strong> {escape(str(item['status']).title())}</p>"
            f"<p class=\"muted\">{escape(str(item['guidance']))}</p>"
            "</li>"
        )
    assessment_id = escape(str(record.get("id") or ""))
    destination = return_to if return_to in {"explore", "results", "draft"} else "draft"
    return f"""
<section class="card" id="evidence-checklist-{assessment_id}">
<h2>Evidence checklist</h2>
<p>{escape(str(view["disclaimer"]))}</p>
<p><strong>Guidance progress:</strong> {view["noted_or_recorded"]} of {view["total"]} items noted or recorded. This progress does not clear a recommend-against flag.</p>
<form method="post" action="/assessments/{assessment_id}/checklist">
<input type="hidden" name="return_to" value="{escape(destination)}">
<ul>{''.join(rows)}</ul>
<button type="submit">Update checklist</button>
</form>
</section>
"""


def explore_page(
    records: list[dict[str, Any]],
    notes_by_id: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    notes_by_id = notes_by_id or {}
    links = "".join(
        f"<li><a href=\"/assessments/{escape(item['id'])}\">{escape(item['business_name'])}</a></li>"
        for item in records
    )
    checklists = "".join(
        "<h2>"
        + escape(str(item.get("business_name") or "Assessment"))
        + "</h2>"
        + _evidence_checklist(
            item,
            item.get("result") if isinstance(item.get("result"), dict) else None,
            notes_by_id.get(str(item.get("id") or "")),
            return_to="explore",
        )
        for item in records
    )
    return layout(
        "Explore",
        """
"""
        + _section_welcome(
            "Welcome to RUGD Explore",
            "This page is where a draft starts.",
            "You can describe the business, see which evidence is still missing, and save the intake. It does not clear a flag.",
        )
        + _SURFACE_NOTE
        + """
<p class="muted">Service tier: Explore.</p>
<div class="banner">Explore is an intake and gap check. It is not a completed feasibility study. It does not clear a flag.</div>
<p>Use a saved draft to clarify the concept, capital assumptions, and missing evidence. Run Analyze only when you want the deterministic engine.</p>
<p>Open a draft to ask the assistant about that assessment. The assistant is assistance only and cannot change the draft.</p>
<p><a class="button" href="/assessments/new">Start an Explore draft</a></p>
"""
        + _guidance_section("explore")
        + f"<ul>{links}</ul>"
        + checklists,
    )


def analyze_index(records: list[dict[str, Any]]) -> str:
    items = "".join(
        f"<li><a href=\"/assessments/{escape(item['id'])}/results\">{escape(item['business_name'])}</a></li>"
        for item in records
    )
    return layout(
        "Analyze",
        f"{_section_welcome('Welcome to RUGD Analyze', 'This page runs a saved draft through the assessment engine and shows the stored result.', 'Financial figures come only from that engine. A hard recommend-against flag still forces do-not-proceed.')}{_SURFACE_NOTE}"
        "<p class=\"muted\">Service tier: Analyze.</p>"
        "<p>Results come from the 0.1 deterministic engine. Authoritative financial numbers come only from the 0.1 engine. "
        "This list does not mark a draft or the official baseline investor-ready.</p>"
        f"<ul>{items}</ul>",
    )
