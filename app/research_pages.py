"""Customer pages for saved research and recorded Market Pulse developments."""

from __future__ import annotations

from html import escape
from typing import Any

from app.pages import layout
from app.federal_register import DOCUMENT_CLASSES, SOURCE_NAME as REGISTER_NAME
from app.public_retrieval import GEOGRAPHY_CHOICES, INDUSTRY_CHOICES, RETRIEVAL_YEARS, SOURCE_NAME
from app.research import (
    CLASS_LABELS,
    MONITOR_NOTICE,
    OBJECTIVES,
    PULSE_KINDS,
    REVIEW_STATUSES,
    SUMMARY_NOTICE,
    objective_label,
)

_NOTE = (
    "Saved research is not a live feed. It does not change financial inputs, "
    "a recommend-against flag, or investor readiness."
)


def _options(pairs: tuple[tuple[str, str], ...], selected: str) -> str:
    return "".join(
        f'<option value="{escape(key)}"{" selected" if key == selected else ""}>{escape(label)}</option>'
        for key, label in pairs
    )


def intelligence_index(records: list[dict[str, Any]], projects_by_assessment: dict[str, list[dict[str, Any]]]) -> str:
    if not records:
        items = "<li>No authorized business is available. Sign in, then open a draft from Explore.</li>"
    else:
        rows = []
        for record in records:
            assessment_id = escape(str(record.get("id") or ""))
            name = escape(str(record.get("business_name") or "Assessment"))
            projects = projects_by_assessment.get(str(record.get("id") or "")) or []
            if projects:
                saved = "".join(
                    f'<li><a href="/assessments/{assessment_id}/intelligence/{escape(str(item.get("id") or ""))}">'
                    f'{escape(str(item.get("title") or "Research project"))}</a></li>'
                    for item in projects
                )
            else:
                saved = "<li>No research project is saved yet.</li>"
            rows.append(
                "<section class=\"card\">"
                f"<h2>{name}</h2>"
                f"<ul>{saved}</ul>"
                f'<p><a class="button" href="/assessments/{assessment_id}/intelligence">Open research</a> '
                f'<a class="button" href="/assessments/{assessment_id}/pulse">Open Market Pulse</a></p>'
                "</section>"
            )
        items = "".join(rows)
    body = f"""
<h1>Research</h1>
<p>{_NOTE}</p>
<p>The market snapshot on Market Intelligence remains a separate demonstration. A saved project is customer research, not that snapshot.</p>
{items}
"""
    return layout("Research", body)


def assessment_research_page(
    record: dict[str, Any],
    projects: list[dict[str, Any]],
    *,
    writable: bool,
    notice: str = "",
) -> str:
    assessment_id = escape(str(record.get("id") or ""))
    banner = f'<div class="banner">{escape(notice)}</div>' if notice else ""
    saved = "".join(
        f'<li><a href="/assessments/{assessment_id}/intelligence/{escape(str(item.get("id") or ""))}">'
        f'{escape(str(item.get("title") or "Research project"))}</a> · '
        f'{escape(objective_label(str((item.get("document") or {}).get("objective") or "")))}</li>'
        for item in projects
    ) or "<li>No research project is saved yet.</li>"
    form = ""
    if writable:
        form = f"""
<form method="post" action="/assessments/{assessment_id}/intelligence">
<input type="hidden" name="op" value="create_project">
<label>Project title <input name="title" maxlength="200" required></label>
<label>Research objective <select name="objective">{_options(OBJECTIVES, "demand")}</select></label>
<label>Market or geographic area <input name="geography" maxlength="200"></label>
<label>Customer segments <input name="segments" maxlength="500"></label>
<label>Known competitors <input name="competitors" maxlength="500"></label>
<button type="submit">Save research project</button>
</form>
"""
    else:
        form = "<p>This file cannot be changed from research.</p>"
    body = f"""
<h1>Research for {escape(str(record.get("business_name") or "Assessment"))}</h1>
{banner}
<p>{_NOTE}</p>
<ul>{saved}</ul>
{form}
<p><a href="/assessments/{assessment_id}/pulse">Market Pulse for this business</a></p>
"""
    return layout("Research", body)


