"""PowerPoint and PDF exports from a saved deck. Figures are copied, not recalculated."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from app.deck import DISCLAIMER, included_slides

LOGO = Path(__file__).resolve().parent / "static" / "rugd-logo.png"
_INK = (0x26, 0x37, 0x46)
_BRONZE = (0xA8, 0x89, 0x58)
_IVORY = (0xF5, 0xF2, 0xEB)
_SLATE = (0x27, 0x32, 0x3B)
_EXPORT_LIMIT = 700


def powerpoint_bytes(deck: dict[str, Any], *, title: str) -> bytes:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    blank = presentation.slide_layouts[6]
    slides = included_slides(deck)
    for index, slide_data in enumerate(slides, start=1):
        slide = presentation.slides.add_slide(blank)
        _pptx_bar(slide, presentation, MSO_SHAPE, RGBColor)
        _pptx_text(
            slide,
            Inches(0.55),
            Inches(0.28),
            Inches(10.5),
            Inches(0.9),
            str(slide_data.get("title") or "Slide"),
            Pt(30),
            bold=True,
            RGBColor=RGBColor,
        )
        _pptx_text(
            slide,
            Inches(0.55),
            Inches(1.2),
            Inches(7.4),
            Inches(3.3),
            _export_text(str(slide_data.get("narrative") or "")),
            Pt(16),
            bold=False,
            RGBColor=RGBColor,
        )
        facts = "\n".join(str(item) for item in (slide_data.get("facts") or [])[:8])
        if facts:
            _pptx_text(
                slide,
                Inches(8.1),
                Inches(1.2),
                Inches(4.6),
                Inches(3.2),
                facts,
                Pt(13),
                bold=False,
                RGBColor=RGBColor,
            )
        _pptx_chart(slide, deck, slide_data)
        _pptx_text(
            slide,
            Inches(0.55),
            Inches(6.85),
            Inches(10.2),
            Inches(0.45),
            f"{index}  ·  {DISCLAIMER}",
            Pt(10),
            bold=False,
            RGBColor=RGBColor,
        )
        if LOGO.is_file() and index in {1, len(slides)}:
            slide.shapes.add_picture(str(LOGO), Inches(11.55), Inches(0.22), height=Inches(0.48))
    if not slides:
        slide = presentation.slides.add_slide(blank)
        _pptx_text(
            slide,
            Inches(0.55),
            Inches(1.2),
            Inches(12),
            Inches(1),
            title or "Pitch deck",
            Pt(28),
            bold=True,
            RGBColor=RGBColor,
        )
    buffer = BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def pdf_bytes(deck: dict[str, Any], *, title: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(unit="in", format=(13.333, 7.5))
    pdf.set_compression(False)
    pdf.set_auto_page_break(False)
    pdf.set_title(title or "Pitch deck")
    slides = included_slides(deck)
    if not slides:
        slides = [{"title": title or "Pitch deck", "narrative": DISCLAIMER, "facts": [], "chart": None}]
    for index, slide_data in enumerate(slides, start=1):
        pdf.add_page()
        pdf.set_fill_color(*_IVORY)
        pdf.rect(0, 0, 13.333, 7.5, style="F")
        pdf.set_fill_color(*_BRONZE)
        pdf.rect(0, 0, 13.333, 0.16, style="F")
        pdf.set_fill_color(*_INK)
        pdf.rect(0, 7.28, 13.333, 0.22, style="F")
        if LOGO.is_file() and index in {1, len(slides)}:
            pdf.image(str(LOGO), x=11.7, y=0.28, h=0.46)
        pdf.set_text_color(*_INK)
        pdf.set_xy(0.5, 0.32)
        pdf.set_font("Helvetica", "B", 26)
        pdf.multi_cell(10.6, 0.38, _pdf_safe(str(slide_data.get("title") or "Slide")))
        pdf.set_font("Helvetica", size=13)
        pdf.set_xy(0.5, 1.35)
        pdf.multi_cell(7.3, 0.26, _pdf_safe(_export_text(str(slide_data.get("narrative") or ""))))
        pdf.set_xy(8.05, 1.35)
        pdf.set_font("Helvetica", size=11)
        facts = "\n".join(_pdf_safe(str(item)) for item in (slide_data.get("facts") or [])[:8])
        if facts:
            pdf.multi_cell(4.7, 0.24, facts)
        _pdf_chart(pdf, deck, slide_data)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(0.4, 7.3)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(12.5, 0.16, _pdf_safe(f"{index}  {DISCLAIMER}")[:180])
    return bytes(pdf.output())


def chart_points(deck: dict[str, Any], chart: str | None) -> list[tuple[str, float]]:
    """Numbers already stored on the deck. Missing values are omitted. Zero stays."""
    figures = deck.get("figures") if isinstance(deck.get("figures"), dict) else {}
    if chart == "cash":
        pairs = (
            ("Monthly revenue", figures.get("assumed_revenue")),
            ("Contribution", figures.get("base_contribution")),
            ("Cash flow", figures.get("base_cash_flow")),
            ("Downside cash flow", figures.get("downside_cash_flow")),
        )
    elif chart == "break_even":
        pairs = (
            ("Entered revenue", figures.get("assumed_revenue")),
            ("Break-even revenue", figures.get("break_even")),
        )
    elif chart == "comparison":
        pairs = (
            ("Base cash flow", figures.get("base_cash_flow")),
            ("Downside cash flow", figures.get("downside_cash_flow")),
        )
    elif chart == "allocation":
        uses = figures.get("uses") if isinstance(figures.get("uses"), list) else []
        pairs = tuple((str(item.get("label") or "Use"), item.get("amount")) for item in uses if isinstance(item, dict))
    else:
        return []
    points = []
    for label, value in pairs:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        points.append((label, float(value)))
    return points


def _export_text(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= _EXPORT_LIMIT:
        return cleaned
    return cleaned[: _EXPORT_LIMIT - 1].rstrip() + "… The full narrative is saved in the workspace."


def _pdf_safe(text: str) -> str:
    return text.encode("latin-1", "replace").decode("latin-1")


def _pptx_bar(slide: Any, presentation: Any, shape_kind: Any, color: Any) -> None:
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, presentation.slide_width, Inches(0.14))
    bar.fill.solid()
    bar.fill.fore_color.rgb = color(*_BRONZE)
    bar.line.fill.background()


def _pptx_text(
    slide: Any,
    left: Any,
    top: Any,
    width: Any,
    height: Any,
    text: str,
    size: Any,
    *,
    bold: bool,
    RGBColor: Any,
) -> None:
    from pptx.enum.text import MSO_ANCHOR as ANCHOR

    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.auto_size = None
    frame.paragraphs[0].text = text
    frame.paragraphs[0].font.size = size
    frame.paragraphs[0].font.bold = bold
    frame.paragraphs[0].font.color.rgb = RGBColor(*_INK)
    frame.paragraphs[0].font.name = "Calibri"
    try:
        frame._txBody.bodyPr.set("anchor", ANCHOR.TOP)
    except Exception:
        return


def _pptx_chart(slide: Any, deck: dict[str, Any], slide_data: dict[str, Any]) -> None:
    points = chart_points(deck, slide_data.get("chart"))
    if not points:
        return
    try:
        from pptx.chart.data import CategoryChartData
        from pptx.enum.chart import XL_CHART_TYPE
        from pptx.util import Inches

        data = CategoryChartData()
        data.categories = [label for label, _value in points]
        data.add_series("Stored amount", [value for _label, value in points])
        chart = slide.shapes.add_chart(
            XL_CHART_TYPE.BAR_CLUSTERED,
            Inches(0.55),
            Inches(4.55),
            Inches(7.2),
            Inches(2.15),
            data,
        ).chart
        chart.has_legend = False
    except Exception:
        return


def _pdf_chart(pdf: Any, deck: dict[str, Any], slide_data: dict[str, Any]) -> None:
    points = chart_points(deck, slide_data.get("chart"))
    if not points:
        return
    span = max(abs(value) for _label, value in points) or 1.0
    y = 5.55
    for label, value in points[:5]:
        if y > 7.05:
            break
        width = max(0.08, abs(value) / span * 3.2)
        pdf.set_fill_color(*(_SLATE if value < 0 else _BRONZE))
        pdf.rect(0.55, y, width, 0.18, style="F")
        pdf.set_text_color(*_INK)
        pdf.set_xy(4.0, y)
        pdf.set_font("Helvetica", size=9)
        pdf.cell(3.2, 0.18, _pdf_safe(f"{label}: {value}"))
        y += 0.28
