"""The Edit assumptions workspace, opened from Analyze > Key Numbers.

Four things are always kept apart on this page:

* Official assessment: the result Analyze last stored. Only a new Analyze run changes it.
* Working draft: the assumptions saved in the draft. Saving here changes only these.
* Proposed: edits typed on this page and not saved.
* Preview: figures calculated from the proposed edits. Not saved, not official.
"""

from __future__ import annotations

from html import escape
from typing import Any

from app import assumptions as asm
from app import display as d
from app import field_help, ui, wording
from app.guidance import family_for
from app.pages import _ws_header, layout

_STYLE = """<style>
.asm .asm-legend { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 0.6rem; margin: 0 0 0.9rem; }
.asm .asm-legend > div { background: var(--card); border: 1px solid var(--line); border-top: 4px solid var(--line); border-radius: 12px; padding: 0.55rem 0.75rem; font-size: 0.88rem; }
.asm .asm-legend b { display: block; font-size: 0.95rem; }
.asm .asm-legend .lg-official { border-top-color: var(--ink); }
.asm .asm-legend .lg-draft { border-top-color: var(--bronze); }
.asm .asm-legend .lg-proposed { border-top-color: #C9A24B; border-top-style: dashed; }
.asm .asm-legend .lg-preview { border-top-color: #8aa4b4; border-top-style: dotted; }
.asm .asm-row { display: grid; grid-template-columns: minmax(11rem, 1.4fr) minmax(9rem, 1.1fr) minmax(9rem, 1fr) minmax(9rem, 0.9fr); gap: 0.4rem 0.9rem; padding: 0.7rem 0; border-top: 1px solid var(--line); align-items: start; }
.asm .asm-row:first-of-type { border-top: 0; }
.asm .asm-row > div { min-width: 0; }
.asm .asm-row.asm-changed { background: #FBF6E8; margin: 0 -0.6rem; padding-left: 0.6rem; padding-right: 0.6rem; border-radius: 10px; }
.asm .asm-k { display: block; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--sub); margin: 0 0 0.15rem; font-weight: 600; }
.asm .asm-label .field-label { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.asm .asm-label label { display: inline; margin: 0; font-weight: 650; }
.asm .asm-impact, .asm .asm-links, .asm .asm-hint { font-size: 0.82rem; margin: 0.2rem 0 0; }
.asm .asm-edit input, .asm .asm-basis select { width: 100%; box-sizing: border-box; }
.asm .asm-saved p { margin: 0.1rem 0; font-size: 0.9rem; }
.asm .asm-err { color: #7a2e2e; font-weight: 650; font-size: 0.85rem; margin: 0.25rem 0 0; }
.asm #asm-preview { margin: 0.4rem 0 0; }
.asm .asm-sectionlinks { font-size: 0.88rem; }
.asm .asm-approve { border: 2px solid var(--bronze); border-radius: 14px; padding: 0.8rem 1rem; background: #fff; margin: 0.8rem 0; }
.asm .asm-approve label.asm-check { display: flex; gap: 0.5rem; align-items: flex-start; font-weight: 600; margin: 0.6rem 0; }
.asm .asm-approve label.asm-check input { width: auto; margin-top: 0.2rem; }
.asm ul.asm-list { margin: 0.3rem 0; padding-left: 1.1rem; font-size: 0.9rem; }
@media (max-width: 800px) {
  .asm .asm-row { grid-template-columns: 1fr; }
  .asm .asm-row.asm-changed { margin: 0; }
}
</style>"""

_COMPARE = (
    ("total_project_cost", "Total project cost", "money"),
    ("debt", "Debt financing", "money"),
    ("equity", "Equity required", "money"),
    ("annual_debt_service", "Loan payments per year", "money"),
    ("base_revenue", "Typical-year sales", "money"),
    ("base_cash_flow", "Typical-year cash left before loan payments", "money"),
    ("base_dscr", "Loan coverage, typical year", "multiple"),
    ("downside_dscr", "Loan coverage, weaker year", "multiple"),
    ("break_even_revenue", "Break-even sales per year", "money"),
    ("base_monthly_cash_flow", "Monthly cash flow, typical month", "money"),
    ("downside_monthly_cash_flow", "Monthly cash flow, weaker month", "money"),
    ("break_even_monthly_revenue", "Break-even sales per month", "money"),
    ("months_to_break_even", "Months to recover initial capital", "months"),
)


