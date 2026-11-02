"""
radar/report.py
===============

Builds the colorful PDF report of your whole radar.

What's in the PDF:
  1. A "Top 10 Picks" table — every ticker ranked by Composite Score,
     keeping only grades A, B, and C, showing the best 10.
  2. The full radar organized by SECTOR → SUB-SECTOR, each sector with
     its own color banner, every grade shown in a color-coded cell.
  3. A legend explaining the grade bands.

Where the data comes from:
  - ideas.csv          → your tickers (name, sector, sub_sector, theme)
  - latest_metrics.csv → raw numbers the dashboard already saves each
                         time it runs on your Mac.
  We score those numbers with the SAME pure-math functions the
  dashboard uses (radar/scoring.py), so PDF grades always match the
  screen. No internet needed — the report builds in about a second.

Two ways to run it:
  - The "📄 PDF Report" button inside the dashboard.
  - Double-click the "Radar Report" desktop icon.
  - (Or from a terminal:  python -m radar.report)

The finished file lands in  ~/Investment_Radar/reports/
named like  Radar_Report_2026-07-09.pdf  (one per day; re-runs overwrite).
"""

# --- 0. Make the parent folder importable (same trick as app.py) -----
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --- 1. Imports -------------------------------------------------------
import io
from datetime import date, datetime

import pandas as pd

from radar.load_data import load_ideas
from radar.latest_metrics import read_latest_metrics, metrics_for_symbol
from radar.scoring import value_score, tech_score, composite_score, grade_letter

# ReportLab: the PDF-building library.
#   - "platypus" is ReportLab's high-level layout engine. You hand it a
#     list of "flowables" (paragraphs, tables, spacers) — the "story" —
#     and it flows them onto pages, adding page breaks automatically.
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

# --- 2. Colors --------------------------------------------------------
#
# Grade colors mirror the emoji circles in the dashboard:
#   🟢 A/B → greens, 🟡 C → amber, 🟠 D → orange, 🔴 F → red.
# HexColor takes the same "#RRGGBB" codes used on the web.
GRADE_COLORS = {
    "A":   colors.HexColor("#1e8e3e"),   # deep green
    "B":   colors.HexColor("#7cb342"),   # light green
    "C":   colors.HexColor("#f9a825"),   # amber
    "D":   colors.HexColor("#ef6c00"),   # orange
    "F":   colors.HexColor("#c62828"),   # red
    "N/A": colors.HexColor("#9e9e9e"),   # gray
}

# One banner color per sector. Sectors are assigned colors in the order
# they appear (alphabetical), cycling if you ever have more sectors
# than colors. All picked dark enough that white text reads clearly.
SECTOR_PALETTE = [
    colors.HexColor("#1565c0"),  # blue
    colors.HexColor("#6a1b9a"),  # purple
    colors.HexColor("#00838f"),  # teal
    colors.HexColor("#c62828"),  # red
    colors.HexColor("#2e7d32"),  # green
    colors.HexColor("#e65100"),  # burnt orange
    colors.HexColor("#4527a0"),  # indigo
    colors.HexColor("#ad1457"),  # magenta
    colors.HexColor("#37474f"),  # slate
    colors.HexColor("#795548"),  # brown
]

NAVY  = colors.HexColor("#0d1b2a")   # header bars
LIGHT = colors.HexColor("#f4f6f8")   # zebra-stripe row shading


