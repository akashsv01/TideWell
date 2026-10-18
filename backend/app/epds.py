"""Edinburgh Postnatal Depression Scale (EPDS), the weekly mood check.

Source: Cox, J.L., Holden, J.M., and Sagovsky, R. (1987). Detection of postnatal depression:
Development of the 10-item Edinburgh Postnatal Depression Scale. British Journal of Psychiatry
150:782-786. The authors allow the scale to be reproduced without further permission provided they
respect copyright by quoting the names of the authors, the title and the source in all reproduced copies.

Scoring is done here, never in the browser. Options are listed in display order with their score:
questions 1, 2 and 4 score 0-3 top to bottom; 3 and 5-10 are reverse scored (3-0).
Cutoffs and the question 10 rule follow clinical_assets/thresholds.md:
  total 10-12 -> watch, 13+ -> amber (a screening score, not a diagnosis)
  Q10 "Never" -> nothing; "Hardly ever"/"Sometimes" -> URGENT card + follow-up question;
  "Yes, quite often", or yes/unsure to the follow-up -> EMERGENCY card.
"""
from typing import Literal, Optional

from app.ai.red_flags import EMERGENCY_RESPONSE, URGENT_RESPONSE

CITATION = (
    "Edinburgh Postnatal Depression Scale. Cox, J.L., Holden, J.M., and Sagovsky, R. (1987). "
    "British Journal of Psychiatry 150:782-786."
)
FOLLOWUP_QUESTION = "Are you thinking of ending your life or hurting yourself?"

# (question, [(option, score), ...]) in display order.
ITEMS: list[tuple[str, list[tuple[str, int]]]] = [
    ("I have been able to laugh and see the funny side of things", [
        ("As much as I always could", 0), ("Not quite so much now", 1),
        ("Definitely not so much now", 2), ("Not at all", 3)]),
    ("I have looked forward with enjoyment to things", [
        ("As much as I ever did", 0), ("Rather less than I used to", 1),
        ("Definitely less than I used to", 2), ("Hardly at all", 3)]),
    ("I have blamed myself unnecessarily when things went wrong", [
        ("Yes, most of the time", 3), ("Yes, some of the time", 2),
        ("Not very often", 1), ("No, never", 0)]),
    ("I have been anxious or worried for no good reason", [
        ("No, not at all", 0), ("Hardly ever", 1), ("Yes, sometimes", 2), ("Yes, very often", 3)]),
    ("I have felt scared or panicky for no very good reason", [
        ("Yes, quite a lot", 3), ("Yes, sometimes", 2), ("No, not much", 1), ("No, not at all", 0)]),
    ("Things have been getting on top of me", [
        ("Yes, most of the time I haven't been able to cope at all", 3),
        ("Yes, sometimes I haven't been coping as well as usual", 2),
        ("No, most of the time I have coped quite well", 1),
        ("No, I have been coping as well as ever", 0)]),
    ("I have been so unhappy that I have had difficulty sleeping", [
        ("Yes, most of the time", 3), ("Yes, sometimes", 2), ("Not very often", 1), ("No, not at all", 0)]),
    ("I have felt sad or miserable", [
        ("Yes, most of the time", 3), ("Yes, quite often", 2), ("Not very often", 1), ("No, not at all", 0)]),
    ("I have been so unhappy that I have been crying", [
        ("Yes, most of the time", 3), ("Yes, quite often", 2), ("Only occasionally", 1), ("No, never", 0)]),
    ("The thought of harming myself has occurred to me", [
        ("Yes, quite often", 3), ("Sometimes", 2), ("Hardly ever", 1), ("Never", 0)]),
]

WATCH_AT = 10  # thresholds.md: 10-12 watch
AMBER_AT = 13  # thresholds.md: 13+ amber


def questions() -> list[dict]:
    """For the frontend: question text and option labels only (scores stay on the server)."""
    return [{"number": i + 1, "text": q, "options": [o for o, _ in opts]} for i, (q, opts) in enumerate(ITEMS)]


def score(answers: list[int]) -> tuple[int, int]:
    """(total 0-30, item 10 score 0-3) from option indexes. Raises ValueError on a bad index."""
    if len(answers) != len(ITEMS):
        raise ValueError("answer all 10 questions")
    points = []
    for i, a in enumerate(answers):
        opts = ITEMS[i][1]
        if not 0 <= a < len(opts):
            raise ValueError(f"question {i + 1}: choose one of the {len(opts)} options")
        points.append(opts[a][1])
    return sum(points), points[9]


def band(total: int) -> Literal["low", "watch", "amber"]:
    return "amber" if total >= AMBER_AT else "watch" if total >= WATCH_AT else "low"


def item10_outcome(item10: int) -> tuple[Optional[str], bool]:
    """(level, needs_followup) for the question 10 score."""
    if item10 >= 3:
        return "emergency", False
    if item10 >= 1:
        return "urgent", True
    return None, False


def followup_outcome(answer: str) -> tuple[str, str]:
    """yes or unsure -> emergency (clinical_assets/guidelines.json mh-07); no -> urgent."""
    if answer in ("yes", "unsure"):
        return "emergency", EMERGENCY_RESPONSE
    return "urgent", URGENT_RESPONSE


def response_for(level: Optional[str]) -> Optional[str]:
    return {"emergency": EMERGENCY_RESPONSE, "urgent": URGENT_RESPONSE}.get(level or "")
