"""Pages for benchmarks, the proposed revenue worksheet, and feasibility improvement scenarios.

Every page here is advisory. None changes the official result, a flag, the scoring, or
human review. Saving writes a separate record. Applying a scenario copies its values
into the working draft only after the customer confirms, and it does not run Analyze.
"""

from __future__ import annotations

from html import escape
from typing import Any

from app import advisory, benchmarks, display, improve, wording
from app import revenue_worksheet as rw
from app.field_help import DAYS
from app.pages import _workspace_links, _ws_header, layout

_STYLE = """<style>
.adv-sub { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; margin: 0.6rem 0 1rem; padding: 0.5rem 0.7rem; background: #FBF9F4; border: 1px solid var(--stone); }
.adv-sub a { color: var(--ink); }
.adv-sub a.on { font-weight: 600; border-bottom: 2px solid var(--bronze); text-decoration: none; }
.adv-note { background: #FBF9F4; border-left: 4px solid var(--bronze); padding: 0.6rem 0.85rem; margin: 0.8rem 0; font-size: 0.92rem; }
.adv-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 0.6rem; margin: 0.6rem 0; }
.adv-stat { background: white; border: 1px solid var(--stone); padding: 0.55rem 0.7rem; }
.adv-stat b { display: block; font-size: 1.15rem; }
.adv-stat span { font-size: 0.8rem; color: #5c6b76; }
.adv-table { overflow-x: auto; }
.adv-table table { min-width: 34rem; font-size: 0.9rem; }
.adv-table td, .adv-table th { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--stone); vertical-align: top; }
.adv-table td.num, .adv-table th.num { text-align: right; white-space: nowrap; }
.adv-tag { display: inline-block; font-size: 0.74rem; padding: 0.05rem 0.45rem; margin: 0 0.3rem 0.2rem 0; background: var(--stone); color: var(--ink); border-radius: 8px; }
.adv-tag.warn { background: #f1dcc0; }
.adv-tag.bad { background: #e8c4c4; }
.adv-rec { background: white; border: 1px solid var(--stone); padding: 0.7rem 0.9rem; margin: 0.6rem 0; }
.adv-rec h3 { margin: 0 0 0.2rem; font-size: 1rem; }
.adv-preset { background: white; border: 1px solid var(--stone); border-left: 4px solid var(--bronze); padding: 0.6rem 0.8rem; margin: 0.5rem 0; }
.adv-preset p { margin: 0.2rem 0; font-size: 0.9rem; }
.adv-form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0 0.8rem; }
.adv-form-grid label small { color: #5c6b76; display: block; }
.adv-chart { width: 100%; max-width: 40rem; height: auto; background: white; border: 1px solid var(--stone); margin: 0.4rem 0; }
.adv-good { color: #2e6b3a; }
.adv-bad { color: #7a2e2e; }
.adv-btn-row form { display: inline; }
.adv-btn-row button { margin-right: 0.4rem; }
button.ghost { background: white; color: var(--ink); border: 1px solid var(--ink); }
.adv-sub { border-radius: 14px; border-color: var(--line); background: var(--card); }
.adv-note { border-radius: 12px; border-left-width: 4px; }
.adv-stat, .adv-rec, .adv-preset, .adv-chart { border-radius: 14px; border-color: var(--line); background: var(--card); }
.adv-table { border-radius: 12px; }
.adv-tag { border-radius: 999px; padding: 0.1rem 0.6rem; }
</style>"""


def _n(value: Any) -> str:
    return display.money(value, missing="n/a")


def _x(value: Any) -> str:
    return display.multiple(value, missing="n/a")


def _id(record: dict[str, Any]) -> str:
    return escape(str(record.get("id") or ""))


def _subnav(record: dict[str, Any], current: str) -> str:
    assessment_id = _id(record)
    items = (
        ("benchmarks", "Benchmarks"),
        ("revenue-worksheet", "Revenue worksheet"),
        ("improve", "Improve feasibility"),
    )
    links = "".join(
        f'<a href="/assessments/{assessment_id}/{slug}"{" class=on aria-current=page" if slug == current else ""}>{label}</a>'
        for slug, label in items
    )
    section = {"benchmarks": "benchmarks", "revenue-worksheet": "revenue-model", "improve": "scenarios"}.get(current, "overview")
    back = (
        f'<a href="/assessments/{assessment_id}/results#{section}">Back to Analyze results</a>'
        if improve.explain_official(record)["ran"]
        else ""
    )
    return (
        f'<div class="adv-sub no-print" aria-label="Planning tools">{links}{back}'
        f'<a href="/assessments/{assessment_id}">Back to your draft</a></div>'
    )


def _shell(record: dict[str, Any], title: str, current: str, body: str) -> str:
    name = escape(str(record.get("business_name") or record.get("profile", {}).get("business_name") or "Your business"))
    return layout(
        title,
        f"{_STYLE}{_ws_header(record, title, 'improve', subtitle=name)}{_subnav(record, current)}{body}",
        active="/assessments",
    )


def _official_strip(record: dict[str, Any]) -> str:
    official = improve.explain_official(record)
    if not official["ran"]:
        return (
            '<div class="adv-note"><strong>Official result:</strong> Analyze has not been run for this draft. '
            "Nothing on this page changes that.</div>"
        )
    from app import wording

    flags = ", ".join(escape(flag) for flag in official["flags"]) or "none"
    plain = wording.official_line(
        {
            "engine_ran": True,
            "recommendation": official["recommendation"],
            "blocking_flags": list(official["flags"]),
            "readiness_status": official["readiness"],
            "human_review_status": official["review"],
        }
    )
    return (
        '<div class="adv-note"><strong>Where the official result stands.</strong> '
        f"{escape(plain)} Nothing on this page changes it."
        '<details class="techref"><summary>Technical reference</summary>'
        "<p><strong>Official result, unchanged by this page:</strong> "
        f"{escape(official['recommendation'] or 'not stated')} · blocking flags: {flags} · "
        f"readiness: {escape(official['readiness'] or 'not stated')} · human review: {escape(official['review'])}.</p>"
        "</details></div>"
    )


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


