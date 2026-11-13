"""Shared page design for every RUGD workspace.

These are presentation helpers only. They format and arrange values that a page already
has. They never compute a score, clear a flag, change a stored value, or set human review.
The Analyze dashboard introduced them. Every other workspace now reuses them.
"""

from __future__ import annotations

from html import escape

ICONS = {
    "shield": '<path d="M12 3l8 3v5c0 5-3.4 8.400-8 10-4.600-1.600-8-5-8-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "cost": '<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.500"/><path d="M6 9v.01M18 15v.01"/>',
    "loan": '<path d="M4 20h16M6 20V10M10 20V10M14 20V10M18 20V10M3 10l9-6 9 6z"/>',
    "gauge": '<path d="M4 17a8 8 0 1116 0"/><path d="M12 17l4-5"/>',
    "chart": '<path d="M4 20V4M4 20h16"/><path d="M8 16v-5M12 16V8M16 16v-3"/>',
    "scale": '<path d="M12 4v16M6 20h12M5 8h14"/><path d="M5 8l-3 6a3 3 0 006 0zM19 8l-3 6a3 3 0 006 0z"/>',
    "seat": '<path d="M7 11V6a2 2 0 012-2h6a2 2 0 012 2v5"/><path d="M5 11h14v5H5zM7 16v4M17 16v4"/>',
    "bulb": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 00-3.500 10.900c.6.500 1 1.200 1 2.100h5c0-.9.400-1.600 1-2.100A6 6 0 0012 3z"/>',
    "book": '<path d="M5 4h10a3 3 0 013 3v13H8a3 3 0 01-3-3z"/><path d="M5 17a3 3 0 013-3h10"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "doc": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
}


def icon(name: str) -> str:
    return (
        '<svg class="dicon" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, "")}</svg>'
    )



ICONS.update(
    {
        "home": '<path d="M4 11l8-7 8 7"/><path d="M6 10v10h12V10"/>',
        "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.500-4.500"/>',
        "chat": '<path d="M4 5h16v11H9l-5 4z"/>',
        "check": '<circle cx="12" cy="12" r="8"/><path d="M8.500 12.500l2.500 2.500 4.500-5"/>',
        "flag": '<path d="M6 21V4M6 5h11l-2 4 2 4H6"/>',
        "slides": '<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M9 21h6M12 17v4"/>',
        "pulse": '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
        "wrench": '<path d="M14 6a4 4 0 005 5l-8 8a2 2 0 01-3-3z"/><path d="M14 6l-1-3 3 1"/>',
        "plan": '<path d="M5 4h14v16H5z"/><path d="M8 9h8M8 13h8M8 17h5"/>',
        "user": '<circle cx="12" cy="8" r="3.500"/><path d="M5 20c0-4 3-6 7-6s7 2 7 6"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
    }
)


def help_tip(
    title: str,
    *,
    means: str,
    how: str,
    source: str,
    assumptions: str,
    limits: str,
) -> str:
    """A compact help control. It explains a figure and never changes it."""
    rows = "".join(
        f"<p><strong>{label}.</strong> {escape(text)}</p>"
        for label, text in (
            ("What it means", means),
            ("How it is calculated", how),
            ("Where it came from", source),
            ("Assumptions used", assumptions),
            ("Limits", limits),
        )
        if text
    )
    return (
        '<details class="dh">'
        f'<summary aria-label="About {escape(title)}"><span aria-hidden="true">?</span></summary>'
        f'<div class="dh-body"><p class="dh-title">{escape(title)}</p>{rows}</div></details>'
    )




def kpi(icon_name: str, label: str, value: str, sub: str, href: str = "", *, help_html: str = "", chip_html: str = "", tone: str = "") -> str:
    """A KPI card. A link that starts with # moves between tabs. No href means no link."""
    link = ""
    if href:
        link = f'<a class="dk-link" href="{escape(href)}"{" data-goto" if href.startswith("#") else ""}>Details</a>'
    return (
        f'<div class="dk{f" dk-{tone}" if tone else ""}">'
        f'<div class="dk-head">{icon(icon_name)}<span class="dk-label">{escape(label)}</span>{help_html}</div>'
        f'<p class="dk-value">{escape(value)}</p>'
        f'<p class="dk-sub">{chip_html}{escape(sub)}</p>{link}</div>'
    )

