"""Dark-theme PDF daily report."""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)

BG = colors.HexColor("#12141a")
CARD = colors.HexColor("#1c1f27")
ACCENT = colors.HexColor("#4da3ff")
TEXT = colors.HexColor("#e8eaf0")
MUTED = colors.HexColor("#9aa3b2")
RED = colors.HexColor("#ff5c5c")
GREEN = colors.HexColor("#4cd07d")
AMBER = colors.HexColor("#ffb24d")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=styles["Title"], textColor=ACCENT,
                    fontName="Helvetica-Bold", fontSize=18, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=TEXT,
                    fontName="Helvetica-Bold", fontSize=12, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("p", parent=styles["Normal"], textColor=TEXT,
                   fontName="Helvetica", fontSize=8.5, leading=11)
M = ParagraphStyle("m", parent=P, textColor=MUTED, fontSize=8)


def _bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(A4[0] - 12*mm, 8*mm,
                           f"Generated {datetime.now():%d %b %Y %H:%M} | page {doc.page}")
    canvas.restoreState()


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#26304a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD, colors.HexColor("#171a21")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#333a48")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _para(text, style=P):
    return Paragraph(text or "-", style)


def write_pdf(notifications, path, changes=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm,
                            topMargin=14*mm, bottomMargin=14*mm)
    story = [Paragraph("Government Jobs & Exams Intelligence Report", H1),
             Paragraph(f"Daily report - {datetime.now():%A, %d %B %Y}", M),
             Spacer(1, 6),
             HRFlowable(width="100%", color=ACCENT, thickness=1),
             Spacer(1, 6)]

    verified = [n for n in notifications if n.verification_status.startswith("Verified")]
    unverified = [n for n in notifications if n.verification_status == "Unverified"]
    from ..models import is_applied
    applied = [n for n in notifications if is_applied(n.status)]
    expired = [n for n in notifications if n.verification_status in
               ("Application Closed", "Expired")]
    upcoming = sorted([n for n in notifications
                       if n.days_left() is not None and n.days_left() >= 0],
                      key=lambda n: n.days_left())

    stats = [["Tracked", "Verified", "Unverified", "Applied", "Expired", "Deadlines ahead"],
             [str(len(notifications)), str(len(verified)), str(len(unverified)),
              str(len(applied)), str(len(expired)), str(len(upcoming))]]
    t = Table(stats, colWidths=[31*mm]*6)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#26304a")),
        ("BACKGROUND", (0, 1), (-1, 1), CARD),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED), ("TEXTCOLOR", (0, 1), (-1, 1), ACCENT),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("FONTSIZE", (0, 0), (-1, 0), 8), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#333a48")),
    ]))
    story += [t, Spacer(1, 4)]

    story.append(Paragraph("Upcoming deadlines", H2))
    rows = [[_para("<b>Notification</b>"), _para("<b>Last date</b>"),
             _para("<b>Days</b>"), _para("<b>Status</b>"), _para("<b>Priority</b>")]]
    for n in upcoming[:20]:
        rows.append([_para(f"{n.job_name} - {n.organization}"),
                     _para(n.application_end), _para(str(n.days_left())),
                     _para(n.verification_status), _para(n.priority)])
    if len(rows) > 1:
        story.append(_table(rows, [88*mm, 24*mm, 12*mm, 38*mm, 20*mm]))
    else:
        story.append(Paragraph("No dated deadlines on record.", M))

    story.append(Paragraph("Applied - tracked applications", H2))
    rows = [[_para("<b>Notification</b>"), _para("<b>Status</b>"),
             _para("<b>Next milestone</b>")]]
    for n in applied:
        rows.append([_para(f"{n.job_name} - {n.organization}"), _para(n.status),
                     _para(n.exam_date or "Awaiting exam date")])
    story.append(_table(rows, [92*mm, 40*mm, 50*mm]) if len(rows) > 1
                 else Paragraph("No applications tracked yet.", M))

    if changes:
        story.append(Paragraph("Changes detected in the last 24 hours", H2))
        rows = [[_para("<b>When</b>"), _para("<b>Record</b>"), _para("<b>Field</b>"),
                 _para("<b>New value</b>")]]
        for nid, ts, field, old, new in changes[:25]:
            rows.append([_para(ts[:16]), _para(nid), _para(field), _para(str(new)[:120])])
        story.append(_table(rows, [26*mm, 26*mm, 30*mm, 100*mm]))

    story.append(Paragraph("Unverified (needs official confirmation - do not pay fees yet)", H2))
    rows = [[_para("<b>Notification</b>"), _para("<b>Source</b>")]]
    for n in unverified[:15]:
        rows.append([_para(n.job_name), _para(n.verification_source)])
    story.append(_table(rows, [122*mm, 60*mm]) if len(rows) > 1
                 else Paragraph("Nothing unverified today.", M))

    doc.build(story, onFirstPage=_bg, onLaterPages=_bg)
    return path
