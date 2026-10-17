"""One shared google-genai client (genai.Client(api_key=..., http_options=...)), plus generate(),
which falls back to GEMINI_FAST_MODEL when the main model is out of quota or overloaded.

Reusing the client avoids per-call setup and the "client has been closed" error when a temporary
client is garbage-collected mid-request. SDK retries are off because its retry loop turned one slow
call into ~60 s; generate() falls back to the other model instead. The API rejects request
deadlines under 10 s. Free-tier keys allow ~20 requests/day per model, and each model has its own quota.
"""
import logging
from functools import lru_cache

from google import genai
from google.genai import errors, types

from app.config import get_settings

log = logging.getLogger("tidewell.gemini")

REQUEST_TIMEOUT_MS = 20_000
_FALLBACK_STATUS = {429, 500, 503, 504}  # quota, server error, overloaded, deadline


@lru_cache
def get_client() -> genai.Client:
    return genai.Client(
        api_key=get_settings().gemini_api_key,
        http_options=types.HttpOptions(
            timeout=REQUEST_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )


def generate(contents, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
    """generate_content on GEMINI_MODEL, then GEMINI_FAST_MODEL if the first is unavailable."""
    s = get_settings()
    models = list(dict.fromkeys([s.gemini_model, s.gemini_fast_model]))
    for i, model in enumerate(models):
        try:
            return get_client().models.generate_content(model=model, contents=contents, config=config)
        except errors.APIError as e:
            if e.code not in _FALLBACK_STATUS or i == len(models) - 1:
                raise
            log.warning("%s unavailable (%s); falling back to %s", model, e.code, models[i + 1])
    raise RuntimeError("unreachable")