def _aid(record: dict[str, Any]) -> str:
    return escape(str(record.get("id") or ""))


def _fmt(kind: str, value: float | None, *, missing: str = "Not calculated") -> str:
    if value is None:
        return missing
    if kind == "money":
        return d.money(value, cents=not float(value).is_integer())
    if kind == "multiple":
        return d.multiple(value)
    return d.decimal_text(value, 1, "months")


def _delta(kind: str, before: float | None, after: float | None) -> str:
    if before is None or after is None:
        return "-"
    diff = round(after - before, 4)
    if abs(diff) < 1e-9:
        return "No change"
    sign = "+" if diff > 0 else "-"
    if kind == "money":
        return f"{sign}{d.money(abs(diff), cents=not float(abs(diff)).is_integer())}"
    if kind == "multiple":
        return f"{sign}{abs(diff):.2f}×"
    return f"{sign}{abs(diff):.1f} months"


def _comparison(official: dict[str, float | None], draft: dict[str, float | None], proposed: dict[str, float | None], *, changed: bool) -> str:
    rows = []
    for key, name, kind in _COMPARE:
        if all(source.get(key) is None for source in (official, draft, proposed)):
            continue
        rows.append(
            [
                escape(name),
                escape(_fmt(kind, official.get(key), missing="No official figure")),
                escape(_fmt(kind, draft.get(key))),
                f"<strong>{escape(_fmt(kind, proposed.get(key)))}</strong>",
                escape(_delta(kind, draft.get(key), proposed.get(key)) if changed else "No edits yet"),
            ]
        )
    if not rows:
        return '<p>Nothing can be calculated yet. Enter the startup numbers or the four monthly numbers first.</p>'
    return ui.table(
        ["Measure", "Official assessment", "Working draft", "Proposed (preview)", "Change from working draft"],
        rows,
    )


def _funding_table(draft_run: dict[str, Any], proposed_run: dict[str, Any]) -> str:
    draft = asm.funding_gap(draft_run["measures"], draft_run["cash"])
    proposed = asm.funding_gap(proposed_run["measures"], proposed_run["cash"])
    if not draft["calculated"] and not proposed["calculated"]:
        return (
            '<p>The funding gap is not calculated because the startup cost build is not calculated yet. '
            "Nothing was filled in for you.</p>"
        )

    def cell(gap: dict[str, Any], key: str) -> str:
        if not gap["calculated"]:
            return "Not calculated"
        if key == "cash":
            return d.money(gap["cash"], cents=not float(gap["cash"]).is_integer()) if gap["cash"] is not None else "Not entered"
        if key == "remaining":
            if gap["remaining"] is None:
                return "Not calculated. Enter the cash you can put in."
            if gap["remaining"] == 0:
                return f"None. Your cash covers the equity, with {d.money(gap['left_over'], cents=not float(gap['left_over']).is_integer())} to spare."
            return d.money(gap["remaining"], cents=not float(gap["remaining"]).is_integer())
        return d.money(gap[key], cents=not float(gap[key]).is_integer())

    rows = []
    for key, name in (
        ("total", "Total project cost"),
        ("debt", "Proposed debt financing"),
        ("equity", "Equity required"),
        ("cash", "Your available cash"),
        ("remaining", "Remaining funding requirement"),
    ):
        rows.append([escape(name), escape(cell(draft, key)), f"<strong>{escape(cell(proposed, key))}</strong>"])
    return ui.table(["Funding", "Working draft", "Proposed (preview)"], rows)


def _financing_terms(profile: dict[str, Any]) -> str:
    rows = []
    for key in ("debt_share", "annual_interest_rate", "amortization_years", "contingency_pct"):
        status = asm.field_status(profile, key)
        value = status["text"]
        chip = d.chip(status["state"], {"missing": "Default used", "zero": "Entered as zero", "estimated": "Your estimate", "placeholder": "Starting number"}[status["state"]])
        rows.append([escape(asm.label(key)), f"{escape(value)} {chip}"])
    return ui.table(["Financing assumption", "Value used in this preview"], rows, numeric_from=9)