def table(headers: list[str], rows: list[list[str]], *, numeric_from: int = 1) -> str:
    head = "".join(f'<th scope="col"{" class=num" if i >= numeric_from else ""}>{escape(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(
            (f'<th scope="row">{cell}</th>' if i == 0 else f'<td{" class=num" if i >= numeric_from else ""}>{cell}</td>')
            for i, cell in enumerate(row)
        ) + "</tr>"
        for row in rows
    )
    return f'<div class="dtable"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def bars(rows: list[tuple[str, float | None, str]], *, reference: tuple[float, str] | None = None, unit_label: str = "") -> str:
    """Horizontal bars from real values. A missing value draws no bar and says so."""
    values = [value for _label, value, _text in rows if value is not None]
    if not values:
        return ""
    low = min([0.0, *values] + ([reference[0]] if reference else []))
    high = max([0.0, *values] + ([reference[0]] if reference else []))
    span = (high - low) or 1.0

    def pos(value: float) -> float:
        return (value - low) / span * 100

    zero = pos(0.0)
    out = []
    for label, value, text in rows:
        if value is None:
            out.append(
                f'<div class="dbar"><span class="dbar-l">{escape(label)}</span><span class="dbar-t dbar-none"></span>'
                f'<span class="dbar-v">{escape(text)}</span></div>'
            )
            continue
        left = min(zero, pos(value))
        width = max(abs(pos(value) - zero), 0.6)
        negative = " dbar-neg" if value < 0 else ""
        ref = (
            f'<i class="dbar-ref" style="left:{pos(reference[0]):.2f}%" title="{escape(reference[1])}"></i>'
            if reference
            else ""
        )
        out.append(
            f'<div class="dbar"><span class="dbar-l">{escape(label)}</span>'
            f'<span class="dbar-t"><i class="dbar-zero" style="left:{zero:.2f}%"></i>'
            f'<i class="dbar-fill{negative}" style="left:{left:.2f}%;width:{width:.2f}%"></i>{ref}</span>'
            f'<span class="dbar-v">{escape(text)}</span></div>'
        )
    note = f'<p class="muted dbar-note">{escape(unit_label)}</p>' if unit_label else ""
    return f'<div class="dbars" role="group">{"".join(out)}{note}</div>'




# ---------------------------------------------------------------------------
# Page building blocks shared by every workspace
# ---------------------------------------------------------------------------


def simple_help(title: str, text: str, *, more: str = "") -> str:
    """A "?" control with one or two plain paragraphs. It explains and never changes a value."""
    extra = f"<p>{escape(more)}</p>" if more else ""
    return (
        '<details class="dh">'
        f'<summary aria-label="About {escape(title)}"><span aria-hidden="true">?</span></summary>'
        f'<div class="dh-body"><p class="dh-title">{escape(title)}</p><p>{escape(text)}</p>{extra}</div></details>'
    )


def when(value: object, *, missing: str = "not recorded") -> str:
    """A stored ISO timestamp in everyday words. The stored value is kept in the datetime attribute."""
    from datetime import datetime, timedelta

    raw = str(value or "").strip()
    if not raw:
        return escape(missing)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return escape(raw)
    text = f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}, {parsed.strftime('%H:%M')}"
    if parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0):
        text += " UTC"
    return f'<time datetime="{escape(raw)}">{escape(text)}</time>'


def pill(label: str, tone: str = "plain") -> str:
    return f'<span class="dpill dpill-{escape(tone)}">{escape(label)}</span>'


def tag(label: str, tone: str = "") -> str:
    return f'<span class="dtag{f" dtag-{escape(tone)}" if tone else ""}">{escape(label)}</span>'


def goto_links(links: list[tuple[str, str]], *, label: str = "Related workspaces") -> str:
    inner = "".join(f'<a href="{escape(href)}">{escape(text)}</a>' for text, href in links)
    return f'<nav class="dgoto no-print" aria-label="{escape(label)}">{inner}</nav>'


def page_header(
    title: str,
    *,
    subtitle: str = "",
    eyebrow: str = "",
    chips: tuple[str, ...] | list[str] = (),
    actions: str = "",
    help_html: str = "",
    links: str = "",
    header_id: str = "",
) -> str:
    """The same top block on every page: title, one line of context, status chips, and the main action."""
    eye = f'<p class="deyebrow">{escape(eyebrow)}</p>' if eyebrow else ""
    sub = f'<p class="dsub">{escape(subtitle)} {help_html}</p>' if subtitle else (f'<p class="dsub">{help_html}</p>' if help_html else "")
    chip_row = f'<p class="dlabel">{"".join(chips)}</p>' if chips else ""
    act = f'<div class="dactions dhead-actions no-print">{actions}</div>' if actions else ""
    ident = f' id="{escape(header_id)}"' if header_id else ""
    return (
        f'<header class="dpagehead"{ident}>'
        f'<div class="dpagehead-main">{eye}<h1>{escape(title)}</h1>{sub}{chip_row}</div>'
        f"{links}{act}</header>"
    )


