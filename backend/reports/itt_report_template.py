"""
InTimeTec — Static PDF Report Template
Layout, colors, fonts, header, footer, cover: NEVER change.
Only report_title, report_subtitle, meta, and story blocks change per report.
"""
from datetime import date as _date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase.pdfmetrics import stringWidth as _sw

BRAND = {
    "orange":      colors.HexColor("#F7941D"),
    "orange_dark": colors.HexColor("#D4760A"),
    "black":       colors.HexColor("#1A1A1A"),
    "dark_gray":   colors.HexColor("#2E2E2E"),
    "mid_gray":    colors.HexColor("#666666"),
    "light_gray":  colors.HexColor("#F0F0F0"),
    "border_gray": colors.HexColor("#DDDDDD"),
    "white":       colors.white,
    "accent_red":  colors.HexColor("#CC2200"),
    "accent_blue": colors.HexColor("#1A5276"),
    "company":     "InTimeTec",
    "company_sub": "CREATING ABUNDANCE",
    "tagline":     "Achieve your dreams… through our dreams.",
}

PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 4 * cm


def _wrap(text, font, size, max_w):
    lines, cur = [], []
    for word in text.split():
        test = " ".join(cur + [word])
        if _sw(test, font, size) <= max_w:
            cur.append(word)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]


