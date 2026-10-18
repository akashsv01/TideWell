"""One-page visit summary PDF (ReportLab): profile, current flags with reasons, the last weeks of
numbers, upcoming visits and questions to ask. Built from live data, so it always matches the tide."""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, TIDE, SAND = colors.HexColor("#0b2545"), colors.HexColor("#0e6a70"), colors.HexColor("#efe3c8")
TIER_COLOR = {"red": colors.HexColor("#b3261e"), "amber": colors.HexColor("#c4761b"),
              "watch": TIDE, "green": colors.HexColor("#4a7c59")}
QUESTIONS = {
    "high_blood_pressure": "My blood pressure has been rising. Does it need treatment or more checks?",
    "depression_anxiety": "My mood has been harder lately. What support or treatment could help?",
    "post_cesarean": "Is my incision healing the way it should?",
    "sleep": "I'm getting very little sleep. What can help me rest?",
    "disengagement": "What should I keep an eye on between visits?",
}


def _v(x, suffix=""):
    return "–" if x is None else f"{x}{suffix}"


def build(profile: dict, points: list[dict], tiers: list[dict], appointments: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch, title="Tidewell visit summary")
    ss = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=ss["Title"], textColor=NAVY, fontSize=20, alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY, fontSize=12.5, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=12.5, textColor=NAVY)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.HexColor("#4a5a70"))
    out = [Paragraph("Tidewell visit summary", h),
           Paragraph(f"Generated {date.today():%B %d, %Y} from self-reported check-ins. For the care team to review.", small)]

    method = "C-section" if profile["delivery_method"] == "c-section" else "Vaginal birth"
    feeding = {"breastfeeding": "Breastfeeding", "formula": "Formula", "mixed": "Breast + formula"}.get(profile.get("feeding_type"), "–")
    hist = ", ".join(profile.get("history_pregnancy_complications") or []) or "None reported"
    out += [Paragraph("Patient", h2), Table([
        ["Name", profile.get("name") or "–", "Postpartum day", str(profile["day_postpartum"])],
        ["Birth", f"{method}, {profile['delivery_date']:%b %d, %Y}", "Weeks at birth", _v(profile.get("gestation_weeks"))],
        ["Feeding", feeding, "Depression/anxiety history",
         "Yes" if profile.get("history_mental_health") is True
         else "No" if profile.get("history_mental_health") is False else "Not reported"],
        ["Pregnancy", hist, "", ""],
    ], colWidths=[1.1 * inch, 2.6 * inch, 1.7 * inch, 1.6 * inch], style=TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("SPAN", (1, 3), (3, 3)), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))]

    flagged = [t for t in tiers if t["tier"] != "green"] or tiers
    out.append(Paragraph("What Tidewell flagged", h2))
    rows = [[t["tier"].upper(), t["category"].replace("_", " ").capitalize(), Paragraph("; ".join(t["reasons"]), body)]
            for t in flagged]
    if rows:
        style = [("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey)]
        style += [("TEXTCOLOR", (0, i), (0, i), TIER_COLOR[t["tier"]]) for i, t in enumerate(flagged)]
        out.append(Table(rows, colWidths=[0.8 * inch, 1.6 * inch, 4.6 * inch], style=TableStyle(style)))

    recent = points[-14:]
    out.append(Paragraph(f"Last {len(recent)} days", h2))
    data = [["Date", "Day", "Mood", "Sleep", "Pain", "Incision", "BP", "Headache", "Mood check"]]
    for p in recent:
        bp = f"{p['bp_sys']}/{p['bp_dia']}" if p.get("bp_sys") else "–"
        data.append([f"{p['day']:%b %d}", _v(p.get("day_postpartum")), _v(p.get("mood")), _v(p.get("sleep_hrs"), " h"),
                     _v(p.get("pain")), _v(p.get("incision_pain")), bp, "Yes" if p.get("headache") else "–",
                     f"{p['epds_score']}/30" if p.get("epds_score") is not None else "–"])
    out.append(Table(data, repeatRows=1, style=TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), SAND),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f9f9")])])))

    if appointments:
        out.append(Paragraph("Upcoming visits", h2))
        for a in appointments:
            out.append(Paragraph(f"{a['slot']:%a %b %d, %I:%M %p} — {a.get('facility_name') or 'Clinic'}", body))

    out.append(Paragraph("Questions to ask", h2))
    qs = [QUESTIONS[t["category"]] for t in flagged if t["tier"] != "green" and t["category"] in QUESTIONS]
    for q in qs or ["Is my recovery on track for this stage?"]:
        out.append(Paragraph(f"• {q}", body))
    out += [Spacer(1, 10), Paragraph("Tidewell does not diagnose. This summary aggregates the patient's own check-ins "
                                     "and readings. Mood check: Edinburgh Postnatal Depression Scale (Cox et al., 1987).", small)]
    doc.build(out)
    return buf.getvalue()
