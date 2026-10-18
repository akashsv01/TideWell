"""iPhone setup guide (ReportLab): connect Apple Health to Tidewell with the Health Auto Export app.

Personalised only with this server's web address. The connection code is NOT printed: it works like
a password and PDFs get saved and forwarded, so the guide points to Settings, where it is shown once.
App screen names can change between Health Auto Export versions, so steps name the setting, not
exact button positions.
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, TIDE, SAND = colors.HexColor("#0b2545"), colors.HexColor("#0e6a70"), colors.HexColor("#f6efdf")

STEPS = [
    ("Install the app",
     "On your iPhone, open the App Store and install <b>Health Auto Export - JSON+CSV</b>. Sending data "
     "to Tidewell uses its <b>Premium</b> automations. There is a 7-day free trial."),
    ("Let it read Apple Health",
     "Open Health Auto Export and allow access to Apple Health when asked. Turn on at least "
     "<b>Sleep</b>, <b>Blood Pressure</b> and <b>Resting Heart Rate</b>. Heart Rate Variability and Steps "
     "are optional. You can change this later in the iPhone Settings app under Health, Data Access."),
    ("Get your connection code from Tidewell",
     "In Tidewell, go to <b>Settings, Connect Apple Health</b> and tap <b>Create connection code</b>. "
     "Keep that screen open: the code is shown only once. It starts with <b>tw_</b>."),
    ("Create the automation",
     "In Health Auto Export, open <b>Automations</b> and add a new one of type <b>REST API</b>. Fill in:"),
    ("Test it",
     "Use the automation's <b>manual export / run now</b> option once. In Tidewell, Settings should then "
     "show <b>Last sync: just now</b>. Tap <b>Get my Apple Health data</b> on the Check in page to bring "
     "the numbers into your tide."),
]

FIELDS = [
    ["Setting", "What to enter"],
    ["URL", "{url}"],
    ["Header", "Key: <b>Authorization</b> &nbsp;&nbsp; Value: <b>Bearer</b> followed by your code (tw_...)"],
    ["Data type", "Health Metrics"],
    ["Metrics", "Sleep Analysis, Blood Pressure, Resting Heart Rate (optional: Heart Rate Variability, Steps)"],
    ["Export format", "JSON"],
    ["Date range", "Last 7 days (or since last sync)"],
    ["Group by", "Days (or Hours)"],
    ["How often", "Every hour"],
]

GOOD_TO_KNOW = [
    "Your iPhone sends data in the background when iOS allows, usually about every hour. Apple Health is "
    "locked while the phone is locked, so data goes out after the phone has been unlocked.",
    "Blood pressure only appears if your cuff saves readings to Apple Health (many Omron and Withings cuffs "
    "do). Sleep and resting heart rate come from an Apple Watch, or sleep from your iPhone's sleep schedule.",
    "Safety: a new blood pressure reading is checked the moment it arrives. If it needs care, Tidewell shows "
    "an alert the next time you open it (or within a minute if it is open), and your support person is "
    "texted for an emergency if you agreed to that. Tidewell does not replace calling 911.",
    "Your own entries always win: Apple Health never overwrites sleep you typed or said yourself.",
    "To stop sharing, tap <b>Disconnect</b> in Tidewell Settings, or delete the automation on the iPhone. "
    "If you lose the code or change phones, create a new one; the old phone stops working.",
]


def build(ingest_url: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title="Connect Apple Health to Tidewell", author="Tidewell")
    ss = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=ss["Title"], textColor=NAVY, fontSize=21, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=12, spaceAfter=5)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10.5, leading=14.5, textColor=NAVY)
    small = ParagraphStyle("s", parent=body, fontSize=8.5, leading=11, textColor=colors.HexColor("#4a5a70"))
    mono = ParagraphStyle("m", parent=body, fontName="Courier-Bold", fontSize=9.5, leading=12)

    out = [
        Paragraph("Connect Apple Health to Tidewell", h),
        Paragraph("Send your sleep, blood pressure and resting heart rate from your iPhone, so you don't have "
                  "to type them. Set it up once; it takes about 10 minutes.", body),
        Spacer(1, 6),
        Table([[Paragraph("<b>You need:</b> an iPhone with the Health app, your Tidewell login, and ideally an "
                          "Apple Watch and/or a blood pressure cuff that saves to Apple Health.", body)]],
              colWidths=[7.1 * inch],
              style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), SAND), ("BOX", (0, 0), (-1, -1), 0, SAND),
                                ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 8)])),
    ]
    for i, (title, text) in enumerate(STEPS, 1):
        block = [Paragraph(f"Step {i}. {title}", h2), Paragraph(text, body)]
        if title == "Create the automation":
            rows = [[Paragraph(f"<b>{a}</b>", body), Paragraph(b.replace("{url}", ingest_url), mono if a == "URL" else body)]
                    for a, b in FIELDS[1:]]
            block.append(Spacer(1, 4))
            block.append(Table([[Paragraph("<b>Setting</b>", body), Paragraph("<b>What to enter</b>", body)]] + rows,
                               colWidths=[1.6 * inch, 5.5 * inch], style=TableStyle([
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f1f2")),
                                   ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d6df")),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])))
            block.append(Spacer(1, 3))
            block.append(Paragraph("Write <b>Bearer</b>, one space, then the code. Names of these settings can differ "
                                   "slightly between app versions.", small))
        out.append(KeepTogether(block))
    out.append(Paragraph("Good to know", h2))
    out += [Paragraph(f"&bull; {t}", body) for t in GOOD_TO_KNOW]
    out += [Spacer(1, 10),
            Paragraph("This guide doesn't contain your connection code on purpose. Treat the code like a password. "
                      "Health Auto Export is a third-party app, not made by Apple or Tidewell. Tidewell does not "
                      "diagnose; in an emergency call 911.", small)]
    doc.build(out)
    return buf.getvalue()