def _record_html(record: dict[str, Any]) -> str:
    tags = [f'<span class="adv-tag">{escape(record["status"])}</span>']
    if record.get("stale"):
        tags.append('<span class="adv-tag warn">Stale, older than two years</span>')
    if record.get("undated"):
        tags.append('<span class="adv-tag warn">No publication date</span>')
    if record.get("conflict"):
        tags.append('<span class="adv-tag bad">Conflicts with another record</span>')
    if not record.get("all_respondents", True):
        tags.append('<span class="adv-tag">Subgroup only</span>')
    links = " ".join(
        f'<a href="{escape(url)}" rel="noopener noreferrer" target="_blank">Source link</a>' for url in record.get("source_urls") or []
    ) or "No link recorded."
    applicability = "".join(f"<li>{escape(note)}</li>" for note in record.get("applicability") or [])
    limits = "".join(f"<li>{escape(note)}</li>" for note in record.get("limitations") or [])
    rows = (
        ("Industry and subsector", f"{record['industry']}. {record['subsector']}"),
        ("Business model", record["business_model"]),
        ("Geography", record["geography"]),
        ("Venue size or scale", record["scale"]),
        ("Metric and units", f"{record['metric']} ({record['unit']})"),
        ("Source", record["source"]),
        ("Published", record.get("published") or "Not stated"),
        ("Period covered", record.get("period") or "Not stated"),
        ("Retrieved", record.get("retrieved") or "Not recorded"),
        ("Methodology", record["methodology"]),
        ("Confidence", record["confidence"]),
    )
    table = "".join(f"<tr><th scope=\"row\">{escape(label)}</th><td>{escape(str(value))}</td></tr>" for label, value in rows)
    return (
        '<div class="adv-rec">'
        f'<h3>{escape(record["metric"])}: {escape(record["value_text"])}</h3>'
        f'<p>{"".join(tags)}</p>'
        f'<p class="muted">{escape(record["source"])} · {links}</p>'
        '<details><summary>Applicability, methodology, and limits</summary>'
        f'<div class="adv-table"><table>{table}</table></div>'
        + (f'<p><strong>Applicability.</strong></p><ul>{applicability}</ul>' if applicability else "")
        + f'<p><strong>Limitations.</strong></p><ul>{limits}</ul></details>'
        + "</div>"
    )


