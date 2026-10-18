"""Guideline answers grounded in trusted sources, instead of a vector index.

1. Claude with the web search tool, restricted (allowed_domains) to the trusted sites below. Each
   sentence comes back with the page URL and the exact passage it relies on.
2. Gemini with the Google Search tool (+ URL context for our curated guideline pages). The
model is told to search only trusted health sites, and we keep ONLY citations whose domain is on the
allowlist below, so an answer can never cite a random blog. If no trusted citation comes back (or
the call fails), we fall back to the curated chunks in clinical_assets/guidelines.json, matched by
keywords. Answers never diagnose and never recommend medication changes.

Gemini API (google-genai): GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch()),
types.Tool(url_context=types.UrlContext())]); citations in
response.candidates[0].grounding_metadata.grounding_chunks[].web.{uri,title,domain}.
Docs: https://ai.google.dev/gemini-api/docs/google-search
"""
import json
import logging
import re
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

from google.genai import types

from app.ai import _claude
from app.ai._gemini import generate
from app.ai.topic import OFF_TOPIC_REPLY
from app.config import BACKEND_DIR, get_settings

log = logging.getLogger("tidewell.guidelines")

GUIDELINES_FILE = BACKEND_DIR.parent / "clinical_assets" / "guidelines.json"

# Trusted public-health and clinical sources. Subdomains count (e.g. www.cdc.gov, pmc.ncbi.nlm.nih.gov).
BASE_TRUSTED = {
    "cdc.gov", "nih.gov", "who.int", "acog.org", "postpartum.net", "womenshealth.gov", "hrsa.gov",
    "medlineplus.gov", "marchofdimes.org", "aap.org", "awhonn.org", "nichd.nih.gov", "mayoclinic.org",
    "clevelandclinic.org", "healthychildren.org",
}

SYSTEM = (
    "You answer questions from a parent in the year after giving birth. Use Google Search and rely ONLY "
    "on these trusted sites: {sites}. Add site: filters to your searches (for example site:cdc.gov). "
    "Answer in 2 to 4 short, plain sentences that will be read aloud. Never diagnose, never recommend "
    "starting, stopping or changing a medication or dose; for medication questions say to ask their "
    "doctor, midwife or pharmacist. If something sounds urgent, say to call their provider now or 911. "
    "Only answer pregnancy, birth, postpartum, feeding, mood or newborn questions. "
    "Mention which organisation the information comes from (for example 'The CDC says...')."
)

OFF_TOPIC_MARK = "OFF_TOPIC"

CLAUDE_SYSTEM = (
    "You are Tidewell, a postpartum care companion. You answer questions from a parent in the year after "
    "giving birth, using the web search tool (it only reaches trusted health organisations). Search "
    "before answering and base every fact on what you found. Answer in 2 to 4 short, warm, plain "
    "sentences that will be read aloud; no headings, lists or markdown, and do not describe your "
    "searching. Name the organisation the advice comes from (for example 'The CDC says...'). Never "
    "diagnose, and never recommend starting, stopping or changing a medication or dose: for medication "
    "questions share what the source says and tell them to check with their doctor, midwife or "
    "pharmacist. If something sounds urgent, say to call their provider now, or 911 in an emergency. "
    "Only answer questions about pregnancy, birth, postpartum recovery, the parent's own health, "
    "feeding, sleep, mood, contraception or newborn care. For anything else reply with exactly "
    f"{OFF_TOPIC_MARK} and nothing more."
)


@lru_cache
def _chunks() -> list[dict]:
    try:
        data = json.loads(GUIDELINES_FILE.read_text(encoding="utf-8"))
        return [c for c in data if c.get("ready_to_ingest", True)]
    except (OSError, ValueError):
        log.warning("could not read %s", GUIDELINES_FILE)
        return []


def _domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


@lru_cache
def trusted_domains() -> frozenset[str]:
    return frozenset(BASE_TRUSTED | {_domain(c["url"]) for c in _chunks() if c.get("url")})


def is_trusted(domain_or_url: str) -> bool:
    d = _domain(domain_or_url) if "://" in domain_or_url else domain_or_url.lower().removeprefix("www.")
    return any(d == t or d.endswith("." + t) for t in trusted_domains())


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", s.lower())}