def _summary_block(summary: dict[str, Any]) -> str:
    parts = [f"<p><strong>{escape(SUMMARY_NOTICE)}</strong></p>"]
    labels = (
        ("market_overview", "Market overview"),
        ("customer_demand_signals", "Customer demand signals"),
        ("competitor_landscape", "Competitor landscape"),
        ("industry_developments", "Industry developments"),
        ("pricing_observations", "Pricing observations"),
        ("customer_needs", "Customer needs"),
        ("regulatory", "Regulatory developments"),
        ("opportunities", "Opportunities"),
        ("threats_and_risks", "Threats and risks"),
        ("evidence_limitations", "Evidence limitations"),
        ("unanswered_questions", "Unanswered questions"),
        ("next_steps", "Recommended next research steps"),
    )
    for key, label in labels:
        values = summary.get(key) or []
        items = "".join(f"<li>{escape(str(item))}</li>" for item in values)
        parts.append(f"<h3>{escape(label)}</h3><ul>{items}</ul>")
    return "<section class=\"card\" id=\"research-summary\">" + "".join(parts) + "</section>"


def project_page(
    record: dict[str, Any],
    project: dict[str, Any],
    evidence: list[dict[str, Any]],
    summary: dict[str, Any],
    *,
    writable: bool,
    plans: list[dict[str, Any]],
    decks: list[dict[str, Any]],
    retrieval: dict[str, Any] | None = None,
    notice: str = "",
) -> str:
    assessment_id = escape(str(record.get("id") or ""))
    project_id = escape(str(project.get("id") or ""))
    document = project.get("document") if isinstance(project.get("document"), dict) else {}
    banner = f'<div class="banner">{escape(notice)}</div>' if notice else ""
    rows = []
    for item in evidence:
        rows.append(
            "<article class=\"card\">"
            f"<h3>{escape(CLASS_LABELS.get(str(item.get('evidence_class') or ''), 'Evidence'))}</h3>"
            f"<p>{escape(str(item.get('finding') or 'No finding was recorded.'))}</p>"
            f"<p>Source: {escape(str(item.get('source_title') or 'Source title not recorded'))}. "
            f"Publisher: {escape(str(item.get('source_organization') or 'not recorded'))}.</p>"
            f"<p>Published: {escape(str(item.get('published_on') or 'publication date not recorded'))}. "
            f"Retrieved: {escape(str(item.get('retrieved_on') or 'retrieval date not recorded'))}.</p>"
            f"<p>URL stored as text: {escape(str(item.get('source_url') or 'none'))}. A URL is not proof of the finding.</p>"
            f"<p>Limitations: {escape(str(item.get('limitations') or 'none recorded'))}.</p>"
            + (
                f'<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">'
                '<input type="hidden" name="op" value="save_evidence">'
                f'<input type="hidden" name="evidence_id" value="{escape(str(item.get("id") or ""))}">'
                f'<input type="hidden" name="evidence_class" value="{escape(str(item.get("evidence_class") or "customer_provided"))}">'
                f'<input type="hidden" name="source_title" value="{escape(str(item.get("source_title") or ""))}">'
                f'<input type="hidden" name="source_organization" value="{escape(str(item.get("source_organization") or ""))}">'
                f'<input type="hidden" name="source_url" value="{escape(str(item.get("source_url") or ""))}">'
                f'<input type="hidden" name="published_on" value="{escape(str(item.get("published_on") or ""))}">'
                f'<input type="hidden" name="retrieved_on" value="{escape(str(item.get("retrieved_on") or ""))}">'
                f'<input type="hidden" name="retrieved" value="{("1" if item.get("retrieved_on") else "")}">'
                f'<input type="hidden" name="category" value="{escape(str(item.get("category") or "demand"))}">'
                f'<label>Finding <textarea name="finding" maxlength="1000">{escape(str(item.get("finding") or ""))}</textarea></label>'
                f'<label>Excerpt <textarea name="excerpt" maxlength="1000">{escape(str(item.get("excerpt") or ""))}</textarea></label>'
                f'<label>Limitations <textarea name="limitations" maxlength="500">{escape(str(item.get("limitations") or ""))}</textarea></label>'
                '<button type="submit">Save evidence edit</button></form>'
                if writable
                else ""
            )
            + "</article>"
        )
    evidence_html = "".join(rows) or "<p>No evidence is saved for this project.</p>"
    edit = ""
    if writable:
        plan_options = "".join(
            f'<option value="{escape(str(item.get("id") or ""))}">{escape(str(item.get("title") or "Business plan"))}</option>'
            for item in plans
        ) or '<option value="">No saved plan</option>'
        deck_options = "".join(
            f'<option value="{escape(str(item.get("id") or ""))}">{escape(str(item.get("title") or "Pitch deck"))}</option>'
            for item in decks
        ) or '<option value="">No saved deck</option>'
        proposal = document.get("proposal") if isinstance(document.get("proposal"), dict) else None
        proposal_html = ""
        if proposal and str(proposal.get("text") or "").strip():
            proposal_html = (
                '<section class="card" id="research-proposal"><h2>Proposal for review</h2>'
                f"<p>{escape(str(proposal.get('text') or ''))}</p>"
                f'<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">'
                '<input type="hidden" name="op" value="decide_proposal">'
                '<button type="submit" name="decision" value="approve">Approve and save the note</button> '
                '<button type="submit" name="decision" value="reject">Reject</button>'
                "</form></section>"
            )
        edit = f"""
<section class="card">
<h2>Update the project</h2>
<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">
<input type="hidden" name="op" value="save_project">
<label>Title <input name="title" maxlength="200" value="{escape(str(project.get("title") or ""))}"></label>
<label>Objective <select name="objective">{_options(OBJECTIVES, str(document.get("objective") or "demand"))}</select></label>
<label>Market or geographic area <input name="geography" maxlength="200" value="{escape(str(document.get("geography") or ""))}"></label>
<label>Customer segments <input name="segments" maxlength="500" value="{escape(str(document.get("segments") or ""))}"></label>
<label>Known competitors <input name="competitors" maxlength="500" value="{escape(str(document.get("competitors") or ""))}"></label>
<button type="submit">Save project</button>
</form>
</section>
<section class="card">
<h2>Add evidence</h2>
<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">
<input type="hidden" name="op" value="save_evidence">
<label>Evidence class
<select name="evidence_class">
<option value="source_backed_unverified">Source-backed, not verified</option>
<option value="customer_provided">Customer-provided observation</option>
</select>
</label>
<label>Source title <input name="source_title" maxlength="200"></label>
<label>Publisher <input name="source_organization" maxlength="200"></label>
<label>Source URL <input name="source_url" maxlength="500"></label>
<label>Publication date <input name="published_on" placeholder="YYYY-MM-DD"></label>
<label><input type="checkbox" name="retrieved" value="1"> I retrieved this source</label>
<label>Retrieval date <input name="retrieved_on" placeholder="YYYY-MM-DD"></label>
<label>Category <select name="category">{_options(OBJECTIVES, str(document.get("objective") or "demand"))}</select></label>
<label>Finding <textarea name="finding" maxlength="1000"></textarea></label>
<label>Excerpt <textarea name="excerpt" maxlength="1000"></textarea></label>
<label>Limitations <textarea name="limitations" maxlength="500"></textarea></label>
<button type="submit">Save evidence</button>
</form>
<p>A source URL is stored as text. This form does not retrieve it, and it cannot mark the claim verified.</p>
</section>
<section class="card">
<h2>Use reviewed research</h2>
<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">
<input type="hidden" name="op" value="propose">
<label>Business plan <select name="plan_id">{plan_options}</select></label>
<label>Pitch deck <select name="deck_id">{deck_options}</select></label>
<label>Target <select name="target"><option value="plan">Business plan</option><option value="deck">Pitch deck</option></select></label>
<button type="submit">Propose a note for review</button>
</form>
<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">
<input type="hidden" name="op" value="save_summary">
<button type="submit">Save this summary</button>
</form>
<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">
<input type="hidden" name="op" value="create_action">
<button type="submit">Create an action from the first unanswered question</button>
</form>
{proposal_html}
</section>
"""
    saved_summaries = document.get("summaries") if isinstance(document.get("summaries"), list) else []
    history = "".join(
        f"<li>Saved {escape(str(item.get('saved_at') or ''))}. {escape(str((item.get('sections') or {}).get('notice') or SUMMARY_NOTICE) if False else SUMMARY_NOTICE)}</li>"
        for item in saved_summaries
        if isinstance(item, dict)
    ) or "<li>No earlier summary is saved.</li>"
    body = f"""
<h1>{escape(str(project.get("title") or "Research project"))}</h1>
{banner}
<p>{_NOTE}</p>
<p>Objective: {escape(objective_label(str(document.get("objective") or "")))}.
Area: {escape(str(document.get("geography") or "not recorded"))}.
Segments: {escape(str(document.get("segments") or "not recorded"))}.</p>
{_summary_block(summary)}
<h2>Saved evidence</h2>
{evidence_html}
{_retrieval_section(assessment_id, project_id, retrieval, writable=writable)}
<h2>Earlier summaries</h2>
<ul>{history}</ul>
{edit}
<p><a href="/assessments/{assessment_id}/advice">Ask the adviser about this assessment</a>. A question is sent only when you choose Ask.</p>
"""
    return layout("Research", body)