def _field_errors(errors: dict[str, str]) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{escape(message)}</li>" for message in errors.values())
    return f'<div class="banner" role="alert"><strong>These entries were not used.</strong><ul class="asm-list">{items}</ul></div>'


def _value_text(key: str, text: str) -> str:
    if text == "":
        return "not entered"
    number = asm._num(text)
    return asm.format_value(key, number) if number is not None else text


def _change_rows(changes: list[dict[str, str]]) -> str:
    rows = []
    for item in changes:
        key = item["field"]
        if item["kind"] == "label":
            before, after = _value_text(key, item["from"]), "label only"
            basis = asm.BASIS_LABELS.get(item["basis"], "")
        elif item["kind"] == "cleared":
            before, after, basis = _value_text(key, item["from"]), "cleared (back to not entered)", "-"
        else:
            before, after = _value_text(key, item["from"]), _value_text(key, item["to"])
            basis = asm.BASIS_LABELS.get(item["basis"], "")
        rows.append([escape(item["label"]), escape(before), f"<strong>{escape(after)}</strong>", escape(basis)])
    return ui.table(["Assumption", "Saved now", "Proposed", "Basis"], rows, numeric_from=9)


def panel_html(record: dict[str, Any], view: dict[str, Any], *, writable: bool) -> str:
    """The preview panel. It is safe to send alone as a fragment."""
    aid = _aid(record)
    proposal = view["proposal"]
    changes = proposal["changes"]
    errors = proposal["errors"]
    proposed_run, draft_run = view["proposed_run"], view["draft_run"]
    changed = bool(changes)
    parts = [
        '<div class="dcard" id="preview-card"><h3>Preview '
        f'{d.chip("calculated", "Not saved")}</h3>'
        '<p class="muted">These figures were calculated for this request from the proposed edits, using the same calculation Analyze uses. '
        "They are not saved and they are not official. The official assessment does not change.</p>"
    ]
    parts.append(_field_errors(errors))
    if not changed and not errors:
        parts.append(
            '<p class="dnote">No edits yet. Change a value above and this panel updates. '
            "Until then the proposed column matches your working draft.</p>"
        )
    preview = proposed_run["preview"]
    problems = list(preview["monthly_issues"]) + list(preview["startup_issues"])
    if preview["projection_error"]:
        problems.append(str(preview["projection_error"]))
    if problems:
        parts.append(
            '<p class="flag">Not calculated for the proposed numbers:</p><ul class="asm-list">'
            + "".join(f"<li>{escape(item)}</li>" for item in problems)
            + "</ul>"
        )
    parts.append("<h4>Before and after</h4>" + _comparison(view["official"], draft_run["measures"], proposed_run["measures"], changed=changed))
    if view["official"]:
        parts.append(
            '<p class="muted">Official assessment: what Analyze last stored. A working draft that differs from it is expected after edits. '
            "Only a new Analyze run updates it.</p>"
        )
    else:
        parts.append('<p class="muted">There is no official figure to compare yet. Analyze has not stored a result with these numbers.</p>')
    parts.append("<h4>Funding gap</h4>" + _funding_table(draft_run, proposed_run))
    parts.append(
        '<p class="muted">Remaining funding requirement is the equity required minus the cash you say you can put in, never below zero. '
        "Equity is the part of the total that is not borrowed. Your cash is a balance you hold, so it is compared with equity but is not the same thing. "
        "This does not assume you will commit all of it or set any aside as a reserve. Pre-opening working capital is already inside the total project cost.</p>"
    )
    parts.append("<h4>Financing assumptions in this preview</h4>" + _financing_terms(proposal["profile"]))
    defaults = asm.defaults_used(proposal["profile"])
    if defaults and (proposed_run["preview"]["projection"] or draft_run["preview"]["projection"]):
        parts.append(
            "<h4>Lines counted by default</h4>"
            '<p class="muted">These lines are blank, so the calculation fills them with a built-in default. '
            "A default is not your figure and not a market figure. A blank is not the same as an entered zero.</p>"
            '<ul class="asm-list">'
            + "".join(f"<li><strong>{escape(item['label'])}.</strong> {escape(item['text'])}</li>" for item in defaults)
            + "</ul>"
        )
    parts.append(
        '<p class="dnote"><strong>What this does not do.</strong> Your assumptions are your own and are not verified. '
        "Changing them does not supply customer evidence, clear a serious concern, set human review, or change an official recommendation. "
        "This preview is not a score and not a readiness percentage.</p>"
    )
    parts.append("</div>")
    # Approval
    hypothetical = [item for item in changes if item["basis"] == "hypothetical"]
    if changed and not errors and writable:
        notes = ""
        if hypothetical:
            names = ", ".join(escape(item["label"]) for item in hypothetical)
            notes = f"<p><strong>Hypothetical:</strong> {names}. These will be labeled hypothetical and will not be treated as a benchmark or as verified.</p>"
        parts.append(
            '<div class="asm-approve" id="approve-card"><h3>Review and approve</h3>'
            "<p>You are about to save these changes to your <strong>working draft</strong> only. "
            "The official assessment, flags, and review status stay exactly as they are until you run a new assessment.</p>"
            f"{_change_rows(changes)}{notes}"
            '<label class="asm-check"><input type="checkbox" name="confirm" value="yes"> '
            "I reviewed these changes and approve saving them to my working draft.</label>"
            '<div class="dactions"><button type="submit" name="op" value="apply" class="dbtn">Save to working draft</button></div></div>'
        )
    elif changed and errors:
        parts.append('<p class="dnote">Fix the entries marked above, then preview again. Nothing can be saved until every entry is valid.</p>')
    elif changed and not writable:
        parts.append('<p class="dnote">You can preview changes here, but this record is read-only, so they cannot be saved to it.</p>')
    return "".join(parts)