def benchmarks_page(
    record: dict[str, Any],
    entries: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    *,
    writable: bool,
    notice: str = "",
    error: str = "",
    form: dict[str, str] | None = None,
) -> str:
    form = form or {}
    profile = record.get("profile") or {}
    context = benchmarks.match(profile, entries)
    industry = str(profile.get("industry") or "").strip() or "not set"
    market = context["market"] or "not set"
    style_label = dict(advisory.SERVICE_STYLES).get(context["style"], "not set")
    intro = (
        f'<div class="adv-note">{escape(context["caveat"])} Industry: {escape(industry)}. Market: {escape(market)}. '
        f"Service style: {escape(style_label)}. Figures are national or customer-recorded. "
        "RUGD has no verified benchmark for your city or venue size.</div>"
    )
    banner = f'<div class="banner">{escape(notice)}</div>' if notice else ""
    if error:
        banner += f'<div class="banner" role="alert">{escape(error)}</div>'
    stored = [item for item in context["records"] if item["status"] == benchmarks.STATUS_SECONDARY]
    mine = [item for item in context["records"] if item["status"] == benchmarks.STATUS_CUSTOMER]
    if context["family"] != "hospitality":
        loaded = (
            f"<p><strong>No benchmark is loaded for {escape(industry)}.</strong> RUGD does not estimate one, and nothing on your "
            "intake is filled from a guess. Record figures you find below, with their sources.</p>"
        )
    elif not stored:
        loaded = "<p>No stored restaurant medians match your service style.</p>"
    else:
        loaded = (
            "<p>These restaurant medians were already stored for the reasonableness check. They come from public commentary and "
            "secondary summaries of the National Restaurant Association's annual survey, not from the primary abstract.</p>"
            + "".join(_record_html(item) for item in stored)
        )
    mine_html = "".join(_record_html(item) for item in mine) or '<p class="muted">You have not recorded any figures yet.</p>'
    remove = ""
    if writable and entries:
        rows = "".join(
            f'<form method="post" action="/assessments/{_id(record)}/benchmarks" class="adv-btn-row">'
            f'<input type="hidden" name="op" value="delete"><input type="hidden" name="entry_id" value="{escape(str(item["id"]))}">'
            f'{escape(str(item["payload"].get("metric") or "Figure"))}: {escape(str(item["payload"].get("source") or ""))} '
            '<button type="submit" class="ghost">Remove</button></form><br>'
            for item in entries
        )
        remove = f"<details><summary>Remove a recorded figure</summary>{rows}</details>"
    unresolved = "".join(
        f'<div class="adv-rec"><h3>{escape(item["metric"])}: not loaded</h3>'
        f'<p><span class="adv-tag bad">{escape(item["status"])}</span></p>'
        f'<p>Public sources disagree: {escape(" versus ".join(item["candidates"]))}. RUGD stores neither value.</p>'
        f'<p class="muted">{escape(item["note"])}</p></div>'
        for item in context["unresolved"]
    )
    labels = [benchmarks.METRICS[key]["label"] for key in context["missing"]]
    missing_html = (
        f"<p><strong>Not loaded:</strong> {escape('; '.join(labels))}. For each of these, RUGD has no figure to show. "
        "Use the worksheet to record one with its source, or build the assumption from your own quotes.</p>"
        if labels
        else ""
    )
    options = "".join(
        f'<option value="{escape(key)}"{" selected" if form.get("metric_key") == key else ""}>'
        f"{escape(spec['label'])} ({escape(spec['unit'])})</option>"
        for key, spec in benchmarks.METRICS.items()
    ) + f'<option value="custom"{" selected" if form.get("metric_key") == "custom" else ""}>Other measure</option>'

    def field(name: str, label: str, hint: str = "", *, required: bool = False) -> str:
        return (
            f'<label for="b-{name}">{escape(label)}{" (required)" if required else ""}'
            f'{f"<small>{escape(hint)}</small>" if hint else ""}</label>'
            f'<input id="b-{name}" name="{name}" value="{escape(form.get(name, ""))}">'
        )

    worksheet = ""
    if writable:
        worksheet = (
            f'<form method="post" action="/assessments/{_id(record)}/benchmarks" id="record-figure">'
            '<input type="hidden" name="op" value="save">'
            '<p class="muted">Enter a figure you found. It is saved as customer-recorded and unverified, never as a RUGD benchmark. '
            "It can pre-fill a suggestion only when you choose to use that suggestion.</p>"
            '<div class="adv-form-grid"><div><label for="b-metric_key">What it measures</label>'
            f'<select id="b-metric_key" name="metric_key">{options}</select></div>'
            + field("custom_label", "Name of the measure", "Only for Other")
            + field("custom_unit", "Units", "Only for Other")
            + field("value", "Figure", "A share of sales is entered as a percent, such as 31.5", required=True)
            + field("source_name", "Source", "Publisher and title, or write your own estimate", required=True)
            + field("source_url", "Source link", "http or https")
            + field("published_on", "Published", "YYYY or YYYY-MM-DD")
            + field("retrieved_on", "Date you found it", "YYYY-MM-DD. Today if blank")
            + field("geography", "Where it applies", "City, county, state, or national")
            + field("scale", "Venue size or scale", "Seats, square feet, or revenue range")
            + '<div><label for="b-confidence">How much you trust it</label><select id="b-confidence" name="confidence">'
            '<option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div>'
            "</div>"
            + field("notes", "Notes", "Anything that limits how it applies")
            + '<button type="submit">Save the figure</button></form>'
        )
    else:
        worksheet = '<p class="muted">This record is view only. Open your own draft to record figures.</p>'
    context_rows = benchmarks.evidence_context(evidence)
    evidence_html = (
        "".join(
            '<div class="adv-rec">'
            f'<h3>{escape(item["metric"])}</h3><p><span class="adv-tag">{escape(item["status"])}</span></p>'
            f'<p>{escape(item["finding"])}</p>'
            f'<p class="muted">{escape(item["source"])} · {escape(item["geography"])} · published {escape(item["published"] or "not stated")} · retrieved {escape(item["retrieved"] or "not stated")}</p>'
            f'<p class="muted">Limitations: {escape(" ".join(item["limitations"]))}</p></div>'
            for item in context_rows
        )
        or '<p class="muted">No research is imported for this draft. Research can add place-level context.</p>'
    )
    sources = "".join(
        f'<li><a href="{escape(item["url"])}" rel="noopener noreferrer" target="_blank">{escape(item["name"])}</a>. {escape(item["covers"])}</li>'
        for item in benchmarks.SOURCE_DIRECTORY
    )
    body = (
        banner
        + _official_strip(record)
        + intro
        + "<h2>Stored figures</h2>"
        + f'<p class="muted">What is a benchmark? {wording.explain("benchmark", _id(record))}</p>'
        + loaded
        + unresolved
        + "<h2>Not loaded</h2>"
        + (missing_html or "<p>Every measure RUGD tracks has a figure on file.</p>")
        + "<h2>Figures you recorded</h2>"
        + mine_html
        + remove
        + "<h2>Record a figure or build your own assumption</h2>"
        + worksheet
        + "<h2>Place and industry context from your research</h2>"
        + evidence_html
        + "<h2>Where to look</h2><ul>"
        + sources
        + "</ul><p class=\"muted\">RUGD retrieves only free public data you ask for, and it does not scrape sites that forbid it.</p>"
    )
    return _shell(record, "Benchmarks and planning figures", "benchmarks", body)


# ---------------------------------------------------------------------------
# Revenue worksheet
# ---------------------------------------------------------------------------


