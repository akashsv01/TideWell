# Tidewell Clinical Thresholds & Logic
*Sourced from ACOG and CDC Guidelines*

## 1. Blood Pressure (Postpartum Hypertension & Preeclampsia)
*   **Green (Normal):** Systolic < 120 and Diastolic < 80 mmHg.
*   **Watch/Amber (Elevated/Stage 1):** Systolic >= 140 OR Diastolic >= 90 mmHg. 
    * *Logic:* If a patient hits this threshold, or has 4 consecutive rising readings approaching this threshold, trigger Amber tier and offer an appointment within 1-3 days.
*   **Red (Severe/Emergency):** Systolic >= 160 OR Diastolic >= 110 mmHg.
    * *Logic:* This is severe preeclampsia range (stroke risk). Must immediately trigger the emergency UI card and text support person.

## 2. EPDS (Edinburgh Postnatal Depression Scale)
*   **Green (Normal):** Score 0 - 8.
*   **Watch/Amber (Possible Depression):** Score >= 10.
    * *Logic:* A score of 10 or higher, or a rapidly rising trend (e.g., 7 to 11 in one week), triggers the Amber tier to suggest a mental health check-in.
*   **Red (Self-Harm Risk):** Item 10 Score > 0.
    * *Logic:* Item 10 asks about self-harm. Any affirmative answer bypasses the AI completely and triggers the 988/911 emergency protocol.
