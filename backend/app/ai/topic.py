"""Topic guardrail for Ask: Tidewell only answers pregnancy, birth and postpartum questions.

Order: obvious postpartum keywords pass at once (no AI call); anything else goes to a small
classifier (Claude structured output, else Gemini JSON). If both are unavailable we decline, since the
keyword list already covers everyday postpartum questions. The answer prompt also refuses off-topic
questions (two layers). A question about the parent's own body or mood counts as on-topic: in the
year after birth it often is.
"""
import json
import logging
import re

from google.genai import types
from pydantic import BaseModel

from app.ai import _claude
from app.ai._gemini import generate
from app.config import get_settings

log = logging.getLogger("tidewell.topic")

OFF_TOPIC_REPLY = (
    "I can only help with pregnancy, birth and life after birth: your recovery, feeding, sleep, mood, "
    "your numbers, and your baby's first months. Try asking me something about that."
)

_ON_TOPIC = re.compile(
    r"\b(postpartum|post-partum|pregnan\w*|birth\w*|deliver\w*|labou?r|c-?section|cesarean|caesarean|"
    r"incision|stitch\w*|perine\w*|tear(ing)?|lochia|bleed\w*|clots?|uterus|womb|placenta|"
    r"breast\w*|nurs(e|ing)|latch\w*|nipple\w*|milk|pump\w*|formula|bottle|mastitis|feeds?|feeding|fed|"
    r"baby|babies|newborn|infant|nappy|diaper\w*|colic|swaddl\w*|"
    r"pre-?eclampsia|eclampsia|blood pressure|bp|hypertension|gestational|"
    r"epds|mood|baby blues|depress\w*|anxi\w*|intrusive|"
    r"midwi\w*|ob-?gyn|obstetric\w*|doula|lactation|pelvic|kegel\w*|contracepti\w*|"
    r"period|menstrua\w*|hormon\w*|hair|night sweats|sleep\w*|tired|exhaust\w*|headaches?|pain\w*|fever|swell\w*|dizz\w*|"
    r"medic\w*|ibuprofen|acetaminophen|paracetamol|tylenol|advil|caffeine|coffee|alcohol|exercis\w*|"
    r"weight|diet|vitamin\w*|sex|tidewell)\b",
    re.I,
)

CLASSIFIER = (
    "You decide whether a question belongs in a postpartum care app. ON TOPIC: pregnancy, labour and "
    "birth, recovery after birth, the parent's own physical or mental health (they gave birth within "
    "the last year, so symptoms like headaches, pain, tiredness or low mood count), feeding, sleep, "
    "contraception and sex after birth, newborn and infant care, and using the app. OFF TOPIC: anything "
    "else, such as coding, homework, news, sport, recipes, travel, money, celebrities, or general "
    "questions that have nothing to do with the parent's health or baby."
)


class Verdict(BaseModel):
    on_topic: bool


def _claude_verdict(question: str) -> bool | None:
    client = _claude.get_client()
    if not client:
        return None
    r = client.messages.parse(
        model=get_settings().claude_model,
        max_tokens=2000,
        system=CLASSIFIER,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": f"Question: {question}"}],
        output_format=Verdict,
    )
    return r.parsed_output.on_topic if r.parsed_output else None


def _gemini_verdict(question: str) -> bool | None:
    if not get_settings().gemini_api_key:
        return None
    r = generate(
        contents=f"Question: {question}",
        config=types.GenerateContentConfig(
            system_instruction=CLASSIFIER, temperature=0,
            response_mime_type="application/json", response_schema=Verdict,
        ),
    )
    return bool(json.loads(r.text or "{}").get("on_topic", True))


def is_on_topic(question: str) -> bool:
    if _ON_TOPIC.search(question):
        return True
    for name, check in (("claude", _claude_verdict), ("gemini", _gemini_verdict)):
        try:
            v = check(question)
            if v is not None:
                return v
        except Exception as e:  # noqa: BLE001 - fall through to the next checker
            log.warning("%s topic check failed (%s: %s)", name, type(e).__name__, e)
    return False