def _basis_select(key: str, view: dict[str, Any]) -> str:
    chosen = view["proposal"]["choices"].get(key, "")
    current = asm._saved_text(view["record"].get("profile") or {}, key)
    options = []
    if current and not asm.stored_basis(view["basis"], view["record"].get("profile") or {}, key) and not chosen:
        options.append(("", "Basis not recorded"))
    options += [(value, text) for value, text in asm.BASIS_LABELS.items()]
    selected = chosen or ("" if options[0][0] == "" else "estimate")
    rendered = "".join(
        f'<option value="{escape(value)}"{" selected" if value == selected else ""}>{escape(text)}</option>' for value, text in options
    )
    saved = asm.stored_basis(view["basis"], view["record"].get("profile") or {}, key) or ("" if current else "estimate")
    return f'<select id="b_{escape(key)}" name="b_{escape(key)}" data-saved="{escape(saved)}">{rendered}</select>'


def _row(record: dict[str, Any], view: dict[str, Any], key: str) -> str:
    aid = _aid(record)
    profile = record.get("profile") or {}
    field = asm.FIELDS[key]
    status = asm.field_status(profile, key)
    saved_basis = asm.stored_basis(view["basis"], profile, key)
    chip_text = {"missing": "Missing", "zero": "Entered as zero", "estimated": "Your estimate", "placeholder": "Starting number"}[status["state"]]
    saved_html = (
        f'<p>{escape(status["text"])}</p>'
        if status["state"] != "estimated"
        else f'<p><strong>{escape(status["text"])}</strong></p>'
    )
    chips = d.chip(status["state"], chip_text)
    if saved_basis:
        chips = f'<span class="dchip dchip-{escape(saved_basis)}" title="{escape(asm.BASIS_EXPLAINED[saved_basis])}">{escape(asm.BASIS_LABELS[saved_basis])}</span>'
    raw = view["proposal"]["values"].get(key, "")
    changed = any(item["field"] == key for item in view["proposal"]["changes"])
    error = view["proposal"]["errors"].get(key, "")
    help_label = field_help.label_with_help(key, field.label, profile, for_id=f"a_{key}", suffix="-asm") if field_help.has_help(key) else f'<label for="a_{escape(key)}">{escape(field.label)}</label>'
    error_html = f'<p class="asm-err" role="alert">{escape(error)}</p>' if error else ""
    return (
        f'<div class="asm-row{" asm-changed" if changed else ""}" id="row-{escape(key)}">'
        f'<div class="asm-label">{help_label}<p class="asm-impact muted">{escape(field.impact)}</p>'
        f'<p class="asm-links no-print"><a href="/assessments/{aid}/benchmarks">Benchmarks</a> · <a href="/assessments/{aid}/improve">Improve</a></p></div>'
        f'<div class="asm-saved"><span class="asm-k">In your working draft</span>{saved_html}<p>{chips}</p></div>'
        f'<div class="asm-edit"><label class="asm-k" for="a_{escape(key)}">New value</label>'
        f'<input id="a_{escape(key)}" name="a_{escape(key)}" type="text" inputmode="decimal" autocomplete="off" value="{escape(raw)}" '
        f'data-saved="{escape(asm._saved_text(profile, key))}"'
        f'{" aria-invalid=\"true\"" if error else ""}>'
        f'<span class="muted asm-hint">{escape(field.hint)}</span>{error_html}</div>'
        f'<div class="asm-basis"><label class="asm-k" for="b_{escape(key)}">Basis</label>{_basis_select(key, view)}</div>'
        "</div>"
    )