def revenue_page(
    record: dict[str, Any],
    form: dict[str, str],
    worksheet: dict[str, Any] | None,
    errors: list[str],
    saved: dict[str, Any] | None,
    *,
    writable: bool,
    notice: str = "",
) -> str:
    profile = record.get("profile") or {}
    banner = f'<div class="banner">{escape(notice)}</div>' if notice else ""
    if errors:
        banner += '<div class="banner" role="alert">' + "<br>".join(escape(item) for item in errors) + "</div>"
    parsed = worksheet if worksheet is not None else rw.parse(form)[0]
    calc = rw.calculate(parsed) if not errors else None
    selected_days = {part.strip() for part in str(form.get("operating_schedule") or "").split(",")}
    day_boxes = "".join(
        f'<label class="inline"><input type="checkbox" name="day_{code}" value="1"{" checked" if code in selected_days else ""}> {escape(label)}</label> '
        for code, label in DAYS
    )

    def val(name: str) -> str:
        return escape(str(form.get(name) or ""))

    period_rows = ""
    for index in range(1, rw.PERIOD_SLOTS + 1):
        period_rows += (
            f"<tr><td><input name=\"period_{index}_name\" value=\"{val(f'period_{index}_name')}\" aria-label=\"Period {index} name\" placeholder=\"Lunch\"></td>"
            f"<td><input name=\"period_{index}_turns\" value=\"{val(f'period_{index}_turns')}\" aria-label=\"Period {index} seat turns\" inputmode=\"decimal\"></td>"
            f"<td><input name=\"period_{index}_util_weekday\" value=\"{val(f'period_{index}_util_weekday')}\" aria-label=\"Period {index} weekday utilization\" inputmode=\"decimal\"></td>"
            f"<td><input name=\"period_{index}_util_weekend\" value=\"{val(f'period_{index}_util_weekend')}\" aria-label=\"Period {index} weekend utilization\" inputmode=\"decimal\"></td>"
            f"<td><input name=\"period_{index}_ticket\" value=\"{val(f'period_{index}_ticket')}\" aria-label=\"Period {index} average check\" inputmode=\"decimal\"></td></tr>"
        )
    stream_rows = ""
    for index in range(1, rw.STREAM_SLOTS + 1):
        stream_rows += (
            f"<tr><td><input name=\"stream_{index}_name\" value=\"{val(f'stream_{index}_name')}\" aria-label=\"Other revenue {index} name\" placeholder=\"Catering\"></td>"
            f"<td><input name=\"stream_{index}_annual\" value=\"{val(f'stream_{index}_annual')}\" aria-label=\"Other revenue {index} yearly amount\" inputmode=\"decimal\"></td>"
            f"<td><input name=\"stream_{index}_basis\" value=\"{val(f'stream_{index}_basis')}\" aria-label=\"Other revenue {index} basis\"></td></tr>"
        )
    buttons = '<button type="submit" name="op" value="calculate">Calculate</button>'
    if writable:
        buttons += '<button type="submit" name="op" value="save" class="ghost">Save the worksheet</button>'
    form_html = (
        f'<form method="post" action="/assessments/{_id(record)}/revenue-worksheet">'
        f'<label for="rw-seats">Seats</label><input id="rw-seats" name="seats" value="{val("seats")}" inputmode="numeric">'
        f"<fieldset><legend>Days you are open</legend>{day_boxes}</fieldset>"
        f'<label for="rw-weeks">Weeks open per year</label><input id="rw-weeks" name="operating_weeks" value="{val("operating_weeks")}" inputmode="decimal">'
        '<h3>Service periods</h3><div class="adv-table"><table><thead><tr><th>Period</th><th>Seat turns</th><th>Weekday use (0-1)</th><th>Weekend use (0-1)</th><th>Average check</th></tr></thead>'
        f"<tbody>{period_rows}</tbody></table></div>"
        '<h3>Other revenue</h3><div class="adv-table"><table><thead><tr><th>Stream</th><th>Per year</th><th>Basis</th></tr></thead>'
        f"<tbody>{stream_rows}</tbody></table></div>"
        f'<label for="rw-note">Note</label><input id="rw-note" name="note" value="{val("note")}">'
        f"<div>{buttons}</div></form>"
    )
    result_html = ""
    if calc:
        lines = "".join(
            f"<tr><td>{escape(line['period'])}, {line['day_type']}</td><td class=\"num\">{line['covers']:,.0f}</td>"
            f"<td>{escape(line['formula'])}</td><td class=\"num\">{_n(line['revenue'])}</td></tr>"
            for line in calc["lines"]
        )
        result_html = (
            "<h2>The calculation</h2>"
            '<div class="adv-table"><table><thead><tr><th>Line</th><th class="num">Covers</th><th>Formula</th><th class="num">Revenue</th></tr></thead>'
            f"<tbody>{lines}</tbody>"
            f'<tfoot><tr><th colspan="3">Service revenue</th><td class="num">{_n(calc["core_revenue"])}</td></tr>'
            f'<tr><th colspan="3">Other revenue</th><td class="num">{_n(calc["other_revenue"])}</td></tr>'
            f'<tr><th colspan="3">Proposed yearly revenue</th><td class="num"><strong>{_n(calc["total_revenue"])}</strong></td></tr></tfoot></table></div>'
            f'<p class="muted">Monthly: {_n(calc["monthly_revenue"])}. Covers per seat per open day: {calc["covers_per_seat_per_open_day"]:.2f}. '
            f'Average check: {_n(calc["average_check"])}.</p>'
        )
        comparison = rw.compare(parsed, calc, profile)
        result_html += _comparison_html(comparison, calc)
    elif not errors:
        needed = rw.missing(parsed)
        result_html = (
            f'<p class="adv-note">Still needed: {escape(", ".join(needed))}. The worksheet shows nothing until these are entered. '
            "No figure is filled in for you.</p>"
        )
    apply_html = ""
    if calc and writable:
        current = str(profile.get("projected_monthly_revenue_base") or "").strip() or "blank"
        apply_html = (
            "<h2>Use it in your working draft</h2>"
            f"<p>Your monthly base revenue in the draft is <strong>{escape(current)}</strong>. The worksheet's monthly figure is "
            f"<strong>{_n(calc['monthly_revenue'])}</strong>. Applying it changes only that field. It does not run Analyze, and the official "
            "result stays as it is until you run Analyze yourself.</p>"
            f'<form method="post" action="/assessments/{_id(record)}/revenue-worksheet">'
            + "".join(f'<input type="hidden" name="{escape(k)}" value="{escape(str(v))}">' for k, v in form.items() if k != "op")
            + '<input type="hidden" name="op" value="apply">'
            '<label class="inline"><input type="checkbox" name="confirm" value="yes"> Replace my monthly base revenue with this figure.</label>'
            '<button type="submit">Apply</button></form>'
        )
    saved_note = (
        f'<p class="muted">Saved worksheet last updated {escape(str(saved["updated_at"]))}.</p>' if saved else ""
    )
    body = (
        banner
        + _official_strip(record)
        + f'<div class="adv-note"><strong>Proposed.</strong> {escape(rw.PROPOSED_LABEL)}</div>'
        + saved_note
        + "<p>The official formula counts one cover per occupied seat per day and splits your operating days 5/7 weekday and 2/7 weekend. "
        "This worksheet counts each service period, seat turns, and the days you are really open, then shows the difference.</p>"
        + form_html
        + result_html
        + apply_html
    )
    return _shell(record, "Proposed restaurant revenue worksheet", "revenue-worksheet", body)