def _retrieval_section(
    assessment_id: str,
    project_id: str,
    retrieval: dict[str, Any] | None,
    *,
    writable: bool,
) -> str:
    if not writable:
        return "<p>Public retrieval is not available for a file this session cannot change.</p>"
    industries = "".join(f"<option>{escape(name)}</option>" for name in INDUSTRY_CHOICES)
    geographies = "".join(f"<option>{escape(name)}</option>" for name in GEOGRAPHY_CHOICES)
    years = "".join(f"<option>{escape(year)}</option>" for year in RETRIEVAL_YEARS)
    classes = "".join(
        f'<option value="{escape(key)}">{escape(label)}</option>' for key, label in DOCUMENT_CLASSES
    )
    review = ""
    error = ""
    if retrieval and retrieval.get("error_category"):
        error = (
            "<p id=\"retrieval-error\">The public retrieval did not return records. "
            f"Category: {escape(str(retrieval.get('error_category') or ''))}.</p>"
        )
    if retrieval and retrieval.get("status") == "review":
        records = retrieval.get("records") if isinstance(retrieval.get("records"), list) else []
        if records:
            choices = "".join(
                "<li>"
                + escape(str(item.get("measure") or "Record"))
                + ": "
                + escape(str(item.get("value") or ""))
                + ". Published "
                + escape(str(item.get("published_on") or "date not recorded"))
                + ". "
                + escape(str(item.get("freshness") or ""))
                + f"<form method=\"post\" action=\"/assessments/{assessment_id}/intelligence/{project_id}\">"
                "<input type=\"hidden\" name=\"op\" value=\"import_public\">"
                f"<input type=\"hidden\" name=\"batch_id\" value=\"{escape(str(retrieval.get('id') or ''))}\">"
                f"<input type=\"hidden\" name=\"selected\" value=\"{escape(str(index))}\">"
                "<button type=\"submit\">Import this record</button></form></li>"
                for index, item in enumerate(records)
                if isinstance(item, dict)
            )
            review = (
                "<section class=\"card\" id=\"retrieval-review\">"
                f"<h2>Review public records</h2><p>Retrieved {escape(str(retrieval.get('retrieved_on') or 'date not recorded'))}. "
                f"Source: {escape(str(retrieval.get('source_name') or SOURCE_NAME))}.</p>"
                f"<p>{escape(str(retrieval.get('limitations') or ''))}</p>"
                f"<p>{escape(str(retrieval.get('notice') or ''))}</p>"
                f"<ul>{choices}</ul>"
                f"<form method=\"post\" action=\"/assessments/{assessment_id}/intelligence/{project_id}\">"
                "<input type=\"hidden\" name=\"op\" value=\"reject_public\">"
                f"<input type=\"hidden\" name=\"batch_id\" value=\"{escape(str(retrieval.get('id') or ''))}\">"
                "<button type=\"submit\">Reject these results</button></form></section>"
            )
        else:
            review = (
                "<section class=\"card\" id=\"retrieval-review\"><h2>Review public records</h2>"
                f"<p>{escape(str(retrieval.get('notice') or 'No public observation was returned for this industry and geography.'))}</p>"
                f"<p>Retrieved {escape(str(retrieval.get('retrieved_on') or 'date not recorded'))}.</p></section>"
            )
    return f"""
<section class="card" id="public-retrieval">
<h2>Retrieve public information</h2>
<p>One request is sent when you choose Retrieve. The address is chosen by RUGD. A typed web address is not used. Results stay unsaved until you import them. A proposed rule or a notice is not an enacted requirement.</p>
<form method="post" action="/assessments/{assessment_id}/intelligence/{project_id}">
<input type="hidden" name="op" value="retrieve_public">
<label>Official source <select name="source"><option value="bls-qcew">{escape(SOURCE_NAME)}</option><option value="federal-register">{escape(REGISTER_NAME)}</option></select></label>
<label>Industry <select name="industry">{industries}</select></label>
<label>Geography <select name="geography">{geographies}</select></label>
<label>Year <select name="year">{years}</select></label>
<label>Federal Register search <input name="term" maxlength="80"></label>
<label>Document class <select name="document_class">{classes}</select></label>
<button type="submit">Retrieve public information</button>
</form>
{error}
{review}
</section>
"""