def _draw_cover(c, doc, title, subtitle, meta):
    w, h = PAGE_W, PAGE_H
    pw = w * 0.45

    # Left dark panel
    c.setFillColor(BRAND["white"]);  c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(BRAND["black"]);  c.rect(0, 0, pw, h, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#242424")); c.setLineWidth(0.4)
    for yi in range(0, int(h), 14):
        c.line(0, yi, pw, yi)

    # Orange spine + top bar
    c.setFillColor(BRAND["orange"]); c.rect(pw, 0, 7, h, fill=1, stroke=0)
    c.setFillColor(BRAND["orange"]); c.rect(pw + 7, h - 52, w - pw - 7, 52, fill=1, stroke=0)
    c.setFillColor(BRAND["white"]);  c.setFont("Helvetica-Bold", 9)
    c.drawRightString(w - 20, h - 19, BRAND["company"].upper())
    c.setFont("Helvetica", 7); c.drawRightString(w - 20, h - 32, BRAND["company_sub"])

    # Logo circles
    cx, cy = pw * 0.50, h * 0.52
    c.setStrokeColor(colors.HexColor("#3A3A3A")); c.setLineWidth(1);  c.circle(cx, cy, 138, fill=0, stroke=1)
    c.setStrokeColor(BRAND["orange"]);             c.setLineWidth(22); c.circle(cx, cy, 115, fill=0, stroke=1)
    c.setStrokeColor(BRAND["orange_dark"]);        c.setLineWidth(12); c.circle(cx, cy, 84,  fill=0, stroke=1)
    c.setFillColor(BRAND["dark_gray"]); c.setStrokeColor(BRAND["orange"]); c.setLineWidth(3)
    c.circle(cx, cy, 58, fill=1, stroke=1)
    c.setFillColor(BRAND["white"])
    c.setFont("Helvetica-Bold", 11); c.drawCentredString(cx, cy + 24, "in")
    c.setFont("Helvetica-Bold", 15); c.drawCentredString(cx, cy + 6,  "time")
    c.setFont("Helvetica-Bold", 19); c.drawCentredString(cx, cy - 15, "tec")
    c.setFillColor(BRAND["orange"]); c.circle(cx - 20, cy + 28, 4, fill=1, stroke=0)
    c.setFillColor(BRAND["mid_gray"]); c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(cx, cy - 40, "CREATING ABUNDANCE")

    # Decorative accents
    c.setFillColor(BRAND["orange"])
    c.circle(22, h - 22, 18, fill=1, stroke=0)
    c.circle(55, h - 8,  10, fill=1, stroke=0)
    c.circle(18, 55,     26, fill=1, stroke=0)
    c.setFillColor(BRAND["orange_dark"]); c.circle(55, 22, 13, fill=1, stroke=0)
    c.setFillColor(BRAND["orange"]);      c.circle(cx - 118, cy - 18, 6, fill=1, stroke=0)
    c.setFillColor(BRAND["orange_dark"]); c.circle(cx + 100, cy + 72, 5, fill=1, stroke=0)
    c.setStrokeColor(BRAND["accent_red"]); c.setLineWidth(2.5)
    c.arc(cx - 148, cy - 148, cx - 88, cy - 88, startAng=195, extent=110)

    # Right panel — title
    rx = pw + 24; rw = w - rx - 20; rcx = rx + rw / 2
    fs = 28 if len(title) <= 35 else (22 if len(title) <= 55 else 17)
    lines, cur = [], []
    for word in title.split():
        if _sw(" ".join(cur + [word]), "Helvetica-Bold", fs) <= rw:
            cur.append(word)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [word]
    if cur: lines.append(" ".join(cur))
    ty = h * 0.65
    c.setFillColor(BRAND["black"]); c.setFont("Helvetica-Bold", fs)
    for ln in lines:
        c.drawString(rx, ty, ln); ty -= fs + 6

    # Subtitle badge
    badge_y = ty - 10
    c.setFillColor(BRAND["orange"]); c.roundRect(rx, badge_y, rw, 30, 5, fill=1, stroke=0)
    c.setFillColor(BRAND["white"]);  c.setFont("Helvetica-Bold", 11)
    sub = subtitle
    while _sw(sub, "Helvetica-Bold", 11) > rw - 20 and len(sub) > 5:
        sub = sub[:-1]
    if sub != subtitle: sub += "…"
    c.drawCentredString(rcx, badge_y + 9, sub)

    # Meta grid
    div_y = badge_y - 16
    c.setStrokeColor(BRAND["border_gray"]); c.setLineWidth(0.8)
    c.line(rx, div_y, rx + rw, div_y)
    fields = [
        ("REPORT ID",    meta.get("report_id",   "—")),
        ("PREPARED FOR", meta.get("client",       "—")),
        ("PREPARED BY",  meta.get("prepared_by",  "—")),
        ("DEPARTMENT",   meta.get("department",   "Operations")),
        ("DATE",         meta.get("date",         "—")),
        ("VERSION",      meta.get("version",      "v1.0")),
    ]
    cell_w = rw / 2; cell_h = 30; meta_top = div_y - 8
    for i, (label, value) in enumerate(fields):
        col = i % 2; row = i // 2
        mx = rx + col * cell_w; my = meta_top - row * cell_h
        bg = BRAND["light_gray"] if (row + col) % 2 == 0 else BRAND["white"]
        c.setFillColor(bg); c.rect(mx, my - cell_h + 2, cell_w - 2, cell_h - 2, fill=1, stroke=0)
        c.setFillColor(BRAND["orange_dark"]); c.setFont("Helvetica-Bold", 7)
        c.drawString(mx + 6, my - 8, label)
        val = str(value)
        while _sw(val, "Helvetica", 8) > cell_w - 16 and len(val) > 3: val = val[:-1]
        if val != str(value): val += "…"
        c.setFillColor(BRAND["dark_gray"]); c.setFont("Helvetica", 8)
        c.drawString(mx + 6, my - 20, val)

    accent_y = meta_top - 3 * cell_h - 10
    c.setFillColor(BRAND["orange"]); c.rect(rx, accent_y, rw, 3, fill=1, stroke=0)
    c.setFillColor(BRAND["mid_gray"]); c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(rcx, 36, BRAND["tagline"])
    c.setFillColor(BRAND["orange"]); c.rect(0, 0, w, 10, fill=1, stroke=0)
    c.setFillColor(BRAND["orange_dark"])
    for xi in range(18, int(w), 18):
        c.circle(xi, 5, 2, fill=1, stroke=0)


def _draw_header_footer(c, doc):
    w, h = PAGE_W, PAGE_H
    rep_title  = getattr(doc, "_itt_title",  "Report")
    rep_id     = getattr(doc, "_itt_id",     "")
    rep_client = getattr(doc, "_itt_client", "")
    rep_date   = getattr(doc, "_itt_date",   "")

    # Header
    c.setFillColor(BRAND["black"]); c.rect(0, h - 40, w, 40, fill=1, stroke=0)
    c.setFillColor(BRAND["orange"]); c.rect(0, h - 40, 7, 40, fill=1, stroke=0)
    c.setStrokeColor(BRAND["orange"]); c.setLineWidth(1.5); c.circle(24, h - 20, 10, fill=0, stroke=1)
    c.setFillColor(BRAND["white"]); c.setFont("Helvetica-Bold", 6); c.drawCentredString(24, h - 23, "ITT")
    c.setFillColor(BRAND["white"]); c.setFont("Helvetica-Bold", 11); c.drawString(40, h - 22, BRAND["company"])
    c.setFillColor(BRAND["orange"]); c.setFont("Helvetica", 6.5); c.drawString(40, h - 33, BRAND["company_sub"])
    c.setStrokeColor(colors.HexColor("#444444")); c.setLineWidth(0.8); c.line(130, h - 36, 130, h - 8)
    title = rep_title
    while _sw(title, "Helvetica", 8.5) > 230 and len(title) > 6: title = title[:-1]
    if title != rep_title: title += "…"
    c.setFillColor(colors.HexColor("#BBBBBB")); c.setFont("Helvetica", 8.5)
    c.drawCentredString(w / 2, h - 24, title)
    c.setFillColor(colors.HexColor("#999999")); c.setFont("Helvetica", 7.5)
    if rep_client: c.drawRightString(w - 14, h - 22, f"Client: {rep_client}")
    c.drawRightString(w - 14, h - 33, rep_date)

    # Footer
    c.setFillColor(BRAND["light_gray"]); c.rect(0, 0, w, 28, fill=1, stroke=0)
    c.setFillColor(BRAND["orange"]);     c.rect(0, 0, 7, 28, fill=1, stroke=0)
    c.setStrokeColor(BRAND["border_gray"]); c.setLineWidth(0.5); c.line(0, 28, w, 28)
    c.setFillColor(BRAND["dark_gray"]); c.setFont("Helvetica-Bold", 8)
    c.drawString(16, 10, f"Page {doc.page}")
    c.setFillColor(BRAND["mid_gray"]); c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 10, "Confidential — For Internal Use Only")
    c.setFont("Helvetica", 7); c.drawRightString(w - 14, 10, rep_id)