def _comparison_html(comparison: dict[str, Any], calc: dict[str, Any]) -> str:
    if comparison["error"]:
        return f'<p class="adv-note">The official calculation could not run: {escape(comparison["error"])}</p>'
    if comparison["official"] is None:
        names = {
            "seats": "seats",
            "average_ticket": "average ticket",
            "weekday_occupancy": "weekday occupancy",
            "weekend_occupancy": "weekend occupancy",
            "operating_days": "operating days",
        }
        wanted = ", ".join(names[key] for key in comparison["missing"])
        return f'<p class="adv-note">To compare with the official calculation, enter {escape(wanted)} in your draft first.</p>'
    steps = comparison["steps"]
    peak = max(step["value"] for step in steps) or 1.0
    rows = "".join(
        f"<tr><td>{escape(step['label'])}</td><td class=\"num\">{_n(step['value'])}</td>"
        f'<td><svg width="160" height="12" role="img" aria-label="{escape(step["label"])}"><rect width="{max(1, step["value"] / peak * 160):.0f}" height="12" fill="#A88958"></rect></svg></td>'
        f"<td>{escape(step['note'])}</td></tr>"
        for step in steps
    )
    difference = comparison["difference"]
    pct = comparison["difference_pct"]
    verdict = (
        f"The worksheet is {_n(abs(difference))} {'above' if difference >= 0 else 'below'} the official figure"
        + (f" ({abs(pct):.0f}%)" if pct is not None else "")
        + "."
    )
    cap = ""
    if comparison["beyond_official_cap"]:
        cap = (
            f'<p class="adv-note">This worksheet assumes {calc["covers_per_seat_per_open_day"]:.2f} covers per seat per open day. '
            "The official formula cannot exceed one occupied seat per day. Turn rates above one need evidence from a comparable place.</p>"
        )
    cash = ""
    if comparison.get("cash_flow"):
        flow = comparison["cash_flow"]
        cash = (
            f'<p>Cash flow before debt service: official {_n(flow["official"])}, proposed {_n(flow["proposed"])}. '
            f'{escape(flow["basis"])} Other revenue is multiplied by the same margin, so enter it at a margin you expect.</p>'
        )
    return (
        "<h2>Compared with the official calculation</h2>"
        f'<div class="adv-table"><table><thead><tr><th>Step</th><th class="num">Yearly revenue</th><th></th><th>What changes</th></tr></thead><tbody>{rows}</tbody></table></div>'
        f"<p><strong>{escape(verdict)}</strong> The official result is not changed by this page.</p>{cap}{cash}"
    )


# ---------------------------------------------------------------------------
# Improve feasibility
# ---------------------------------------------------------------------------

_GROUPS = (
    ("Venue size and build", ("seats", "construction_cost", "equipment", "soft_costs", "preopening_working_capital", "contingency_pct")),
    ("Cash and financing", ("debt_share", "annual_interest_rate", "amortization_years")),
    ("Revenue", ("average_ticket", "weekday_occupancy", "weekend_occupancy", "operating_days")),
    ("Operating costs", ("annual_fixed_costs", "contribution_margin", "downside_multiplier")),
)
_METRIC_ROWS = (
    ("total_project_cost", "Total project cost", _n),
    ("debt", "Debt", _n),
    ("equity", "Your equity", _n),
    ("annual_debt_service", "Loan payments, per year", _n),
    ("base_revenue", "Expected sales", _n),
    ("base_cash_flow", "Base cash flow before debt service", _n),
    ("base_dscr", "Loan coverage, typical year", _x),
    ("downside_cash_flow", "Downside cash flow before debt service", _n),
    ("downside_dscr", "Loan coverage, weaker year", _x),
    ("break_even_revenue", "Sales needed to break even", _n),
)


def preset_form(preset: dict[str, Any]) -> dict[str, str]:
    form = {f"ov_{key}": improve._plain(value) for key, value in preset["overrides"].items()}
    if preset.get("scale"):
        form["scale_with_size"] = "on"
    if preset.get("derive"):
        form["derive_debt_from_cash"] = "on"
    if preset.get("cash") is not None:
        form["cash_contribution"] = improve._plain(preset["cash"])
    form["name"] = preset["title"]
    return form


def _bars(title: str, rows: list[tuple[str, float | None]], reference: float | None = None, fmt: Any = _x) -> str:
    values = [value for _label, value in rows if value is not None]
    top = max([*values, reference or 0, 0.01])
    height = 26 * len(rows) + 28
    width = 560
    left = 170
    scale = (width - left - 70) / top
    parts = [f'<svg class="adv-chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
             f'<text x="8" y="16" font-size="12" font-weight="600" fill="#263746">{escape(title)}</text>']
    for index, (label, value) in enumerate(rows):
        y = 28 + index * 26
        shown = max(0.0, value or 0.0)
        good = reference is not None and value is not None and value >= reference
        color = "#2e6b3a" if good else "#A88958"
        parts.append(f'<text x="8" y="{y + 12}" font-size="11" fill="#263746">{escape(label[:26])}</text>')
        parts.append(f'<rect x="{left}" y="{y}" width="{max(1.0, shown * scale):.0f}" height="16" fill="{color}"></rect>')
        parts.append(f'<text x="{left + shown * scale + 6:.0f}" y="{y + 12}" font-size="11" fill="#263746">{escape(fmt(value))}</text>')
    if reference is not None:
        x = left + reference * scale
        parts.append(f'<line x1="{x:.0f}" y1="22" x2="{x:.0f}" y2="{height - 2}" stroke="#7a2e2e" stroke-dasharray="3 3"></line>')
    parts.append("</svg>")
    return "".join(parts)


