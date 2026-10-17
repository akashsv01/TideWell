from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_visit_summary(filename="maya_visit_summary.pdf"):
    # Create a canvas
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Tidewell Visit Summary")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, "Generated for provider review. Summarizes past 21 days of voice check-ins.")
    
    c.setStrokeColor(colors.grey)
    c.line(50, height - 80, width - 50, height - 80)
    
    # Patient Basics
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 110, "Patient Profile: Maya (Day 18 Postpartum)")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 130, "Delivery: C-section at 38 weeks")
    c.drawString(50, height - 150, "History: Gestational hypertension, history of depression")
    c.drawString(50, height - 170, "Status: Breastfeeding")
    
    # Risk Tier & Alert
    c.setFillColor(colors.orange)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 210, "CURRENT TIER: AMBER (Recommend Visit in 1-3 Days)")
    c.setFillColor(colors.black)
    
    # Clinical Reasons
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 240, "Key Flags & Patterns:")
    c.setFont("Helvetica", 12)
    c.drawString(70, height - 260, "- Postpartum High BP: Blood pressure rose across 4 consecutive readings.")
    c.drawString(70, height - 280, "- Headaches reported on 3 of the last 7 days.")
    c.drawString(70, height - 300, "- Depression/Anxiety: EPDS score increased from 7 to 11 in one week.")
    c.drawString(70, height - 320, "- Sleep: Averaging only 3.8 hours per night over the last 7 days.")
    
    # Vitals Trend
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 360, "Recent Vitals (Last 4 BP Readings)")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 380, "1. 132 / 84 mmHg")
    c.drawString(50, height - 400, "2. 136 / 88 mmHg")
    c.drawString(50, height - 420, "3. 141 / 90 mmHg")
    c.setFillColor(colors.red)
    c.drawString(50, height - 440, "4. 144 / 92 mmHg (Latest)")
    c.setFillColor(colors.black)
    
    # Suggested Questions for Doctor
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 490, "Questions for the Doctor:")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 510, "1. My blood pressure has been rising steadily. Do I need to adjust my medication?")
    c.drawString(50, height - 530, "2. My headaches have been frequent this week. Is this related to the BP?")
    c.drawString(50, height - 550, "3. I am struggling with sleep and mood. Can we discuss mental health support?")
    
    # Footer statement
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.dimgrey)
    c.drawString(50, 50, "Tidewell does not diagnose. This report aggregates patient self-reported data and vitals.")
    
    # Save PDF
    c.save()
    print(f"Success! {filename} has been generated.")

if __name__ == "__main__":
    generate_visit_summary()