def _section(record: dict[str, Any], view: dict[str, Any], section: tuple[str, str, str, tuple[str, ...]]) -> str:
    sid, title, note, keys = section
    rows = "".join(_row(record, view, key) for key in keys)
    return f'<section class="dcard" id="{sid}"><h3>{escape(title)}</h3><p class="muted">{escape(note)}</p>{rows}</section>'


def _history(record: dict[str, Any], saved: list[dict[str, Any]], official: list[dict[str, Any]]) -> str:
    parts = []
    if saved:
        items = []
        for entry in reversed(saved[-10:]):
            payload = entry.get("payload") or {}
            lines = []
            for change in payload.get("changes") or []:
                key = str(change.get("field") or "")
                if key not in asm.FIELDS:
                    continue
                if change.get("kind") == "label":
                    lines.append(f"{asm.label(key)}: label set to {asm.BASIS_LABELS.get(str(change.get('basis')), 'none')}")
                    continue
                basis = asm.BASIS_LABELS.get(str(change.get("basis") or ""), "")
                before, after = _value_text(key, str(change.get("from") or "")), _value_text(key, str(change.get("to") or ""))
                lines.append(f"{asm.label(key)}: {before} to {after}" + (f" ({basis})" if basis else ""))
            if lines:
                body = '<ul class="asm-list">' + "".join(f"<li>{escape(line)}</li>" for line in lines) + "</ul>"
                items.append(f'<li><strong>{ui.when(entry.get("created_at"))}</strong>{body}</li>')
        if items:
            parts.append('<h4>Changes saved to the working draft</h4><ul class="asm-list">' + "".join(items) + "</ul>")
    if not parts:
        parts.append('<p class="muted">No assumption changes have been saved from this page yet.</p>')
    history_rows = []
    for index, entry in enumerate(official[:8]):
        result = entry["result"]
        values = asm.official_measures(result)
        label = "Current official result" if entry.get("superseded_at") is None else "Previous official result"
        when = ui.when(entry.get("saved_at"), missing="date not recorded")
        replaced = f", replaced {ui.when(entry.get('superseded_at'))}" if entry.get("superseded_at") else ""
        history_rows.append(
            [
                f"<strong>{escape(label)}</strong><br><span class=\"muted\">Saved {when}{replaced}</span>",
                escape(wording.official_line(result)),
                escape(_fmt("money", values.get("total_project_cost"), missing="Not calculated")),
                escape(_fmt("multiple", values.get("downside_dscr"))),
            ]
        )
    if history_rows:
        parts.append(
            "<h4>Official results kept</h4>"
            '<p class="muted">Each time a new assessment is run, the result it replaces is kept here. Nothing is overwritten without a copy.</p>'
            + ui.table(["Result", "Where it stood", "Total project cost", "Weaker-year coverage"], history_rows, numeric_from=2)
        )
    return f'<div class="dcard" id="history"><h3>History</h3>{"".join(parts)}</div>'


