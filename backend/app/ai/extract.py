"""Gemini structured extraction of check-in metrics.

Confirmed API (google-genai SDK):
  client = genai.Client(api_key=...)
  client.models.generate_content(model=..., contents=...,
      config=types.GenerateContentConfig(response_mime_type="application/json",
                                         response_schema=PydanticModel))
  response.text -> JSON string; response.parsed -> model instance (None if it fails validation)
Tool calling (for agent.py, Phase 1): GenerateContentConfig(tools=[python_fn, ...]) runs functions
  automatically; or types.Tool(function_declarations=[types.FunctionDeclaration(...)]) and read
  response.function_calls for manual control.
Model: stable Flash IDs today are gemini-3.8-flash / gemini-3.6-flash (alias: gemini-flash-latest).
Docs: https://github.com/googleapis/python-genai  |  https://ai.google.dev/gemini-api/docs/models
"""
import json

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import CheckinMetrics

SYSTEM = (
    "You extract structured health check-in data from what a postpartum parent said. "
    "Only record what was explicitly said; leave a field null (or false/empty) when it was not mentioned. "
    "Never infer a diagnosis. Scales are 0-10. Blood pressure 'X over Y' means bp_sys=X, bp_dia=Y. "
    "Put any other symptoms or concerns in 'mentions' as short phrases."
)

_SCALE_FIELDS = ("mood", "pain", "incision_pain")


def _sanitize(raw: dict) -> dict:
    """Drop values that would fail validation instead of crashing the check-in."""
    out = {k: v for k, v in raw.items() if k in CheckinMetrics.model_fields and v is not None}
    for f in _SCALE_FIELDS:
        if f in out:
            try:
                out[f] = min(10, max(0, int(round(float(out[f])))))
            except (TypeError, ValueError):
                out.pop(f)
    if out.get("bleeding") not in (None, "none", "light", "heavy"):
        out.pop("bleeding")
    if not isinstance(out.get("mentions", []), list):
        out.pop("mentions")
    return out


def extract_metrics(transcript: str) -> CheckinMetrics:
    s = get_settings()
    client = genai.Client(api_key=s.gemini_api_key)
    response = client.models.generate_content(
        model=s.gemini_model,
        contents=transcript,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=CheckinMetrics,
            temperature=0,
        ),
    )
    if isinstance(response.parsed, CheckinMetrics):
        return response.parsed
    try:
        return CheckinMetrics.model_validate(_sanitize(json.loads(response.text or "{}")))
    except Exception:
        return CheckinMetrics()