def pulse_page(
    record: dict[str, Any],
    developments: list[dict[str, Any]],
    monitors: list[dict[str, Any]],
    *,
    writable: bool,
    evidence: list[dict[str, Any]] | None = None,
    notice: str = "",
) -> str:
    assessment_id = escape(str(record.get("id") or ""))
    banner = f'<div class="banner">{escape(notice)}</div>' if notice else ""
    cards = []
    for item in developments:
        status = escape(str(item.get("review_status") or "open"))
        controls = ""
        if writable:
            controls = (
                f'<form method="post" action="/assessments/{assessment_id}/pulse">'
                f'<input type="hidden" name="op" value="review_development">'
                f'<input type="hidden" name="development_id" value="{escape(str(item.get("id") or ""))}">'
                '<button type="submit" name="review_status" value="reviewed">Mark reviewed</button> '
                '<button type="submit" name="review_status" value="relevant">Mark relevant</button> '
                '<button type="submit" name="review_status" value="not_relevant">Mark not relevant</button>'
                "</form>"
            )
        cards.append(
            "<article class=\"card\">"
            f"<h3>{escape(str(item.get('title') or 'Development'))}</h3>"
            f"<p>Recorded by you. Status: {status}. This was not collected by monitoring.</p>"
            f"<p>Date: {escape(str(item.get('occurred_on') or 'not recorded'))}. "
            f"Source: {escape(str(item.get('source_label') or 'not recorded'))}.</p>"
            f"<p>Affected: {escape(str(item.get('affected') or 'not recorded'))}.</p>"
            f"<p>Relevance: {escape(str(item.get('relevance') or ''))}</p>"
            f"<p>Implications: {escape(str(item.get('implications') or ''))}</p>"
            f"<p>Limitations: {escape(str(item.get('limitations') or ''))}</p>"
            f"<p>Evidence reference: {escape(str(item.get('evidence_id') or 'none'))}. A retrieved record is not a material business event.</p>"
            f"{controls}</article>"
        )
    development_html = "".join(cards) or "<p>No development is recorded.</p>"
    monitor_html = []
    for item in monitors:
        monitor_html.append(
            "<article class=\"card\">"
            f"<h3>{escape(str(item.get('topic') or 'Topic'))}</h3>"
            f"<p>{escape(MONITOR_NOTICE)}</p>"
            "<p>Configured monitoring. Actual completed checks: 0. Newly collected findings: none. "
            "Historical findings from a check: none.</p>"
            f"<p>Keywords: {escape(str(item.get('keywords') or 'not recorded'))}. "
            f"Geography: {escape(str(item.get('geography') or 'not recorded'))}. "
            f"Preference: {escape(str(item.get('frequency') or 'manual'))}.</p>"
            "</article>"
        )
    monitors_shown = "".join(monitor_html) or "<p>No monitoring topic is configured.</p>"
    forms = ""
    if writable:
        forms = f"""
<section class="card">
<h2>Record a development</h2>
<form method="post" action="/assessments/{assessment_id}/pulse">
<input type="hidden" name="op" value="create_development">
<label>Title <input name="title" maxlength="200" required></label>
<label>Kind <select name="kind">{_options(PULSE_KINDS, "competitor")}</select></label>
<label>Date <input name="occurred_on" placeholder="YYYY-MM-DD"></label>
<label>Source <input name="source_label" maxlength="200"></label>
<label>Affected business or market <input name="affected" maxlength="200"></label>
<label>Relevance <textarea name="relevance" maxlength="500"></textarea></label>
<label>Potential implications <textarea name="implications" maxlength="500"></textarea></label>
<p>A linked public record keeps its source. A proposed rule or a notice is not an enacted requirement, and a retrieved record is not a material business event.</p>
<label>Link an approved public evidence record
<select name="evidence_id"><option value="">None</option>{''.join(
    f'<option value="{escape(str(item.get("id") or ""))}">{escape(str(item.get("finding") or "Retrieved record")[:80])}</option>'
    for item in (evidence or [])
    if item.get("evidence_class") == "retrieved_public"
)}</select>
</label>
<button type="submit">Save development</button>
</form>
</section>
<section class="card">
<h2>Configure a monitoring topic</h2>
<form method="post" action="/assessments/{assessment_id}/pulse">
<input type="hidden" name="op" value="save_monitor">
<label>Topic <input name="topic" maxlength="200" required></label>
<label>Keywords <input name="keywords" maxlength="300"></label>
<label>Competitor names <input name="competitors" maxlength="300"></label>
<label>Geographic focus <input name="geography" maxlength="200"></label>
<label>Frequency preference
<select name="frequency"><option value="manual">Manual</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select>
</label>
<label>Source preference <input name="source_preference" maxlength="200"></label>
<button type="submit">Save monitoring topic</button>
</form>
<p>Saving a topic does not run a check and does not call an external service.</p>
</section>
"""
    body = f"""
<h1>Market Pulse for {escape(str(record.get("business_name") or "Assessment"))}</h1>
{banner}
<p>Recorded developments are not the demonstration cards. Monitoring is not running.</p>
<h2>Recorded developments</h2>
{development_html}
<h2>Monitoring configuration</h2>
{monitors_shown}
{forms}
<p><a href="/assessments/{assessment_id}/intelligence">Back to research</a></p>
"""
    return layout("Research", body)