def local_answer(question: str) -> Optional[dict]:
    """Best keyword match in guidelines.json (offline fallback)."""
    q = _words(question)
    best, best_score = None, 0
    for c in _chunks():
        text = " ".join([c.get("section", ""), c.get("content", ""), " ".join(c.get("example_phrases", []))])
        score = len(q & _words(text))
        if score > best_score:
            best, best_score = c, score
    if not best or best_score < 2:
        return None
    return {
        "answer": best["content"],
        "citations": [_cite(f'{best["source"]}: {best["section"]}', best["url"])],
        "source": "curated",
    }


def _cite(title: str, url: str, quote: str = "") -> dict:
    return {"title": title or _domain(url), "url": url, "site": _domain(url), "quote": " ".join(quote.split())[:220]}


def _claude_answer(question: str, contents: str) -> Optional[dict]:
    """Claude + the web search tool, locked to the trusted domains. Citations are real page URLs with
    the exact passage each sentence relies on (web_search_result_location.cited_text)."""
    client = _claude.get_client()
    if not client:
        return None
    tools = [{
        "type": "web_search_20260209", "name": "web_search", "max_uses": 3,
        "allowed_domains": sorted(trusted_domains())[:64],  # API limit: 64 hostnames
        "user_location": {"type": "approximate", "country": "US"},
    }]
    messages = [{"role": "user", "content": contents}]
    for _ in range(3):  # a long search turn can pause; resend to let the server resume it
        r = client.beta.messages.create(
            model=get_settings().claude_model, max_tokens=4000,
            system=CLAUDE_SYSTEM, messages=messages, tools=tools,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        if r.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": r.content}]
    if r.stop_reason == "refusal":
        return None
    # The answer is the text after the last search result (anything before it is the model working).
    last_result = max((i for i, b in enumerate(r.content) if b.type == "web_search_tool_result"), default=-1)
    parts, cites, seen = [], [], set()
    for b in r.content[last_result + 1:]:
        if b.type != "text":
            continue
        parts.append(b.text)
        for c in getattr(b, "citations", None) or []:
            url = getattr(c, "url", "")
            if getattr(c, "type", "") == "web_search_result_location" and is_trusted(url) and url not in seen:
                seen.add(url)
                cites.append(_cite(getattr(c, "title", ""), url, getattr(c, "cited_text", "")))
    answer = re.sub(r"\s+", " ", "".join(parts)).strip()
    if answer == OFF_TOPIC_MARK:
        return {"answer": OFF_TOPIC_REPLY, "citations": [], "source": "off_topic"}
    if answer and cites:
        return {"answer": answer, "citations": cites[:4], "source": "web"}
    log.info("Claude answer had no trusted citation; trying Gemini")
    return None


def ask(question: str, patient_context: Optional[str] = None) -> dict:
    """{answer, citations: [{title, url, site, quote}], source: "web" | "curated" | "none" | "off_topic"}.
    Claude web search first, then Gemini Google Search grounding, then the curated guidelines. Never raises."""
    sites = ", ".join(sorted(trusted_domains()))
    contents = (f"About this parent: {patient_context}\n\n" if patient_context else "") + f"Question: {question}"
    try:
        out = _claude_answer(question, contents)
        if out:
            return out
    except Exception as e:  # noqa: BLE001
        log.warning("Claude web search failed (%s: %s); trying Gemini", type(e).__name__, e)
    try:
        r = generate(
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM.format(sites=sites),
                tools=[types.Tool(google_search=types.GoogleSearch()), types.Tool(url_context=types.UrlContext())],
                temperature=0.2,
            ),
        )
        meta = r.candidates[0].grounding_metadata if r.candidates else None
        cites, seen = [], set()
        for ch in (meta.grounding_chunks or []) if meta else []:
            web = getattr(ch, "web", None)
            if not web:
                continue
            dom = (web.domain or web.title or "").lower()
            if not is_trusted(dom) or dom in seen:
                continue
            seen.add(dom)
            # web.uri is a Google redirect; link to the site itself for a clean, trustworthy citation.
            cites.append(_cite(web.title or dom, f"https://{dom}"))
        answer = (r.text or "").strip()
        if answer and cites:
            return {"answer": answer, "citations": cites[:3], "source": "web"}
        log.info("web answer had no trusted citation; using curated guidelines")
    except Exception as e:  # noqa: BLE001
        log.warning("grounded search failed (%s: %s); using curated guidelines", type(e).__name__, e)
    return local_answer(question) or {
        "answer": "I couldn't find trusted guidance on that just now. Please ask your doctor, midwife or care team.",
        "citations": [], "source": "none",
    }