WORKSPACES: tuple[tuple[str, str, str], ...] = (
    ("explore", "Explore", ""),
    ("research", "Research", "/intelligence"),
    ("analyze", "Analyze", "/results"),
    ("improve", "Improve", "/improve"),
    ("plan", "Business plan", "/plans"),
    ("deck", "Pitch deck", "/decks"),
    ("reports", "Reports", "/reports"),
    ("adviser", "Adviser", "/advice"),
    ("actions", "Action Center", "/actions"),
    ("pulse", "Market Pulse", "/pulse"),
)


def workspace_nav(assessment_id: str, current: str = "") -> str:
    """One row that moves between a business's workspaces. The current one is marked."""
    aid = escape(str(assessment_id))
    links = []
    for key, label, suffix in WORKSPACES:
        mark = ' aria-current="page" class="on"' if key == current else ""
        links.append(f'<a href="/assessments/{aid}{suffix}"{mark}>{escape(label)}</a>')
    return (
        '<nav class="dws no-print" id="journey-nav" aria-label="Business workflow">'
        + "".join(links)
        + "</nav>"
    )


def callout(text: str, *, tone: str = "note", strong: str = "") -> str:
    lead = f"<strong>{escape(strong)}</strong> " if strong else ""
    return f'<p class="dnote dnote-{escape(tone)}" role="note">{lead}{escape(text)}</p>'


def empty_state(title: str, text: str, *, action_html: str = "", icon_name: str = "doc") -> str:
    act = f'<div class="dactions">{action_html}</div>' if action_html else ""
    return (
        f'<div class="dempty">{icon(icon_name)}<div><p class="dempty-t">{escape(title)}</p>'
        f'<p class="muted">{escape(text)}</p>{act}</div></div>'
    )


def card(title: str, body: str, *, help_html: str = "", cls: str = "", icon_name: str = "") -> str:
    ico = icon(icon_name) if icon_name else ""
    head = f"<h3>{ico}{escape(title)} {help_html}</h3>" if title else ""
    return f'<div class="dcard {escape(cls)}">{head}{body}</div>'


def kpi_grid(items: list[str]) -> str:
    return f'<div class="dkpis">{"".join(items)}</div>'


def stat(label: str, value: str, sub: str = "", *, icon_name: str = "chart", tone: str = "", help_html: str = "", href: str = "") -> str:
    """A KPI card. Without an href there is no Details link."""
    link = f'<a class="dk-link" href="{escape(href)}"{" data-goto" if href.startswith("#") else ""}>Details</a>' if href else ""
    return (
        f'<div class="dk{f" dk-{tone}" if tone else ""}">'
        f'<div class="dk-head">{icon(icon_name)}<span class="dk-label">{escape(label)}</span>{help_html}</div>'
        f'<p class="dk-value">{escape(value)}</p>'
        f'<p class="dk-sub">{escape(sub)}</p>{link}</div>'
    )


def details(summary: str, body: str, *, tight: bool = False, open_: bool = False, cls: str = "") -> str:
    return (
        f'<details class="dmore{" dmore-tight" if tight else ""} {escape(cls)}"{" open" if open_ else ""}>'
        f"<summary>{escape(summary)}</summary>{body}</details>"
    )


def item_card(
    title: str,
    *,
    href: str = "",
    eyebrow: str = "",
    meta: str = "",
    chips: str = "",
    body: str = "",
    actions: str = "",
    icon_name: str = "doc",
    cls: str = "",
    item_id: str = "",
) -> str:
    """A list item for a saved thing: an assessment, report, plan, deck, action, or research project."""
    name = f'<a href="{escape(href)}">{escape(title)}</a>' if href else escape(title)
    eye = f'<p class="deyebrow">{escape(eyebrow)}</p>' if eyebrow else ""
    meta_html = f'<p class="muted ditem-meta">{meta}</p>' if meta else ""
    chip_html = f'<p class="dlabel">{chips}</p>' if chips else ""
    act = f'<div class="dactions ditem-actions">{actions}</div>' if actions else ""
    ident = f' id="{escape(item_id)}"' if item_id else ""
    return (
        f'<article class="ditem {escape(cls)}"{ident}>'
        f'<div class="ditem-ico">{icon(icon_name)}</div>'
        f'<div class="ditem-body">{eye}<h3 class="ditem-t">{name}</h3>{meta_html}{chip_html}{body}{act}</div></article>'
    )


def button(label: str, href: str, *, ghost: bool = False, small: bool = False) -> str:
    cls = "dbtn" + (" dbtn-ghost" if ghost else "") + (" dbtn-small" if small else "")
    return f'<a class="{cls}" href="{escape(href)}">{escape(label)}</a>'


