"""One shared google-genai client (genai.Client(api_key=..., http_options=...)).
Reusing it avoids per-call setup and the "client has been closed" error when a temporary client is
garbage-collected mid-request. Retries are capped because the SDK's default retry loop turned one
slow call into ~60 s. The API rejects request deadlines under 10 s."""
from functools import lru_cache

from google import genai
from google.genai import types

from app.config import get_settings

REQUEST_TIMEOUT_MS = 20_000


@lru_cache
def get_client() -> genai.Client:
    return genai.Client(
        api_key=get_settings().gemini_api_key,
        http_options=types.HttpOptions(
            timeout=REQUEST_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=2)
        ),
    )
