# Tidewell Clinical Thresholds & Logic

## 1. Blood Pressure (Hypertension & Preeclampsia)
*   **Red (Emergency):** Systolic >= 160 OR Diastolic >= 110 mmHg. (Source: ACOG)
*   **Red (Emergency w/ Symptoms):** Systolic >= 140 OR Diastolic >= 90 mmHg PLUS severe headache or vision changes. (Source: CDC)
*   **Amber (Elevated/Stage 1):** Systolic >= 140 OR Diastolic >= 90 mmHg. Action: Offer appointment within 1-3 days based on upward trend. (Source: Kansas Perinatal Quality Collaborative)

## 2. Fever & Infection
*   **Red (Emergency):** Temperature >= 100.4°F (38°C). (Source: CDC)

## 3. Postpartum Hemorrhage
*   **Red (Emergency):** Bleeding that soaks through one or more pads in an hour, or passing blood clots bigger than an egg. (Source: CDC)

## 4. Mental Health (EPDS)
*   **Watch/Amber:** Total score >= 10. (Standard cutoff for "possible depression" to maximize early intervention).
*   **Red (Self-Harm/Q10):** Handled directly by app logic, NOT AI phrase matching.
    *   "Never" -> Green.
    *   "Hardly ever" / "Sometimes" -> Urgent Card + Follow-up question ("Are you thinking of ending your life or hurting yourself?").
    *   "Yes, quite often" OR affirmative to follow-up -> Immediate 988/911 Emergency Card.

## 5. "Watch" Tier Criteria
*   Assigned when a patient has a history of depression/anxiety, an EPDS score between 10-12, or BP trending upwards but below 140/90. (Confirmed by Clinical Advisor).
