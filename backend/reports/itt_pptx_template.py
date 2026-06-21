"""
InTimeTec — Static PPTX Report Template
Slide layouts, colors, fonts, and brand elements: NEVER change.
Only title, summary, and section content change per presentation.
"""
from datetime import date as _date
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# ── Brand palette ──────────────────────────────────────────────────────────────
_ORANGE      = RGBColor(0xF7, 0x94, 0x1D)
_ORANGE_DARK = RGBColor(0xD4, 0x76, 0x0A)
_BLACK       = RGBColor(0x1A, 0x1A, 0x1A)
_DARK_GRAY   = RGBColor(0x2E, 0x2E, 0x2E)
_MID_GRAY    = RGBColor(0x66, 0x66, 0x66)
_LIGHT_GRAY  = RGBColor(0xF0, 0xF0, 0xF0)
_WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
_ACCENT_BLUE = RGBColor(0x1A, 0x52, 0x76)

_W = Inches(13.33)   # 16:9 widescreen
_H = Inches(7.5)
_COMPANY = "InTimeTec"
_TAGLINE = "CREATING ABUNDANCE"


def _rgb(r, g, b):
    from pptx.dml.color import RGBColor
    return RGBColor(r, g, b)


def _set_fill(shape, r, g, b):
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(r, g, b)


def _add_rect(slide, left, top, width, height, r, g, b):
    from pptx.util import Emu
    shape = slide.shapes.add_shape(1, left, top, width, height)  # MSO_SHAPE_TYPE.RECTANGLE = 1
    shape.line.fill.background()
    _set_fill(shape, r, g, b)
    return shape


def _add_text_box(slide, left, top, width, height, text, font_size, bold=False,
                  color=_WHITE, align=PP_ALIGN.LEFT, italic=False):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf  = txb.text_frame
    tf.word_wrap = True
    p   = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = str(text)
    run.font.size   = Pt(font_size)
    run.font.bold   = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txb


def _brand_bar_left(slide, width=Inches(0.12)):
    """Orange left accent bar used on content slides."""
    _add_rect(slide, 0, 0, width, _H, 0xF7, 0x94, 0x1D)


def _brand_header(slide, title_text: str):
    """Black header bar with orange left stripe and white title."""
    bar_h = Inches(0.9)
    _add_rect(slide, 0, 0, _W, bar_h, 0x1A, 0x1A, 0x1A)
    _add_rect(slide, 0, 0, Inches(0.15), bar_h, 0xF7, 0x94, 0x1D)
    _add_text_box(slide, Inches(0.3), Inches(0.05), Inches(9), bar_h - Inches(0.1),
                  title_text, 22, bold=True, color=_WHITE)
    # Company name top-right
    _add_text_box(slide, Inches(10.5), Inches(0.08), Inches(2.7), Inches(0.45),
                  _COMPANY, 11, bold=True, color=_ORANGE, align=PP_ALIGN.RIGHT)
    _add_text_box(slide, Inches(10.5), Inches(0.45), Inches(2.7), Inches(0.35),
                  _TAGLINE, 7, color=_rgb(0x99, 0x99, 0x99), align=PP_ALIGN.RIGHT)


def _brand_footer(slide, report_id: str, page_num: int):
    """Light gray footer bar with page number and report ID."""
    bar_h = Inches(0.4)
    _add_rect(slide, 0, _H - bar_h, _W, bar_h, 0xF0, 0xF0, 0xF0)
    _add_rect(slide, 0, _H - bar_h, Inches(0.12), bar_h, 0xF7, 0x94, 0x1D)
    _add_text_box(slide, Inches(0.2), _H - bar_h + Inches(0.05), Inches(2), bar_h,
                  f"Slide {page_num}", 8, bold=True, color=_DARK_GRAY)
    _add_text_box(slide, 0, _H - bar_h + Inches(0.05), _W - Inches(0.2), bar_h,
                  "Confidential — For Internal Use Only", 7,
                  italic=True, color=_MID_GRAY, align=PP_ALIGN.CENTER)
    _add_text_box(slide, _W - Inches(2.5), _H - bar_h + Inches(0.05), Inches(2.4), bar_h,
                  report_id, 7, color=_MID_GRAY, align=PP_ALIGN.RIGHT)


