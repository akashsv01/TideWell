"""One shared Anthropic client, or None when ANTHROPIC_API_KEY is not set (callers fall back to Gemini).

Claude API (anthropic SDK): client.messages.create(...); server tool web_search_20260209 with
allowed_domains; cited text blocks carry citations of type web_search_result_location
{url, title, cited_text}. Docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
"""
from functools import lru_cache
from typing import Optional

import anthropic

from app.config import get_settings

REQUEST_TIMEOUT_S = 45.0  # web search turns run several searches server-side


@lru_cache
def get_client() -> Optional[anthropic.Anthropic]:
    key = get_settings().anthropic_api_key
    return anthropic.Anthropic(api_key=key, timeout=REQUEST_TIMEOUT_S, max_retries=1) if key else None