_SCRIPT = """<script>
(function () {
  var form = document.getElementById("asm-form");
  var box = document.getElementById("asm-preview");
  if (!form || !box || !window.fetch) return;
  var timer = null;
  function collect() {
    var params = new URLSearchParams();
    Array.prototype.forEach.call(form.elements, function (node) {
      if (!node.name || node.type === "checkbox" || node.type === "submit") return;
      params.set(node.name, node.value || "");
    });
    params.set("op", "calculate");
    params.set("fragment", "1");
    return params;
  }
  function refresh() {
    box.setAttribute("aria-busy", "true");
    fetch(form.getAttribute("action"), {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: collect().toString(),
      credentials: "same-origin"
    }).then(function (response) {
      return response.text().then(function (text) {
        if (response.ok) box.innerHTML = text;
        else box.innerHTML = '<p class="flag">The preview is not available to this session. Nothing was changed.</p>';
        box.removeAttribute("aria-busy");
      });
    }).catch(function () {
      box.innerHTML = '<p class="flag">The preview could not be calculated. Nothing was changed.</p>';
      box.removeAttribute("aria-busy");
    });
  }
  function mark(node) {
    var row = node.closest ? node.closest(".asm-row") : null;
    if (!row) return;
    var changed = false;
    Array.prototype.forEach.call(row.querySelectorAll("[data-saved]"), function (field) {
      var saved = field.getAttribute("data-saved"), now = field.value.trim();
      var a = parseFloat(saved.replace(/[$,]/g, "")), b = parseFloat(now.replace(/[$,]/g, ""));
      if (field.tagName === "INPUT" && !isNaN(a) && !isNaN(b) ? a !== b : now !== saved) changed = true;
    });
    row.classList.toggle("asm-changed", changed);
  }
  function schedule() { window.clearTimeout(timer); timer = window.setTimeout(refresh, 350); }
  function onEdit(event) {
    if (event.target && event.target.name && /^(a|b)_/.test(event.target.name)) {
      mark(event.target);
      schedule();
    }
  }
  form.addEventListener("input", onEdit);
  form.addEventListener("change", onEdit);
})();
</script>"""