def _cover_slide(prs: Presentation, title: str, subtitle: str, meta: dict):
    """Slide 1: branded cover — black left panel, white right, logo mark."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout

    # Background
    _add_rect(slide, 0, 0, _W, _H, 0xFF, 0xFF, 0xFF)

    # Left dark panel (45 %)
    pw = int(_W * 0.45)
    _add_rect(slide, 0, 0, pw, _H, 0x1A, 0x1A, 0x1A)

    # Orange spine
    _add_rect(slide, pw, 0, Inches(0.12), _H, 0xF7, 0x94, 0x1D)

    # Orange top bar (right side)
    _add_rect(slide, pw + Inches(0.12), 0, _W - pw - Inches(0.12), Inches(0.75), 0xF7, 0x94, 0x1D)

    # Company name in top bar
    _add_text_box(slide, pw + Inches(0.3), Inches(0.05), Inches(5), Inches(0.35),
                  _COMPANY.upper(), 12, bold=True, color=_WHITE)
    _add_text_box(slide, pw + Inches(0.3), Inches(0.4), Inches(5), Inches(0.3),
                  _TAGLINE, 8, color=_rgb(0xFF, 0xFF, 0xFF))

    # Logo area (left panel center)
    logo_left = Inches(0.4); logo_top = Inches(1.8)
    logo_size = Inches(3.2)
    logo_box = slide.shapes.add_shape(9, logo_left, logo_top, logo_size, logo_size)  # oval
    logo_box.fill.solid(); logo_box.fill.fore_color.rgb = _rgb(0x2E, 0x2E, 0x2E)
    logo_box.line.color.rgb = _ORANGE; logo_box.line.width = Pt(3)

    _add_text_box(slide, logo_left, logo_top + Inches(0.7),  logo_size, Inches(0.5),
                  "in",   20, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
    _add_text_box(slide, logo_left, logo_top + Inches(1.1),  logo_size, Inches(0.55),
                  "time", 26, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
    _add_text_box(slide, logo_left, logo_top + Inches(1.65), logo_size, Inches(0.65),
                  "tec",  32, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)

    # Report title (right panel)
    rx = pw + Inches(0.35)
    rw = _W - rx - Inches(0.3)
    _add_text_box(slide, rx, Inches(1.0), rw, Inches(1.8),
                  title.upper(), 28, bold=True, color=_BLACK)

    # Subtitle badge
    badge_top = Inches(3.1)
    _add_rect(slide, rx, badge_top, rw, Inches(0.55), 0xF7, 0x94, 0x1D)
    _add_text_box(slide, rx, badge_top + Inches(0.05), rw, Inches(0.45),
                  subtitle, 13, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)

    # Meta fields
    fields = [
        ("REPORT ID",    meta.get("report_id",   "—")),
        ("PREPARED FOR", meta.get("client",       "—")),
        ("PREPARED BY",  meta.get("prepared_by",  "—")),
        ("DEPARTMENT",   meta.get("department",   "Operations")),
        ("DATE",         meta.get("date",         "—")),
        ("VERSION",      meta.get("version",      "v1.0")),
    ]
    cell_w = rw / 2; cell_h = Inches(0.55); mt = Inches(3.9)
    for i, (label, value) in enumerate(fields):
        col = i % 2; row = i // 2
        mx = rx + col * cell_w; my = mt + row * cell_h
        bg = (0xF0, 0xF0, 0xF0) if (row + col) % 2 == 0 else (0xFF, 0xFF, 0xFF)
        _add_rect(slide, mx, my, cell_w - Inches(0.03), cell_h - Inches(0.03), *bg)
        _add_text_box(slide, mx + Inches(0.08), my + Inches(0.02), cell_w, Inches(0.22),
                      label, 7, bold=True, color=_ORANGE_DARK)
        _add_text_box(slide, mx + Inches(0.08), my + Inches(0.24), cell_w, Inches(0.26),
                      str(value), 8, color=_DARK_GRAY)

    # Bottom tagline
    _add_text_box(slide, rx, Inches(7.0), rw, Inches(0.35),
                  "Achieve your dreams… through our dreams.", 9,
                  italic=True, color=_MID_GRAY, align=PP_ALIGN.CENTER)

    # Bottom orange bar
    _add_rect(slide, 0, _H - Inches(0.15), _W, Inches(0.15), 0xF7, 0x94, 0x1D)


def _summary_slide(prs: Presentation, summary: str, report_id: str):
    """Slide 2: Executive Summary."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, _W, _H, 0xFF, 0xFF, 0xFF)
    _brand_header(slide, "Executive Summary")
    _brand_bar_left(slide)
    _brand_footer(slide, report_id, 2)

    # Highlight box
    hb_top = Inches(1.1); hb_h = Inches(1.2)
    _add_rect(slide, Inches(0.25), hb_top, _W - Inches(0.5), hb_h, 0xF7, 0x94, 0x1D)
    _add_rect(slide, Inches(0.25), hb_top, Inches(0.5), hb_h, 0xD4, 0x76, 0x0A)
    _add_text_box(slide, Inches(0.85), hb_top + Inches(0.15),
                  _W - Inches(1.1), hb_h - Inches(0.3),
                  summary[:220] if len(summary) > 220 else summary,
                  10, bold=True, color=_WHITE)

    # Full summary body
    _add_text_box(slide, Inches(0.25), Inches(2.5), _W - Inches(0.5), Inches(4.5),
                  summary, 11, color=_DARK_GRAY)