def tabbed(root_id: str, sections: tuple[tuple[str, str], ...], panels: dict[str, str], *, header: str = "", after: str = "", aria: str = "Sections") -> str:
    """Hash-driven tabs. Without scripting every panel is in the page, and printing shows every panel."""
    tabs = "".join(
        f'<a href="#{key}" data-tab="{key}"{" aria-current=\"true\"" if i == 0 else ""}>{escape(label)}</a>'
        for i, (key, label) in enumerate(sections)
    )
    body = "".join(
        f'<section class="dpanel" id="{key}" data-panel="{key}" aria-labelledby="{key}-h">'
        f'<h2 id="{key}-h" class="dpanel-h">{escape(label)}</h2>{panels.get(key, "")}</section>'
        for key, label in sections
    )
    return (
        f'<div class="dash" id="{escape(root_id)}" data-tabbed>{header}'
        f'<nav class="dtabs no-print" aria-label="{escape(aria)}">{tabs}</nav>{body}{after}</div>'
    )


def plain_page(content: str, *, root_id: str = "") -> str:
    """Wrap a non-tabbed page in the shared design scope."""
    ident = f' id="{escape(root_id)}"' if root_id else ""
    return f'<div class="dash"{ident}>{content}</div>'


EXTRA_STYLE = """
:root { --card: #FFFEFB; --line: #E4DFD3; --soft: #FBF9F4; --sub: #5c6b76; --bad: #8a3030; --ok: #2e6b3a; }
.dpagehead { display: flex; flex-wrap: wrap; gap: 0.5rem 1.4rem; align-items: flex-start; justify-content: space-between; margin: 0 0 0.4rem; }
.dpagehead-main { min-width: 0; flex: 1 1 22rem; }
.dpagehead h1 { font-size: 1.75rem; margin: 0 0 0.25rem; letter-spacing: -0.02em; }
.dsub { margin: 0 0 0.4rem; color: var(--sub); }
.dhead-actions { margin: 0.2rem 0 0; }
.dws, main #journey-nav.dws { display: flex; flex-direction: row; flex-wrap: nowrap; gap: 0.3rem; overflow-x: auto; padding: 0.3rem 0; margin: 0.5rem 0 0.4rem; scrollbar-width: thin; }
#journey-context { margin: 0 0 0.8rem; }
.dws a, main #journey-nav.dws a { flex: 0 0 auto; text-decoration: none; color: var(--ink); background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 0.35rem 0.85rem; font-size: 0.88rem; white-space: nowrap; }
.dws a:hover, main #journey-nav.dws a:hover { background: #F1E9D8; color: var(--ink); }
.dws a.on, main #journey-nav.dws a.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.dnote-warn { background: #F6E7CB; border-left-color: #D9BE88; }
.dempty { display: flex; gap: 0.8rem; align-items: flex-start; background: var(--card); border: 1px dashed #cfc9bb; border-radius: 16px; padding: 1rem 1.2rem; margin: 0.4rem 0 0.9rem; }
.dempty-t { font-weight: 600; margin: 0 0 0.2rem; }
.dempty .muted { margin: 0.1rem 0; }
.ditems { display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr)); gap: 0.8rem; margin: 0.4rem 0 1rem; align-items: start; }
.ditem { display: flex; gap: 0.8rem; background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 0.95rem 1.05rem; margin: 0; }
.ditem-ico { flex: 0 0 auto; padding-top: 0.15rem; }
.ditem-body { min-width: 0; flex: 1; }
.ditem-t { margin: 0 0 0.15rem; font-size: 1.05rem; display: block; overflow-wrap: anywhere; }
.ditem-t a { color: var(--ink); text-decoration-color: var(--bronze); }
.ditem p { margin: 0.25rem 0; }
.ditem-meta { font-size: 0.86rem; }
.ditem-actions { margin: 0.5rem 0 0; }
.ditem-list { display: block; }
.ditem-list .ditem { margin: 0 0 0.7rem; }
.dsection-t { font-size: 1.15rem; margin: 1.4rem 0 0.4rem; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
.dform label { display: block; margin: 0.75rem 0 0.2rem; font-weight: 600; font-size: 0.9rem; color: #33434f; }
.dform input, .dform select, .dform textarea { border: 1px solid #cfc9bb; border-radius: 10px; padding: 0.6rem 0.8rem; font-size: 0.97rem; background: #fff; }
.dform textarea { min-height: 5rem; }
.dform button, .dash button.dbtn { border-radius: 999px; padding: 0.55rem 1.15rem; cursor: pointer; }
.dform .dactions { margin-top: 0.9rem; }
.dstep { display: flex; gap: 0.4rem; list-style: none; padding: 0; margin: 0.4rem 0 0.9rem; flex-wrap: wrap; }
.dstep li { flex: 1 1 8rem; background: var(--card); border: 1px solid var(--line); border-top: 4px solid var(--line); border-radius: 12px; padding: 0.5rem 0.7rem; font-size: 0.9rem; font-weight: 600; text-align: center; }
.dstep li.done { border-top-color: var(--bronze); }
.dstep li.current { border-top-color: var(--bronze); background: #F1E9D8; }
.dash .banner, main .banner { border-radius: 12px; }
.dash .dtable table { width: 100%; }
.dpagehead .dpill { font-size: 0.85rem; padding: 0.2rem 0.7rem; }
.dpagehead .dlabel { margin: 0.3rem 0 0; }
.ditem-links { margin: 0.3rem 0; padding-left: 1.1rem; font-size: 0.92rem; }
.ditem-links li { margin: 0.2rem 0; }
.ditem form { display: inline; }
.dkpis-tight { grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); }
.ditems-wide { grid-template-columns: repeat(auto-fill, minmax(26rem, 1fr)); }
main .journey { gap: 0.35rem; margin: 0.6rem 0 0.4rem; }
main .journey li { border-radius: 12px; border-color: var(--line); border-top-color: var(--line); background: var(--card); font-size: 0.88rem; }
main .journey li.current { background: #F1E9D8; border-top-color: var(--bronze, #A88958); }
main .journey li.done { border-top-color: var(--bronze, #A88958); }
main .journey.card-journey li { padding: 0.3rem 0.4rem; font-size: 0.8rem; }
main .badge { border-radius: 999px; padding: 0.2rem 0.7rem; font-size: 0.82rem; }
main .glance { gap: 0.7rem; }
main .glance p { border-radius: 14px; border-color: var(--line); border-top-width: 1px; border-top-color: var(--line); background: var(--card); }
main .ditem .badges { margin: 0.3rem 0; }
main .ditem .status-line { font-size: 0.92rem; color: var(--sub); }
main .ditem .card-action { margin: 0.5rem 0 0.3rem; align-items: center; }
main .ditem-links-row { font-size: 0.9rem; color: var(--sub); }
main .dpurpose, main .dwords, main .dstarters { margin: 0.6rem 0; }
main .plan-nav { display: flex; flex-direction: row; flex-wrap: nowrap; gap: 0.4rem; overflow-x: auto; padding: 0.3rem 0 0.5rem; margin: 0.4rem 0 1rem; position: sticky; top: 0; background: var(--ivory, #F5F2EB); z-index: 2; scrollbar-width: thin; }
main .plan-nav a { position: static; flex: 0 0 auto; white-space: nowrap; color: var(--ink); border: 1px solid var(--line); border-radius: 999px; background: var(--card); padding: 0.28rem 0.75rem; font-size: 0.86rem; text-decoration: none; }
main .plan-nav a:hover { border-color: var(--bronze, #A88958); background: #F1E9D8; color: var(--ink); }
main .slide { border-radius: 16px; border: 1px solid var(--line); border-top: 6px solid var(--bronze, #A88958); background: var(--card); aspect-ratio: auto; min-height: 12rem; overflow: visible; }
main .slide textarea { min-height: 5.5rem; }
main .slide-actions button { padding: 0.25rem 0.8rem; font-size: 0.85rem; background: transparent; color: var(--ink, #263746); border: 1px solid var(--line); }
main .adviser-log { list-style: none; padding: 0; margin: 0.6rem 0; display: flex; flex-direction: column; gap: 0.5rem; }
main .adviser-log li { border: 1px solid var(--line); border-left: 1px solid var(--line); border-radius: 16px; padding: 0.65rem 0.9rem; background: var(--card); max-width: 46rem; }
main .adviser-log li.you { align-self: flex-end; background: #EEF1F4; }
main .adviser-log li.adviser { align-self: flex-start; }
main .adviser-log li.you { border-left-color: var(--line); }
main .adviser-log li p { margin: 0.15rem 0; }
@media (max-width: 800px) {
  .dpagehead h1 { font-size: 1.45rem; }
  .ditems { grid-template-columns: 1fr; }
}
@media print {
  .dws { display: none !important; }
}
"""

