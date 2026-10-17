"""Patient category assignment at onboarding (plan section 8, step 1). Rules only, multi-label.

CLINICAL: which categories apply to everyone vs only some patients is a clinical decision.
The "always" ones below are conservative defaults; confirm with Person 4 before the demo.
"""
from typing import Iterable

HIGH_BP = "high_blood_pressure"
DEPRESSION = "depression_anxiety"
POST_CESAREAN = "post_cesarean"
BLEEDING_INFECTION = "bleeding_infection"
GESTATIONAL_DIABETES = "gestational_diabetes"
BREASTFEEDING = "breastfeeding_complications"
HEART_STRAIN = "heart_strain"
DISENGAGEMENT = "disengagement"

_BP_WORDS = ("hypertension", "preeclampsia", "pre-eclampsia", "eclampsia", "high blood pressure", "blood pressure")
_DIABETES_WORDS = ("diabetes", "gdm")
_HEART_WORDS = ("cardiac", "cardiomyopathy", "heart")


def _mentions(conditions: Iterable[str], words: tuple[str, ...]) -> bool:
    text = " ".join(conditions).lower()
    return any(w in text for w in words)


def assign(delivery_type: str, conditions: list[str], breastfeeding: bool) -> list[str]:
    cats = [DEPRESSION, BLEEDING_INFECTION, DISENGAGEMENT]  # apply to every patient
    if _mentions(conditions, _BP_WORDS):
        cats.append(HIGH_BP)
    if delivery_type == "c-section":
        cats.append(POST_CESAREAN)
    if _mentions(conditions, _DIABETES_WORDS):
        cats.append(GESTATIONAL_DIABETES)
    if breastfeeding:
        cats.append(BREASTFEEDING)
    if _mentions(conditions, _HEART_WORDS):
        cats.append(HEART_STRAIN)
    return cats