# --- 3. Score every ticker (same math as the dashboard) --------------
def build_report_dataframe() -> pd.DataFrame:
    """
    Load ideas.csv + latest_metrics.csv and return one row per ticker
    with scores, grades, and price attached. Mirrors the dashboard's
    'cloud path' exactly — pure math over stored metrics.
    """
    ideas = load_ideas()
    stored = read_latest_metrics()

    rows = []
    for _, row in ideas.iterrows():
        m = metrics_for_symbol(stored, row["symbol"])
        if m is None:
            # Ticker exists in ideas.csv but has no saved metrics yet
            # (added moments ago, dashboard not refreshed). Show N/A.
            v = t = c = None
            price = "N/A"
        else:
            v = value_score({
                "debt_to_equity": m["debt_to_equity"],
                "current_ratio":  m["current_ratio"],
                "net_cash_pct":   m["net_cash_pct"],
                "roe":            m["roe"],
                "fcf_yield":      m["fcf_yield"],
            })
            t = tech_score({
                "stage_2":            m["stage_2"],
                "dist_from_20d_high": m["dist_from_20d_high"],
                "rs_vs_spy":          m["rs_vs_spy"],
                "atr_pct":            m["atr_pct"],
            }, extended=m.get("extended") or False)
            c = composite_score(v, t)
            price = m["current_price"] or "N/A"

        rows.append({
            "symbol":     row["symbol"],
            "name":       str(row.get("name", "") or ""),
            "sector":     str(row.get("sector", "") or "").strip() or "Uncategorized",
            "sub_sector": str(row.get("sub_sector", "") or "").strip() or "General",
            "theme":      str(row.get("theme", "") or ""),
            "price":      price,
            "value_score":     v,
            "tech_score":      t,
            "composite_score": c,
            "grade":           grade_letter(c),
        })
    return pd.DataFrame(rows)


# --- 4. Small building blocks -----------------------------------------
def _fmt(score) -> str:
    """
    Turn a 0-100 float into a short display string.

    Careful: our scoring functions return None for "no data" (ETFs,
    crypto), but the moment None enters a pandas DataFrame it becomes
    NaN — a float that round() refuses to touch. pd.isna() catches
    both None and NaN in one check.
    """
    return "N/A" if pd.isna(score) else f"{round(score)}"


def _grade_cell_style(table_style: list, df_rows, grade_col: int,
                      first_data_row: int = 1) -> None:
    """
    Paint each row's grade cell with its grade color + white bold text.
    ReportLab styles cells by (column, row) coordinates, so we walk the
    rows and append one BACKGROUND command per grade cell.
    """
    for i, g in enumerate(df_rows):
        r = first_data_row + i
        table_style.append(("BACKGROUND", (grade_col, r), (grade_col, r),
                            GRADE_COLORS.get(g, GRADE_COLORS["N/A"])))
        table_style.append(("TEXTCOLOR", (grade_col, r), (grade_col, r),
                            colors.white))
        table_style.append(("FONTNAME", (grade_col, r), (grade_col, r),
                            "Helvetica-Bold"))