LEGACY_STYLE = """
main .card, main details.more { border-radius: 16px; border-color: #E4DFD3; background: #FFFEFB; }
main .banner { border-radius: 12px; padding: 0.55rem 0.9rem; font-size: 0.9rem; }
main h2 { border-bottom-color: #E4DFD3; }
main table { border-radius: 12px; overflow: hidden; }
main .button, main button { border-radius: 999px; }
main .button.primary { padding: 0.6rem 1.2rem; }
main input, main select, main textarea { border-radius: 10px; border-color: #cfc9bb; }
main details.plain > summary { color: #4d5b66; }
main input[type=checkbox], main input[type=radio] { width: auto; display: inline-block; margin: 0 0.5rem 0 0; vertical-align: middle; }
"""


_BASE_STYLE = """<style>
main:has(.dash) { max-width: 1180px; }
.dash { --card: #FFFEFB; --line: #E4DFD3; --soft: #FBF9F4; --sub: #5c6b76; --bad: #8a3030; --ok: #2e6b3a; }
.dash h1 { font-size: 1.75rem; margin: 0 0 0.4rem; }
.dash h2.dpanel-h { border: 0; margin: 0 0 0.8rem; font-size: 1.3rem; padding: 0; }
.dash h3 { margin: 0 0 0.5rem; font-size: 1.02rem; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
.dash .muted { color: var(--sub); }
.dash code { font-size: 0.78rem; background: var(--soft); border: 1px solid var(--line); border-radius: 6px; padding: 0.05rem 0.35rem; overflow-wrap: anywhere; }
.dicon { flex: 0 0 auto; color: var(--bronze); }
.dhead { display: flex; flex-wrap: wrap; gap: 0.4rem 1.2rem; align-items: baseline; justify-content: space-between; }
.dgoto { display: flex; flex-direction: row; flex-wrap: wrap; gap: 0.25rem 0.9rem; padding: 0; font-size: 0.88rem; }
.dgoto a { color: var(--ink); text-decoration: none; border: 0; border-bottom: 1px solid var(--line); padding: 0.1rem 0; }
.dgoto a:hover { background: transparent; border-bottom-color: var(--bronze); }
.dtabs { position: sticky; top: 0; z-index: 4; display: flex; flex-direction: row; flex-wrap: nowrap; gap: 0.3rem; overflow-x: auto; background: var(--ivory); padding: 0.55rem 0; margin: 0.6rem 0 1rem; border-bottom: 1px solid var(--line); scrollbar-width: thin; }
.dtabs a { flex: 0 0 auto; text-decoration: none; color: var(--ink); background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 0.45rem 1rem; font-weight: 500; font-size: 0.93rem; white-space: nowrap; }
.dtabs a:hover { background: #F1E9D8; }
.dtabs a[aria-current="true"] { background: var(--ink); color: #fff; border-color: var(--ink); }
.js-dash .dpanel[hidden] { display: none; }
.dpanel { margin-bottom: 1.4rem; scroll-margin-top: 4rem; }
.js-dash .dpanel-h { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.dcard, .dstatus, .dk, .dtile, .drec { background: var(--card); border: 1px solid var(--line); border-radius: 16px; }
.dcard { padding: 1rem 1.15rem; margin: 0 0 0.9rem; }
.dcard p { margin: 0.35rem 0; }
.dstatus { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 1.2rem; padding: 1.25rem 1.4rem; margin-bottom: 0.9rem; border-top: 4px solid var(--bronze); }
.deyebrow { display: flex; align-items: center; gap: 0.4rem; margin: 0 0 0.3rem; font-size: 0.74rem; letter-spacing: 0.07em; text-transform: uppercase; color: #6f5a33; font-weight: 600; }
.dlabel { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.2rem 0 0.5rem; }
.dpill { display: inline-block; border-radius: 999px; padding: 0.3rem 0.85rem; font-weight: 600; font-size: 0.95rem; background: var(--soft); border: 1px solid var(--line); }
.dpill-warn { background: #F6E7CB; border-color: #D9BE88; color: #5b4519; font-size: 1.1rem; }
.dreason { margin: 0.35rem 0; }
.dstanding { background: var(--soft); border-left: 4px solid var(--bronze); border-radius: 0 10px 10px 0; padding: 0.55rem 0.8rem; margin: 0.7rem 0 0; font-size: 0.92rem; }
.dfacts { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin: 0; align-content: start; }
.dfact { background: var(--soft); border: 1px solid var(--line); border-radius: 12px; padding: 0.55rem 0.7rem; }
.dfact dt { font-size: 0.76rem; color: var(--sub); display: flex; align-items: center; gap: 0.3rem; flex-wrap: wrap; }
.dfact dd { margin: 0.15rem 0 0; font-weight: 600; overflow-wrap: anywhere; }
.dkpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 0.7rem; margin: 0 0 0.9rem; }
.dk { padding: 0.85rem 1rem; }
.dk-head { display: flex; align-items: center; gap: 0.4rem; color: var(--sub); font-size: 0.86rem; }
.dk-label { flex: 1; }
.dk-value { font-size: 1.65rem; font-weight: 650; letter-spacing: -0.02em; margin: 0.3rem 0 0.1rem; overflow-wrap: anywhere; }
.dk-sub { margin: 0; font-size: 0.82rem; color: var(--sub); }
.dk-link { font-size: 0.82rem; color: var(--ink); }
.dk-bad .dk-value { color: var(--bad); }
.dk-ok .dk-value { color: var(--ok); }
.dtiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: 0.7rem; margin: 0 0 0.9rem; }
.dtile { display: flex; flex-direction: column; gap: 0.15rem; padding: 0.85rem 1rem; text-decoration: none; color: var(--ink); }
.dtile:hover { border-color: var(--bronze); background: #FBF6EA; }
.dtile-t { font-weight: 600; }
.dtile-v { font-size: 0.93rem; }
.dgrid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr)); gap: 0.9rem; align-items: start; }
.dgaps { margin: 0.2rem 0; padding-left: 1.1rem; }
.dgaps li { margin: 0.3rem 0; }
.dmini { margin: 0.5rem 0; }
.dnext { border-left: 4px solid var(--bronze); }
.dh { display: inline; margin: 0; }
.dh > summary { list-style: none; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; width: 1.35rem; height: 1.35rem; border-radius: 50%; border: 1.5px solid #8c7a55; background: #fff; color: #6f5a33; font-size: 0.78rem; font-weight: 700; line-height: 1; }
.dh > summary::-webkit-details-marker { display: none; }
.dh[open] > summary, .dh > summary:hover { background: #F1E9D8; }
.dh-body { display: block; flex-basis: 100%; margin: 0.5rem 0 0.2rem; padding: 0.7rem 0.95rem; background: var(--soft); border: 1px solid var(--line); border-radius: 12px; font-size: 0.88rem; font-weight: 400; color: #33434f; text-align: left; letter-spacing: 0; white-space: normal; }
.dh-body p { margin: 0.35rem 0; }
.dh-title { font-weight: 650; }
.dk .dh[open] { display: block; flex-basis: 100%; }
.dtable { overflow-x: auto; margin: 0.4rem 0; }
.dtable table { margin: 0; min-width: 18rem; font-size: 0.9rem; background: transparent; }
.dtable th, .dtable td { padding: 0.4rem 0.55rem; border-bottom: 1px solid var(--line); vertical-align: top; }
.dtable thead th { background: var(--ink); color: #fff; font-weight: 600; }
.dtable tbody th { background: transparent; color: var(--ink); font-weight: 500; text-align: left; }
.dtable tr:nth-child(even) td { background: transparent; }
.dtable .num { text-align: right; white-space: nowrap; }
.dchip { display: inline-block; font-size: 0.7rem; padding: 0.02rem 0.45rem; border-radius: 999px; border: 1px solid var(--line); background: var(--soft); color: #4d5b66; margin-left: 0.25rem; vertical-align: middle; white-space: nowrap; }
.dchip-calculated { background: #E8EFF3; border-color: #C5D3DC; }
.dchip-placeholder, .dchip-missing { background: #F6E7CB; border-color: #D9BE88; color: #5b4519; }
.dchip-zero { background: #EEEAE0; }
.dchip-benchmark { background: #EFE9F4; border-color: #D3C6DF; }
.dtag { display: inline-block; font-size: 0.74rem; padding: 0.05rem 0.5rem; margin: 0 0.3rem 0.2rem 0; background: var(--stone); border-radius: 999px; }
.dtag-warn { background: #f1dcc0; }
.dtag-bad { background: #e8c4c4; }
.dbars { margin: 0.6rem 0 0.2rem; }
.dbar { display: grid; grid-template-columns: minmax(6.5rem, 9rem) minmax(0, 1fr) minmax(4.5rem, auto); gap: 0.6rem; align-items: center; margin: 0.35rem 0; font-size: 0.86rem; }
.dbar-t { position: relative; height: 0.85rem; background: #F0ECE2; border-radius: 999px; overflow: hidden; }
.dbar-fill { position: absolute; top: 0; bottom: 0; background: var(--bronze); border-radius: 999px; }
.dbar-neg { background: #b04a4a; }
.dbar-zero { position: absolute; top: 0; bottom: 0; width: 1px; background: #8a8577; z-index: 1; }
.dbar-ref { position: absolute; top: -2px; bottom: -2px; border-left: 2px dashed var(--ink); z-index: 2; }
.dbar-v { text-align: right; font-weight: 600; white-space: nowrap; }
.dbar-none { background: transparent; border: 1px dashed var(--line); }
.dbar-note { font-size: 0.8rem; margin: 0.3rem 0 0; }
.dbig { font-size: 1.6rem; font-weight: 650; margin: 0.2rem 0; overflow-wrap: anywhere; }
.dnote { background: var(--soft); border-left: 4px solid var(--bronze); border-radius: 0 10px 10px 0; padding: 0.5rem 0.8rem; font-size: 0.9rem; }
.dverdict { display: flex; gap: 0.7rem; align-items: flex-start; background: #F6E7CB; border: 1px solid #D9BE88; border-radius: 14px; padding: 0.8rem 1rem; margin: 0 0 0.9rem; }
.dverdict-ok { background: #E4F0E6; border-color: #B7D3BC; }
.dbm { border-top: 1px solid var(--line); padding: 0.65rem 0; }
.dbm:first-of-type { border-top: 0; }
.dbm p { margin: 0.2rem 0; }
.dbm-top { display: flex; justify-content: space-between; gap: 0.8rem; flex-wrap: wrap; }
.dbm-val { font-weight: 650; }
.dactions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.4rem 0 1rem; }
.dbtn { display: inline-block; text-decoration: none; background: var(--ink); color: #fff; border-radius: 999px; padding: 0.55rem 1.1rem; font-size: 0.92rem; margin: 0; }
.dbtn:hover { background: #34495a; color: #fff; }
.dbtn-ghost { background: var(--card); color: var(--ink); border: 1px solid #cfc9bb; }
.dbtn-ghost:hover { background: #F1E9D8; color: var(--ink); }
.dbtn-small { padding: 0.35rem 0.85rem; font-size: 0.85rem; margin: 0 0.4rem 0.3rem 0; }
.drec { display: flex; gap: 0.9rem; padding: 0.95rem 1.1rem; margin: 0 0 0.8rem; }
.drec-n { flex: 0 0 2rem; height: 2rem; border-radius: 50%; background: var(--ink); color: #fff; display: grid; place-items: center; font-weight: 600; }
.drec-body { min-width: 0; flex: 1; }
.drec-body p { margin: 0.3rem 0; }
.drec-caveat { font-size: 0.82rem; }
.dmore { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 0.2rem 1rem; margin: 0.9rem 0; }
.dmore > summary { cursor: pointer; padding: 0.6rem 0; font-weight: 600; }
.dmore-tight { border: 0; background: transparent; padding: 0; margin: 0.3rem 0; }
.dmore-tight > summary { padding: 0.2rem 0; font-weight: 500; font-size: 0.9rem; color: #4d5b66; }
@media (max-width: 800px) {
  .dstatus { grid-template-columns: 1fr; padding: 1rem; }
  .dbar { grid-template-columns: 1fr minmax(4rem, auto); }
  .dbar-t { grid-column: 1 / -1; grid-row: 2; }
  .dbar-v { grid-row: 1; grid-column: 2; }
  .drec { padding: 0.8rem; }
  .dk-value { font-size: 1.4rem; }
}
@media print {
  .dtabs, .dgoto { display: none !important; }
  .js-dash .dpanel[hidden] { display: block; }
  .js-dash .dpanel-h { position: static; width: auto; height: auto; clip: auto; }
}
</style>"""


