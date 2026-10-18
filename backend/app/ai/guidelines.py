"""Guideline answers grounded in trusted sources, instead of a vector index.

Primary: Gemini with the Google Search tool (+ URL context for our curated guideline pages). The
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

from app.ai._gemini import generate
from app.config import BACKEND_DIR

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
    "Mention which organisation the information comes from (for example 'The CDC says...')."
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
        "citations": [{"title": f'{best["source"]}: {best["section"]}', "url": best["url"]}],
        "source": "curated",
    }


def ask(question: str, patient_context: Optional[str] = None) -> dict:
    """{answer, citations: [{title, url}], source: "web" | "curated" | "none"}. Never raises."""
    sites = ", ".join(sorted(trusted_domains()))
    contents = (f"About this parent: {patient_context}\n\n" if patient_context else "") + f"Question: {question}"
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
            cites.append({"title": web.title or dom, "url": f"https://{dom}"})
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