def assumptions_page(
    record: dict[str, Any],
    view: dict[str, Any],
    *,
    writable: bool,
    saved_changes: list[dict[str, Any]],
    official_history: list[dict[str, Any]],
    notice: str = "",
    errors: list[str] | None = None,
    stale: list[str] | None = None,
) -> str:
    aid = _aid(record)
    name = str(record.get("business_name") or (record.get("profile") or {}).get("business_name") or "Your business")
    profile = record.get("profile") or {}
    banner = f'<div class="banner">{escape(notice)}</div>' if notice else ""
    if errors:
        banner += '<div class="banner" role="alert">' + "<br>".join(escape(item) for item in errors) + "</div>"
    if stale:
        names = ", ".join(escape(asm.label(key)) for key in stale)
        banner += (
            '<div class="banner" id="draft-differs"><strong>Your working draft is different from the official assessment.</strong> '
            f"Assumptions changed since the last Analyze run: {names}. The official figures still show the earlier numbers until you run a new assessment.</div>"
        )
    legend = (
        '<div class="asm-legend" aria-label="What each figure on this page means">'
        '<div class="lg-official"><b>Official assessment</b>What Analyze last stored. Only a new Analyze run changes it.</div>'
        '<div class="lg-draft"><b>Working draft</b>The assumptions saved in your draft. Saving here changes only these.</div>'
        '<div class="lg-proposed"><b>Proposed</b>Edits typed on this page. Not saved until you approve.</div>'
        '<div class="lg-preview"><b>Preview</b>Figures calculated from the proposed edits. Not saved, not official.</div>'
        "</div>"
    )
    hypothetical = asm.hypothetical_fields(view["basis"], profile)
    hyp_note = ""
    if hypothetical:
        hyp_note = (
            '<p class="dnote"><strong>Hypothetical values in your draft:</strong> '
            + escape(", ".join(asm.label(key) for key in hypothetical))
            + ". They are planning figures you chose, not benchmarks and not verified.</p>"
        )
    example = asm.example_for(profile) if writable else {}
    example_html = ""
    if example:
        names = ", ".join(escape(asm.label(key)) for key in example)
        example_html = (
            '<div class="dcard" id="example"><h3>Do not have these figures yet?</h3>'
            f"<p>{escape(asm.EXAMPLE_NOTE)}</p>"
            f"<p>The example fills only the blank lines ({names}) in the form below and labels them hypothetical. "
            "It does not touch your saved draft.</p>"
            '<div class="dactions"><button type="submit" name="op" value="example" class="dbtn dbtn-ghost">Fill blank lines with the restaurant example</button></div></div>'
        )
    elif writable and family_for(str(profile.get("industry") or "")) == "hospitality":
        example_html = (
            '<p class="muted">The restaurant example only fills blank lines, and equipment, soft costs, and pre-opening working capital already have values in your draft.</p>'
        )
    sections = "".join(_section(record, view, section) for section in asm.SECTIONS)
    read_only_note = ""
    if not writable:
        read_only_note = ui.callout(
            "You can try changes and see a preview here. This record is read-only for your account, so nothing can be saved to it.",
            tone="warn",
            strong="Preview only.",
        )
    form = (
        f'<form class="dform" id="asm-form" method="post" action="/assessments/{aid}/assumptions" autocomplete="off">'
        f'<input type="hidden" name="base" value="{escape(view["stamp"])}">'
        '<button type="submit" name="op" value="calculate" tabindex="-1" aria-hidden="true" '
        'style="position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden">Preview changes</button>'
        f"{example_html}{sections}"
        '<div class="dactions"><button type="submit" name="op" value="calculate" class="dbtn">Preview changes</button>'
        f'<a class="dbtn dbtn-ghost" href="/assessments/{aid}/assumptions">Discard edits</a></div>'
        f'<div id="asm-preview" aria-live="polite">{panel_html(record, view, writable=writable)}</div>'
        "</form>"
    )
    run_card = ""
    if writable:
        run_card = (
            '<div class="dcard" id="run-new"><h3>Run a new assessment</h3>'
            "<p>Saving assumptions never changes the official assessment. When you want the official result to reflect your working draft, "
            "run a new assessment yourself. The result it replaces is kept in History.</p>"
            f'<form method="post" action="/assessments/{aid}/analyze"><div class="dactions">'
            '<button type="submit" class="dbtn dbtn-ghost">Run a new assessment with my working draft</button></div></form></div>'
        )
    links = (
        f'<p class="asm-sectionlinks">Related: <a href="/assessments/{aid}/benchmarks">Benchmarks</a> · '
        f'<a href="/assessments/{aid}/improve">Improve</a> · <a href="/assessments/{aid}/revenue-worksheet">Revenue worksheet</a> · '
        f'<a href="/assessments/{aid}/results#key-numbers">Back to Key Numbers</a></p>'
    )
    guide = (
        '<div class="dcard"><h3>How to use this page</h3>'
        "<p>Change the assumptions behind the numbers. Total project cost, debt, equity, coverage, and break-even are calculated, so they have no box here. "
        "Pick a basis for each figure you change so it is never mistaken for something checked.</p>"
        "<p class=\"muted\">A sourced benchmark is a figure with a named source, saved under Benchmarks. A hypothetical value is an illustration you chose. "
        "RUGD never presents a hypothetical value as a benchmark, and no benchmark is loaded for you here.</p></div>"
    )
    header = _ws_header(
        record,
        "Edit assumptions",
        "analyze",
        subtitle=f"{name}: change the assumptions behind the Key Numbers, preview the effect, and approve before anything is saved.",
    )
    body = ui.plain_page(
        f'{header}<div class="asm">{banner}{legend}{read_only_note}{hyp_note}{guide}{form}{run_card}{_history(record, saved_changes, official_history)}{links}</div>',
        root_id="assumptions-workspace",
    )
    return layout("Edit assumptions", f"{_STYLE}{body}{_SCRIPT}", active="/assessments")