STYLE = _BASE_STYLE[: -len("</style>")] + EXTRA_STYLE + LEGACY_STYLE + "</style>"


SCRIPT = """<script>
(function () {
  var root = document.querySelector('.dash[data-tabbed]');
  if (!root) { return; }
  var tabs = Array.prototype.slice.call(root.querySelectorAll('.dtabs a[data-tab]'));
  var panels = Array.prototype.slice.call(root.querySelectorAll('.dpanel'));
  var ids = panels.map(function (p) { return p.id; });
  document.documentElement.classList.add('js-dash');
  function panelFor(hash) {
    var id = (hash || '').replace(/^#/, '');
    if (!id) { return { panel: ids[0], anchor: '' }; }
    if (ids.indexOf(id) >= 0) { return { panel: id, anchor: '' }; }
    var el = document.getElementById(id);
    var host = el && el.closest ? el.closest('.dpanel') : null;
    return host ? { panel: host.id, anchor: id } : { panel: ids[0], anchor: '' };
  }
  function show(hash, fromUser) {
    var target = panelFor(hash);
    panels.forEach(function (p) { p.hidden = p.id !== target.panel; });
    tabs.forEach(function (t) {
      if (t.getAttribute('data-tab') === target.panel) {
        t.setAttribute('aria-current', 'true');
        var bar = t.parentNode;
        if (bar && bar.scrollWidth > bar.clientWidth) { bar.scrollLeft = Math.max(0, t.offsetLeft - 12); }
      }
      else { t.removeAttribute('aria-current'); }
    });
    var scrollTo = target.anchor ? document.getElementById(target.anchor) : null;
    if (scrollTo) { scrollTo.scrollIntoView(); }
    else if (fromUser) { root.scrollIntoView(); }
  }
  window.addEventListener('hashchange', function () { show(location.hash, true); });
  root.addEventListener('click', function (event) {
    var link = event.target.closest ? event.target.closest('a[data-tab], a[data-goto]') : null;
    if (!link) { return; }
    var href = link.getAttribute('href') || '';
    if (href.charAt(0) !== '#') { return; }
    event.preventDefault();
    if (location.hash === href) { show(href, true); } else { location.hash = href; }
  });
  show(location.hash, false);
}());
</script>"""