def _compare_table(base_metrics: dict[str, Any], items: list[dict[str, Any]]) -> str:
    head = "<th>Measure</th><th class=\"num\">Your draft</th>" + "".join(
        f'<th class="num">{escape(item["name"] or "Scenario")}</th>' for item in items
    )
    rows = []
    for key, label, fmt in _METRIC_ROWS:
        cells = f'<td class="num">{fmt(base_metrics.get(key))}</td>'
        for item in items:
            metrics = item["metrics"]
            if not metrics:
                cells += '<td class="num">n/a</td>'
                continue
            value = metrics.get(key)
            old = base_metrics.get(key)
            tone = ""
            if isinstance(value, (int, float)) and isinstance(old, (int, float)) and value != old:
                higher_is_better = key in {"base_revenue", "base_cash_flow", "base_dscr", "downside_cash_flow", "downside_dscr"}
                lower_is_better = key in {"annual_debt_service", "total_project_cost", "break_even_revenue"}
                if higher_is_better or lower_is_better:
                    better = (value > old) == higher_is_better
                    tone = ' class="num adv-good"' if better else ' class="num adv-bad"'
            cells += f"<td{tone or ' class=num'}>{fmt(value)}</td>"
        rows.append(f"<tr><th scope=\"row\">{escape(label)}</th>{cells}</tr>")
    return f'<div class="adv-table"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def _scenario_notes(scenario: dict[str, Any], base: dict[str, Any]) -> str:
    changed = [key for key in scenario["changed"] if key != "available_cash"]
    parts = []
    if changed or "available_cash" in scenario["changed"]:
        lines = []
        for key in scenario["changed"]:
            if key == "available_cash":
                lines.append(f"<li>{escape(improve.LABELS[key])}: {escape(_n(base['cash']))} → {escape(_n(scenario['cash']))}</li>")
            else:
                lines.append(f"<li>{escape(improve.LABELS[key])}: {escape(improve._plain(base['inputs'][key]))} → {escape(improve._plain(scenario['inputs'][key]))} (you changed this)</li>")
        parts.append("<p><strong>You changed</strong></p><ul>" + "".join(lines) + "</ul>")
    if scenario["dependent"]:
        parts.append(
            "<p><strong>Recalculated from supported relationships</strong></p><ul>"
            + "".join(
                f"<li>{escape(improve.LABELS[item['field']])}: {escape(improve._plain(item['from']))} → {escape(improve._plain(item['to']))}, {escape(item['relationship'])}</li>"
                for item in scenario["dependent"]
            )
            + "</ul>"
        )
    if scenario["needs"]:
        parts.append(
            "<p><strong>Needs your verification</strong></p><ul>"
            + "".join(f"<li>{escape(item['field'])}: {escape(item['verify'])}</li>" for item in scenario["needs"])
            + "</ul>"
        )
    return "".join(parts)