def _content_slide(prs: Presentation, heading: str, body: str,
                   bullets: list, note: str, report_id: str, page_num: int):
    """One slide per report section."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, _W, _H, 0xFF, 0xFF, 0xFF)
    _brand_header(slide, heading)
    _brand_bar_left(slide)
    _brand_footer(slide, report_id, page_num)

    # Content area
    content_top = Inches(1.05)
    content_h   = _H - Inches(1.45)

    if bullets:
        # Left: body text | Right: bullets
        col_w = (_W - Inches(0.5)) / 2
        _add_text_box(slide, Inches(0.25), content_top, col_w, content_h, body, 10, color=_DARK_GRAY)
        # Bullet column with light bg
        _add_rect(slide, col_w + Inches(0.4), content_top, col_w - Inches(0.15), content_h,
                  0xF0, 0xF0, 0xF0)
        # Orange top accent
        _add_rect(slide, col_w + Inches(0.4), content_top, col_w - Inches(0.15), Inches(0.06),
                  0xF7, 0x94, 0x1D)
        bullet_str = "\n".join(f"▸  {b}" for b in bullets)
        _add_text_box(slide, col_w + Inches(0.55), content_top + Inches(0.15),
                      col_w - Inches(0.4), content_h - Inches(0.2),
                      bullet_str, 9, color=_DARK_GRAY)
    else:
        _add_text_box(slide, Inches(0.25), content_top, _W - Inches(0.5), content_h,
                      body, 11, color=_DARK_GRAY)

    if note:
        note_top = _H - Inches(0.85)
        _add_rect(slide, Inches(0.25), note_top, _W - Inches(0.5), Inches(0.38),
                  0xF0, 0xF0, 0xF0)
        _add_rect(slide, Inches(0.25), note_top, Inches(0.06), Inches(0.38), 0x1A, 0x52, 0x76)
        _add_text_box(slide, Inches(0.4), note_top + Inches(0.04),
                      _W - Inches(0.65), Inches(0.3),
                      note, 8, italic=True, color=_MID_GRAY)


class ITTPPTXTemplate:
    """
    Static InTimeTec PPTX template.
    Call render(ai_data, session_id, output_path) to produce a branded PPTX.
    ai_data keys used: report_title, report_subtitle, ai_summary,
                       sections[], client, department
    """

    def render(self, ai_data: dict, session_id: str, output_path: str) -> str:
        title    = ai_data.get("report_title", "Executive Report")
        subtitle = ai_data.get("report_subtitle", "Professional Report")
        summary  = ai_data.get("ai_summary", "")
        sections = ai_data.get("sections", [])

        meta = {
            "report_id":   f"RPT-{session_id[-8:].upper()}",
            "client":      ai_data.get("client", "InTimeTec"),
            "prepared_by": "InTimeTec AI System",
            "department":  ai_data.get("department", "Operations"),
            "date":        _date.today().strftime("%B %d, %Y"),
            "version":     "v1.0",
        }
        report_id = meta["report_id"]

        prs = Presentation()
        prs.slide_width  = _W
        prs.slide_height = _H

        _cover_slide(prs, title, subtitle, meta)
        if summary:
            _summary_slide(prs, summary, report_id)

        for i, sec in enumerate(sections, start=3):
            _content_slide(
                prs,
                heading   = sec.get("heading", "Section"),
                body      = sec.get("body", ""),
                bullets   = sec.get("bullets", []),
                note      = sec.get("note", ""),
                report_id = report_id,
                page_num  = i,
            )

        prs.save(output_path)
        return output_path