# --- 5. The PDF builder ------------------------------------------------
def build_pdf(target) -> None:
    """
    Build the report into `target` — either a file path (str/Path) or
    an in-memory buffer (io.BytesIO). The dashboard uses the buffer
    form so it can offer the bytes as a download; the desktop icon
    uses the file-path form.
    """
    df = build_report_dataframe()

    styles = getSampleStyleSheet()
    h_title = ParagraphStyle("RTitle", parent=styles["Title"],
                             fontSize=26, textColor=NAVY, spaceAfter=2)
    h_sub = ParagraphStyle("RSub", parent=styles["Normal"], fontSize=11,
                           textColor=colors.HexColor("#5f6b7a"),
                           alignment=TA_CENTER, spaceAfter=14)
    h_section = ParagraphStyle("RSection", parent=styles["Heading1"],
                               fontSize=16, textColor=NAVY,
                               spaceBefore=16, spaceAfter=6)
    cell = ParagraphStyle("RCell", parent=styles["Normal"], fontSize=8.5,
                          leading=10.5)
    cell_bold = ParagraphStyle("RCellB", parent=cell,
                               fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(
        target if isinstance(target, io.BytesIO) else str(target),
        pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch,
        title="Investment Radar Report",
    )
    story = []

    # ---- Header ----
    today = date.today().strftime("%A, %B %-d, %Y")
    story.append(Paragraph("INVESTMENT RADAR", h_title))
    story.append(Paragraph(
        f"{today} &nbsp;•&nbsp; {len(df)} tickers on the radar", h_sub))

    # ---- Market posture banner (Phase 3) ----
    # Read from latest_metrics.csv (written on the Mac) — the PDF
    # builds offline, same as the scores. Advice text only.
    _pm = read_latest_metrics()
    _posture_text = ""
    if not _pm.empty and "market_posture" in _pm.columns:
        _vals = [str(v).strip() for v in _pm["market_posture"].tolist()
                 if str(v).strip()]
        _posture_text = _vals[0] if _vals else ""
    if _posture_text:
        _label = _posture_text.split(" — ")[0]
        _band_color = {
            "RISK-ON": colors.HexColor("#1e8e3e"),
            "CASH": colors.HexColor("#c62828"),
        }.get(_label, colors.HexColor("#ef6c00"))
        _h_posture = ParagraphStyle(
            "RPosture", parent=styles["Normal"], fontSize=10.5,
            textColor=colors.white, alignment=TA_CENTER,
            fontName="Helvetica-Bold")
        _band = Table(
            [[Paragraph(f"MARKET POSTURE: {_posture_text}", _h_posture)]],
            colWidths=[7.3 * inch])
        _band.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _band_color),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(_band)
        story.append(Spacer(1, 10))

    # ---- Section 1: Top 10 picks ----
    story.append(Paragraph("Top 10 Picks — Grades A / B / C", h_section))
    story.append(Paragraph(
        "Ranked by Composite Score (Value + Technical combined). "
        "Only tickers grading A, B, or C make this list.", h_sub))

    top = df[df["grade"].isin(["A", "B", "C"])].copy()
    top = top.sort_values("composite_score", ascending=False).head(10)

    head = ["#", "Symbol", "Name", "Sector", "Price", "Value", "Tech",
            "Composite", "Grade"]
    data = [head]
    for rank, (_, r) in enumerate(top.iterrows(), start=1):
        data.append([
            str(rank), r["symbol"],
            Paragraph(r["name"], cell),
            Paragraph(r["sector"], cell),
            r["price"], _fmt(r["value_score"]), _fmt(r["tech_score"]),
            _fmt(r["composite_score"]), r["grade"],
        ])

    tstyle = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),   # bold symbols
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (4, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d2dc")),
        ("ROWBACKGROUNDS", (0, 1), (-2, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    _grade_cell_style(tstyle, list(top["grade"]), grade_col=8)

    story.append(Table(
        data,
        colWidths=[0.32 * inch, 0.62 * inch, 1.95 * inch, 1.35 * inch,
                   0.75 * inch, 0.52 * inch, 0.48 * inch, 0.72 * inch,
                   0.55 * inch],
        style=TableStyle(tstyle),
        repeatRows=1,
    ))
    story.append(Spacer(1, 10))

    # ---- Section 2: full radar, sector by sector ----
    story.append(Paragraph("Full Radar — by Sector &amp; Sub-Sector",
                           h_section))

    sectors = sorted(df["sector"].unique())
    for s_idx, sector in enumerate(sectors):
        s_color = SECTOR_PALETTE[s_idx % len(SECTOR_PALETTE)]
        s_df = df[df["sector"] == sector]

        # Sector banner: a one-cell table = an easy full-width color bar.
        banner = Table(
            [[Paragraph(
                f'<font color="white"><b>{sector.upper()}</b>'
                f' &nbsp;&nbsp;({len(s_df)} ticker'
                f'{"s" if len(s_df) != 1 else ""})</font>',
                ParagraphStyle("Banner", parent=cell, fontSize=11.5))]],
            colWidths=[7.26 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), s_color),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]),
        )
        story.append(Spacer(1, 8))
        story.append(banner)

        for sub in sorted(s_df["sub_sector"].unique()):
            g_df = s_df[s_df["sub_sector"] == sub].sort_values(
                "composite_score", ascending=False,
                na_position="last")

            sub_head = ["", "Symbol", "Name", "Theme", "Price", "Value",
                        "Tech", "Composite", "Grade"]
            sub_data = [[
                Paragraph(f'<font color="#{s_color.hexval()[2:]}">'
                          f"<b>{sub}</b></font>", cell_bold),
                "", "", "", "", "", "", "", "",
            ], sub_head[:]]
            # Row 0 = sub-sector label row, row 1 = column headers,
            # data starts at row 2.
            for _, r in g_df.iterrows():
                sub_data.append([
                    "", r["symbol"],
                    Paragraph(r["name"], cell),
                    Paragraph(r["theme"], cell),
                    r["price"], _fmt(r["value_score"]),
                    _fmt(r["tech_score"]), _fmt(r["composite_score"]),
                    r["grade"],
                ])

            sub_style = [
                ("SPAN", (0, 0), (-1, 0)),                     # label row
                ("BACKGROUND", (0, 1), (-1, 1),
                 colors.HexColor("#e8edf2")),                  # header row
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("FONTNAME", (1, 2), (1, -1), "Helvetica-Bold"),
                ("ALIGN", (4, 2), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 1), (-1, -1), 0.4,
                 colors.HexColor("#c9d2dc")),
                ("ROWBACKGROUNDS", (0, 2), (-2, -1),
                 [colors.white, LIGHT]),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
            _grade_cell_style(sub_style, list(g_df["grade"]),
                              grade_col=8, first_data_row=2)

            story.append(Table(
                sub_data,
                colWidths=[0.32 * inch, 0.62 * inch, 1.80 * inch,
                           1.50 * inch, 0.75 * inch, 0.52 * inch,
                           0.48 * inch, 0.72 * inch, 0.55 * inch],
                style=TableStyle(sub_style),
                repeatRows=2,
            ))

    # ---- Legend ----
    story.append(Spacer(1, 16))
    leg_data = [[
        Paragraph("<b>Grade legend</b>", cell), "A  85-100", "B  70-84",
        "C  50-69", "D  25-49", "F  0-24",
    ]]
    leg_style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i, g in enumerate(["A", "B", "C", "D", "F"], start=1):
        leg_style.append(("BACKGROUND", (i, 0), (i, 0), GRADE_COLORS[g]))
        leg_style.append(("TEXTCOLOR", (i, 0), (i, 0), colors.white))
        leg_style.append(("FONTNAME", (i, 0), (i, 0), "Helvetica-Bold"))
    story.append(Table(leg_data,
                       colWidths=[1.2 * inch] + [1.0 * inch] * 5,
                       style=TableStyle(leg_style)))

    # Grade honesty note (Phase 4, Part C) — text only.
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "ETF and crypto grades are Tech-only (no Value Score) and are "
        "not the same claim as a stock's blended Value + Tech grade.",
        ParagraphStyle("GradeNote", parent=cell, fontSize=8,
                       textColor=colors.HexColor("#5f6b7a"))))

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Generated {stamp} • Scores derived from latest_metrics.csv — "
        "same math as the dashboard.",
        ParagraphStyle("Foot", parent=cell, fontSize=7.5,
                       textColor=colors.HexColor("#8a94a0"))))

    doc.build(story)


# --- 6. Convenience wrappers ------------------------------------------
def default_report_path() -> Path:
    """~/Investment_Radar/reports/Radar_Report_YYYY-MM-DD.pdf"""
    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    return reports_dir / f"Radar_Report_{date.today().isoformat()}.pdf"


def build_pdf_bytes() -> bytes:
    """Build the PDF in memory — what the dashboard download button uses."""
    buf = io.BytesIO()
    build_pdf(buf)
    return buf.getvalue()


def build_pdf_file() -> Path:
    """Build the PDF on disk — what the desktop icon uses."""
    path = default_report_path()
    build_pdf(path)
    return path


# --- 7. Run this file directly ----------------------------------------
if __name__ == "__main__":
    out = build_pdf_file()
    print(f"✓ Report written to {out}")