def improve_page(
    record: dict[str, Any],
    saved: list[dict[str, Any]],
    form: dict[str, str],
    *,
    writable: bool,
    notice: str = "",
    errors: list[str] | None = None,
) -> str:
    errors = list(errors or [])
    profile = record.get("profile") or {}
    banner = f'<div class="banner">{escape(notice)}</div>' if notice else ""
    if errors:
        banner += '<div class="banner" role="alert">' + "<br>".join(escape(item) for item in errors) + "</div>"
    try:
        target = float(form.get("target") or improve.TARGETS[0])
    except ValueError:
        target = improve.TARGETS[0]
    if target not in improve.TARGETS:
        target = improve.TARGETS[0]
    try:
        step = float(form.get("step") or 0.25)
    except ValueError:
        step = 0.25
    if not 0.05 <= step <= 0.6:
        step = 0.25
    official = improve.explain_official(record)
    head = banner + f'<div class="adv-note"><strong>{escape(improve.NOT_APPROVED)}</strong></div>' + _official_strip(record)
    explain = _explain_html(official, _id(record))
    base = improve.base_inputs(profile)
    if base["missing"]:
        labels = ", ".join(improve.LABELS[key] for key in base["missing"])
        body = (
            head
            + explain
            + "<h2>Scenarios need the startup numbers</h2>"
            + f"<p>These are not entered yet: {escape(labels)}. A scenario changes your own numbers, so it needs them first. "
            + f'<a href="/assessments/{_id(record)}">Open your draft</a>, or this record may be a monthly-only or demonstration record.</p>'
        )
        return _shell(record, "Improve feasibility", "improve", body)
    base_metrics, base_error = improve.evaluate(base["inputs"])
    if base_metrics is None:
        body = head + explain + f'<div class="banner" role="alert">The working numbers cannot be calculated yet: {escape(base_error)}</div>'
        return _shell(record, "Improve feasibility", "improve", body)

    findings = improve.financial_findings(base_metrics, target)
    gap = improve.gap(base["inputs"], base_metrics, base["cash"], target)
    target_links = " ".join(
        f'<a href="/assessments/{_id(record)}/improve?target={value:g}"{" class=on" if value == target else ""}>{value:g}×{" (readiness default)" if value == improve.TARGETS[0] else " (lender oriented)"}</a>'
        for value in improve.TARGETS
    )
    stats = "".join(
        f'<div class="adv-stat"><b>{fmt(base_metrics[key])}</b><span>{escape(label)}</span></div>'
        for key, label, fmt in (
            ("total_project_cost", "Total project cost", _n),
            ("annual_debt_service", "Loan payments, per year", _n),
            ("base_dscr", "Loan coverage, typical year", _x),
            ("downside_dscr", "Loan coverage, weaker year", _x),
            ("base_revenue", "Expected sales", _n),
            ("break_even_revenue", "Sales needed to break even", _n),
        )
    )
    finding_html = (
        "<ul>" + "".join(f"<li>{escape(line)}</li>" for line in findings) + "</ul>"
        if findings
        else "<p>Under your assumptions the working numbers meet the coverage level used here. The official result can still be unfavorable for evidence reasons.</p>"
    )
    placeholders = [improve.LABELS[key] for key in base["placeholders"]]
    placeholder_note = (
        f'<p class="muted">Still blank, or at RUGD\'s starting numbers: {escape(", ".join(placeholders))}. These are not market figures. Confirm or replace each one.</p>'
        if placeholders
        else ""
    )
    cash_row = (
        f"<td class=\"num\">{_n(gap['base']['gap_vs_cash'])}</td><td class=\"num\">{_n(gap['downside']['gap_vs_cash'])}</td>"
        if base["cash"] is not None
        else '<td class="num" colspan="2">Enter the cash you can put in to see this</td>'
    )
    gap_table = (
        '<div class="adv-table"><table><thead><tr><th>At '
        + f"{target:g}× coverage</th><th class=\"num\">Base case</th><th class=\"num\">Downside case</th></tr></thead><tbody>"
        f"<tr><th scope=\"row\">Cash flow before debt service</th><td class=\"num\">{_n(gap['base']['cash_flow'])}</td><td class=\"num\">{_n(gap['downside']['cash_flow'])}</td></tr>"
        f"<tr><th scope=\"row\">Yearly shortfall against debt service</th><td class=\"num\">{_n(gap['base']['annual_shortfall'])}</td><td class=\"num\">{_n(gap['downside']['annual_shortfall'])}</td></tr>"
        f"<tr><th scope=\"row\">Debt the cash flow can carry</th><td class=\"num\">{_n(gap['base']['debt_capacity'])}</td><td class=\"num\">{_n(gap['downside']['debt_capacity'])}</td></tr>"
        f"<tr><th scope=\"row\">Funding needed from you</th><td class=\"num\">{_n(gap['base']['owner_funding_needed'])}</td><td class=\"num\">{_n(gap['downside']['owner_funding_needed'])}</td></tr>"
        f"<tr><th scope=\"row\">Gap against the cash you entered</th>{cash_row}</tr>"
        "</tbody></table></div>"
        f"<p class=\"muted\">Revenue short of break-even: {_n(gap['revenue_gap'])} a year. Debt capacity uses the same level-payment method as the main assessment. "
        "A lender, not this page, decides what debt is available.</p>"
    )

    preset_items = improve.presets(base["inputs"], base_metrics, base["cash"], target, step)
    preset_html = "".join(
        '<div class="adv-preset">'
        f'<h3>{escape(item["title"])}</h3><p>{escape(item["basis"])}</p>'
        f'<p><a class="button" href="/assessments/{_id(record)}/improve?target={target:g}&amp;step={step:g}&amp;preset={escape(item["id"])}#draft">Try this scenario</a>'
        f'{"" if item["solved"] else " <span class=adv-tag>What-if, not solved</span>"}</p></div>'
        for item in preset_items
    )
    preset_key = form.get("preset") or ""
    chosen = next((item for item in preset_items if item["id"] == preset_key), None)
    values: dict[str, str] = {}
    if form.get("op") in {"calculate", "save"}:
        values = {
            key: value
            for key, value in form.items()
            if key.startswith("ov_") or key in {"cash_contribution", "name", "scale_with_size", "derive_debt_from_cash"}
        }
    elif chosen:
        values = preset_form(chosen)
    elif form.get("scenario"):
        found = next((item for item in saved if str(item.get("id")) == form["scenario"]), None)
        if found:
            data = improve.recompute(found)
            for key in data["changed"] + [entry["field"] for entry in data["dependent"]]:
                if key == "available_cash":
                    if data["cash"] is not None:
                        values["cash_contribution"] = improve._plain(float(data["cash"]))
                elif key in data["inputs"]:
                    values[f"ov_{key}"] = improve._plain(data["inputs"][key])
            values["name"] = data["name"]
    draft = None
    if values and not errors:
        _base, draft, draft_errors = improve.scenario_from_form(profile, values)
        errors.extend(draft_errors)
        if draft_errors:
            head += '<div class="banner" role="alert">' + "<br>".join(escape(item) for item in draft_errors) + "</div>"

    def field(key: str) -> str:
        current = improve._plain(base["inputs"][key])
        placeholder_text = "placeholder " + current if key in base["placeholders"] else "now " + current
        return (
            f'<label for="ov-{key}">{escape(improve.LABELS[key])}<small>{escape(placeholder_text)}</small></label>'
            f'<input id="ov-{key}" name="ov_{key}" value="{escape(values.get("ov_" + key, ""))}" inputmode="decimal" placeholder="no change">'
        )

    groups = "".join(
        f'<fieldset><legend>{escape(title)}</legend><div class="adv-form-grid">{"".join(field(key) for key in keys)}</div></fieldset>'
        for title, keys in _GROUPS
    )
    cash_now = "not entered" if base["cash"] is None else improve._plain(base["cash"])
    buttons = '<button type="submit" name="op" value="calculate">Calculate</button>'
    if writable:
        buttons += '<button type="submit" name="op" value="save" class="ghost">Save this scenario</button>'
    form_html = (
        f'<form method="post" action="/assessments/{_id(record)}/improve#draft" id="draft">'
        f'<input type="hidden" name="target" value="{target:g}"><input type="hidden" name="step" value="{step:g}">'
        '<p class="muted">Leave a box blank to keep your number. Enter a value to test a change.</p>'
        f"{groups}"
        '<fieldset><legend>Capital and linked changes</legend><div class="adv-form-grid">'
        f'<div><label for="cash-contribution">Cash you can put in<small>now {escape(cash_now)}</small></label>'
        f'<input id="cash-contribution" name="cash_contribution" value="{escape(values.get("cash_contribution", ""))}" inputmode="decimal" placeholder="no change"></div></div>'
        f'<label class="inline"><input type="checkbox" name="scale_with_size" {"checked" if values.get("scale_with_size") else ""}> Scale construction, equipment, and soft costs with seats (same cost per seat)</label>'
        f'<label class="inline"><input type="checkbox" name="derive_debt_from_cash" {"checked" if values.get("derive_debt_from_cash") else ""}> Borrow only what my cash does not cover (sets the debt share)</label>'
        "</fieldset>"
        f'<label for="scenario-name">Name this scenario</label><input id="scenario-name" name="name" value="{escape(values.get("name", ""))}" maxlength="80">'
        f"<div>{buttons}</div></form>"
    )
    draft_html = ""
    if draft and draft["metrics"]:
        draft_gap = improve.gap(draft["inputs"], draft["metrics"], draft["cash"], target)
        meets = draft_gap["meets_target"]["downside"]
        draft_html = (
            "<h3>Draft result</h3>"
            + _compare_table(base_metrics, [draft | {"name": draft["name"] or "Draft"}])
            + _scenario_notes(draft, base)
            + (
                f'<p>Downside coverage reaches {target:g}× in this scenario, under your assumptions.</p>'
                if meets
                else f'<p>Downside coverage stays below {target:g}× in this scenario.</p>'
            )
            + '<p class="adv-note">This is a projection from assumptions you would need to verify. It is not approved.</p>'
        )
    saved_records = [improve.recompute(item) for item in saved]
    saved_html = ""
    if saved_records:
        compare = _compare_table(base_metrics, [item for item in saved_records])
        chart_rows = [("Your draft", base_metrics["downside_dscr"])] + [(item["name"], (item["metrics"] or {}).get("downside_dscr")) for item in saved_records]
        chart = _bars(f"Downside coverage (dashed line is {target:g}×)", chart_rows, target)
        funding_rows = [("Your draft", gap["downside"]["owner_funding_needed"])] + [
            (item["name"], improve.gap(item["inputs"], item["metrics"], item["cash"], target)["downside"]["owner_funding_needed"] if item["metrics"] else None)
            for item in saved_records
        ]
        chart += _bars("Funding needed from you (downside)", funding_rows, None, _n)
        per = []
        for item in saved_records:
            scenario_notes = _scenario_notes(item, base) if item["metrics"] else ""
            applied = "".join(
                f"<li>Applied {escape(str(entry.get('at') or ''))}: "
                + ", ".join(f"{escape(improve.LABELS.get(c['field'], c['field']))} {escape(c['from'] or 'blank')} → {escape(c['to'])}" for c in entry.get("changes") or [])
                + "</li>"
                for entry in item["applied"]
            )
            to_apply = improve.applicable_values(item)
            controls = ""
            if writable:
                preview = "".join(
                    f"<li>{escape(improve.LABELS.get(key, key))}: {escape(str(profile.get(key) or 'blank'))} → {escape(value)}</li>" for key, value in to_apply.items()
                )
                controls = (
                    f'<div class="adv-btn-row"><a class="button ghost" href="/assessments/{_id(record)}/improve?target={target:g}&amp;scenario={escape(str(item["id"]))}#draft">Edit as draft</a>'
                    f'<form method="post" action="/assessments/{_id(record)}/improve"><input type="hidden" name="op" value="delete"><input type="hidden" name="scenario_id" value="{escape(str(item["id"]))}">'
                    '<button type="submit" class="ghost">Delete</button></form>'
                    f'<details><summary>Apply to my working draft</summary><p>These fields in your draft would change:</p><ul>{preview or "<li>Nothing differs from your draft.</li>"}</ul>'
                    "<p>Applying edits your assumptions only. It does not run Analyze, and the official result, flags, and review status stay as they are.</p>"
                    f'<form method="post" action="/assessments/{_id(record)}/improve"><input type="hidden" name="op" value="apply"><input type="hidden" name="scenario_id" value="{escape(str(item["id"]))}">'
                    '<label class="inline"><input type="checkbox" name="confirm" value="yes"> I approve changing these fields in my draft.</label>'
                    '<button type="submit">Apply</button></form></details></div>'
                )
            per.append(
                f'<div class="adv-rec"><h3>{escape(item["name"])}</h3>'
                f'{"<p class=muted>" + escape(item["note"]) + "</p>" if item["note"] else ""}'
                f'<details><summary>What changed and what to verify</summary>{scenario_notes}</details>'
                f'{"<ul>" + applied + "</ul>" if applied else ""}{controls}</div>'
            )
        saved_html = f"<h2>Saved scenarios side by side</h2>{compare}{chart}" + "".join(per)
    else:
        saved_html = "<h2>Saved scenarios</h2><p>None saved yet. Calculate a scenario above, then save it to compare it here.</p>"
    body = (
        head
        + explain
        + f"<h2>Where your working numbers stand</h2><p class=\"muted\">What is loan coverage? {wording.explain('dscr', _id(record))}</p>"
        + f'<div class="adv-grid">{stats}</div>'
        + finding_html
        + placeholder_note
        + f'<p class="muted">Coverage level: {target_links}. The investor-readiness check looks at the weaker year.</p>'
        + f"<h2>Funding and cash-flow gaps</h2><p class=\"muted\">What is break-even? {wording.explain('break_even', _id(record))}</p>"
        + gap_table
        + f"<h2>Realistic alternatives</h2><p class=\"muted\">What is a scenario? {wording.explain('scenario', _id(record))}</p>"
        + f'<p class="muted">Solved options show the arithmetic. What-ifs use a {step * 100:g}% step you can change in the link: add step=0.2 for 20%.</p>'
        + preset_html
        + "<h2>Test your own scenario</h2>"
        + form_html
        + draft_html
        + saved_html
    )
    return _shell(record, "Improve feasibility", "improve", body)