def _styles():
    S = {}
    S["h1"]     = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=20,
                    textColor=BRAND["black"], spaceAfter=8, spaceBefore=18, leading=26)
    S["h2"]     = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13,
                    textColor=BRAND["orange"], spaceAfter=5, spaceBefore=12, leading=17)
    S["h3"]     = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=11,
                    textColor=BRAND["dark_gray"], spaceAfter=4, spaceBefore=8, leading=15)
    S["body"]   = ParagraphStyle("Body", fontName="Helvetica", fontSize=10,
                    textColor=BRAND["dark_gray"], spaceAfter=6, leading=16, alignment=TA_JUSTIFY)
    S["bullet"] = ParagraphStyle("Bullet", fontName="Helvetica", fontSize=10,
                    textColor=BRAND["dark_gray"], spaceAfter=3, leading=15, leftIndent=16)
    S["th"]     = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=9,
                    textColor=BRAND["white"], alignment=TA_CENTER, leading=12)
    S["td"]     = ParagraphStyle("TD", fontName="Helvetica", fontSize=9,
                    textColor=BRAND["dark_gray"], leading=13)
    return S


class _SectionDivider(Flowable):
    def __init__(self, title):
        super().__init__(); self.title = title; self.width = CONTENT_W; self.height = 28

    def draw(self):
        c = self.canv
        c.setFillColor(BRAND["black"]); c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        c.setFillColor(BRAND["orange"]); c.roundRect(0, 0, 6, self.height, 2, fill=1, stroke=0)
        c.setFillColor(BRAND["white"]); c.setFont("Helvetica-Bold", 11)
        c.drawString(16, 9, self.title.upper())
        c.setFillColor(BRAND["orange"])
        for xi in [self.width - 12, self.width - 22, self.width - 32]:
            c.circle(xi, 14, 2.5, fill=1, stroke=0)