def _explain_html(official: dict[str, Any], aid: str = "") -> str:
    if not official["ran"]:
        return ""
    from app import wording

    def rows(items: list[dict[str, Any]]) -> str:
        out = []
        for item in items:
            found = wording.finding(item["flag"])
            links = " ".join(
                f'<a href="{escape(href)}">{escape(label)}</a>'
                for label, href in (wording.links_for(item["flag"], aid) if aid else [])
            )
            tag = " <span class=\"adv-tag warn\">Holding the assessment back</span>" if item["blocking"] else ""
            out.append(
                f"<li><strong>{escape(found.title)}</strong>{tag}<br>{escape(found.todo)}"
                f"{'<br>' + links if links else ''}"
                '<details class="techref"><summary>Technical reference</summary>'
                f"<p><code>{escape(item['flag'])}</code>. {escape(item['action'])}</p></details></li>"
            )
        return "".join(out) or "<li>Nothing on file.</li>"

    return (
        "<h2>What RUGD found</h2>"
        "<p><strong>Evidence still needed.</strong> A what-if scenario cannot fix these. Only real evidence and an authorized review can.</p>"
        f"<ul>{rows(official['evidence'])}</ul>"
        "<p><strong>Money questions.</strong> Better figures can help here, but only a new Analyze run changes the official result.</p>"
        f"<ul>{rows(official['financial'])}</ul>"
    )