class _HighlightBox(Flowable):
    _IW = 34; _PY = 10; _LH = 13; _F = "Helvetica-Bold"; _FS = 9.5

    def __init__(self, text, icon="▶"):
        super().__init__(); self.text = text; self.icon = icon; self.width = CONTENT_W
        lines = _wrap(text, self._F, self._FS, self.width - self._IW - 10)
        self.height = max(36, self._PY * 2 + len(lines) * self._LH)

    def draw(self):
        c = self.canv
        c.setFillColor(BRAND["orange"]);      c.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=0)
        c.setFillColor(BRAND["orange_dark"]); c.roundRect(0, 0, self._IW, self.height, 5, fill=1, stroke=0)
        c.setFillColor(BRAND["white"]); c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(self._IW / 2, self.height / 2 - 6, self.icon)
        lines = _wrap(self.text, self._F, self._FS, self.width - self._IW - 10)
        c.setFillColor(BRAND["white"]); c.setFont(self._F, self._FS)
        ty = self._PY + (len(lines) - 1) * self._LH
        for ln in lines:
            c.drawString(self._IW + 8, ty, ln); ty -= self._LH


class _NoteBox(Flowable):
    _PX = 14; _PY = 9; _LH = 13; _F = "Helvetica-Oblique"; _FS = 8.5

    def __init__(self, text):
        super().__init__(); self.text = text; self.width = CONTENT_W
        lines = _wrap(text, self._F, self._FS, self.width - self._PX * 2 - 4)
        self.height = max(28, self._PY * 2 + len(lines) * self._LH)

    def draw(self):
        c = self.canv
        c.setFillColor(BRAND["light_gray"]); c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setStrokeColor(BRAND["border_gray"]); c.setLineWidth(0.5)
        c.roundRect(0, 0, self.width, self.height, 4, fill=0, stroke=1)
        c.setFillColor(BRAND["accent_blue"]); c.rect(0, 0, 4, self.height, fill=1, stroke=0)
        lines = _wrap(self.text, self._F, self._FS, self.width - self._PX * 2 - 4)
        c.setFillColor(BRAND["mid_gray"]); c.setFont(self._F, self._FS)
        ty = self._PY + (len(lines) - 1) * self._LH
        for ln in lines:
            c.drawString(self._PX, ty, ln); ty -= self._LH


class _StatRow(Flowable):
    HEIGHT = 66

    def __init__(self, stats):
        super().__init__(); self.stats = stats; self.width = CONTENT_W; self.height = self.HEIGHT

    def draw(self):
        c = self.canv; n = len(self.stats); cw = self.width / n
        for i, (value, label) in enumerate(self.stats):
            x = i * cw
            bg = BRAND["orange"] if i % 2 == 0 else BRAND["black"]
            c.setFillColor(bg); c.roundRect(x + 3, 2, cw - 6, self.height - 4, 5, fill=1, stroke=0)
            c.setFillColor(BRAND["white"]); c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(x + cw / 2, self.height - 28, str(value))
            lbl = str(label)
            while _sw(lbl, "Helvetica", 7.5) > cw - 12 and len(lbl) > 3: lbl = lbl[:-1]
            if lbl != str(label): lbl += "…"
            c.setFillColor(colors.HexColor("#DDDDDD")); c.setFont("Helvetica", 7.5)
            c.drawCentredString(x + cw / 2, self.height - 42, lbl)
            c.setFillColor(BRAND["orange_dark"] if i % 2 == 0 else BRAND["orange"])
            c.rect(x + 3, 2, cw - 6, 3, fill=1, stroke=0)


class ITTPDFTemplate:
    """
    Static InTimeTec PDF template.
    Call render(ai_data, session_id, output_path) to produce a branded PDF.
    ai_data keys used: report_title, ai_summary, sections[], structured_data[]
    """

    def __init__(self):
        self._styles = _styles()

    def _section(self, title):
        return [Spacer(1, 6), _SectionDivider(title), Spacer(1, 10)]

    def _h(self, text, level=2):
        key = {1: "h1", 2: "h2", 3: "h3"}.get(level, "h2")
        return Paragraph(text, self._styles[key])

    def _body(self, text):
        return Paragraph(text, self._styles["body"])

    def _bullets(self, items):
        return [Paragraph(f"•  {it}", self._styles["bullet"]) for it in items]

    def _highlight(self, text, icon="▶"):
        return [Spacer(1, 4), _HighlightBox(text, icon), Spacer(1, 8)]

    def _note(self, text):
        return [Spacer(1, 4), _NoteBox(text), Spacer(1, 8)]

    def _stats(self, items):
        return [_StatRow(items), Spacer(1, 10)]

    def _table(self, headers, rows, col_widths=None):
        n = len(headers)
        cws = col_widths or [CONTENT_W / n] * n
        data = [[Paragraph(h, self._styles["th"]) for h in headers]]
        for row in rows:
            data.append([Paragraph(str(cell), self._styles["td"]) for cell in row])
        t = Table(data, colWidths=cws, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0),  BRAND["black"]),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),   [BRAND["white"], BRAND["light_gray"]]),
            ("GRID",         (0, 0), (-1, -1), 0.3, BRAND["border_gray"]),
            ("LINEBELOW",    (0, 0), (-1, 0),  2,   BRAND["orange"]),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return [t, Spacer(1, 10)]

    def render(self, ai_data: dict, session_id: str, output_path: str) -> str:
        title    = ai_data.get("report_title", "Executive Report")
        subtitle = ai_data.get("report_subtitle", "Professional Report")
        summary  = ai_data.get("ai_summary", "")
        sections = ai_data.get("sections", [])
        struct   = ai_data.get("structured_data", [])

        meta = {
            "report_id":   f"RPT-{session_id[-8:].upper()}",
            "client":      ai_data.get("client", "InTimeTec"),
            "prepared_by": "InTimeTec AI System",
            "department":  ai_data.get("department", "Operations"),
            "date":        _date.today().strftime("%B %d, %Y"),
            "version":     "v1.0",
        }

        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2.4*cm, bottomMargin=1.8*cm,
        )
        doc._itt_title  = title
        doc._itt_id     = meta["report_id"]
        doc._itt_client = meta["client"]
        doc._itt_date   = meta["date"]

        story = [PageBreak()]

        # Executive Summary
        story.extend(self._section("Executive Summary"))
        if summary:
            story.extend(self._highlight(summary[:200] if len(summary) > 200 else summary))
            story.append(self._body(summary))

        # Structured data table
        if struct:
            story.extend(self._section("Key Data"))
            story.extend(self._table(
                ["Parameter", "Value"],
                [[r.get("item", ""), r.get("value", "")] for r in struct],
                col_widths=[CONTENT_W * 0.5, CONTENT_W * 0.5],
            ))

        # Content sections
        for sec in sections:
            story.append(PageBreak())
            story.extend(self._section(sec.get("heading", "Section")))
            body_text = sec.get("body", "")
            # Split on double newline into paragraphs
            for para in body_text.split("\n\n"):
                para = para.strip()
                if para:
                    story.append(self._body(para))
                    story.append(Spacer(1, 6))

            # Bullet points if provided
            bullets = sec.get("bullets", [])
            if bullets:
                story.extend(self._bullets(bullets))

            # Note if provided
            note = sec.get("note", "")
            if note:
                story.extend(self._note(note))

        def on_cover(c, d):
            _draw_cover(c, d, title, subtitle, meta)

        def on_inner(c, d):
            _draw_header_footer(c, d)

        doc.build(story, onFirstPage=on_cover, onLaterPages=on_inner)
        return output_path
