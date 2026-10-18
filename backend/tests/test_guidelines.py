from types import SimpleNamespace

from google.genai import types

from app.ai import guidelines


def _entry(section: str, phrases: str = "") -> tuple[dict, set[str], set[str]]:
    chunk = {
        "section": section,
        "content": "This content contains general words that should not create a match.",
        "app_guidance": f"Guidance for {section}.",
        "source": "Trusted source",
        "url": "https://cdc.gov/example",
    }
    return chunk, guidelines._words(section), guidelines._words(phrases)


def test_local_answer_uses_specific_topic_match(monkeypatch):
    monkeypatch.setattr(
        guidelines,
        "_index",
        lambda: [_entry("Postpartum Blood Pressure", "my blood pressure is high")],
    )

    result = guidelines.local_answer("My blood pressure is high")

    assert result is not None
    assert result["answer"] == "Guidance for Postpartum Blood Pressure."
    assert result["source"] == "curated"


def test_local_answer_does_not_match_only_generic_content_words(monkeypatch):
    monkeypatch.setattr(guidelines, "_index", lambda: [_entry("Postpartum Blood Pressure")])

    assert guidelines.local_answer("What should I do after delivery?") is None


def test_local_answer_declines_ambiguous_topic(monkeypatch):
    monkeypatch.setattr(
        guidelines,
        "_index",
        lambda: [
            _entry("Postpartum Sleep"),
            _entry("Newborn Sleep"),
        ],
    )

    assert guidelines.local_answer("Tell me about sleep") is None


def test_local_answer_does_not_confuse_infant_crying_with_mood_guidance(monkeypatch):
    monkeypatch.setattr(
        guidelines,
        "_index",
        lambda: [_entry("Low Mood", "still crying every day")],
    )

    assert guidelines.local_answer("Why is my newborn crying after every feeding?") is None


def test_ask_does_not_return_an_unmatched_curated_answer(monkeypatch):
    monkeypatch.setattr(guidelines, "_gemini_answer", lambda _: None)
    monkeypatch.setattr(guidelines, "_claude_answer", lambda _: None)
    monkeypatch.setattr(guidelines, "_gemini_url_answer", lambda *_: None)
    monkeypatch.setattr(guidelines, "_index", lambda: [_entry("Postpartum Blood Pressure")])

    result = guidelines.ask("What should I do about a new concern after delivery?")

    assert result["source"] == "none"
    assert result["citations"] == []
    assert "couldn't find trusted guidance" in result["answer"]


def _url_response(text: str, urls: list[tuple[str, bool]]):
    ok, err = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS, types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_ERROR
    meta = SimpleNamespace(url_metadata=[SimpleNamespace(retrieved_url=u, url_retrieval_status=ok if fetched else err)
                                         for u, fetched in urls])
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(url_context_metadata=meta)])


def test_url_fallback_cites_only_fetched_trusted_pages(monkeypatch):
    lactmed = "https://www.ncbi.nlm.nih.gov/books/NBK500986/"
    monkeypatch.setattr(guidelines, "candidate_urls", lambda _: [lactmed])
    monkeypatch.setattr(guidelines, "generate", lambda **_: _url_response(
        "LactMed says ibuprofen is a preferred choice while nursing.",
        [(lactmed, True), ("https://www.cdc.gov/not-fetched", False), ("https://randomblog.com/post", True)],
    ))

    result = guidelines._gemini_url_answer("Can I take ibuprofen while breastfeeding?", "Question: ...")

    assert result["source"] == "web"
    assert [(c["title"], c["url"]) for c in result["citations"]] == [("NIH LactMed", lactmed)]


def test_url_fallback_declines_when_pages_do_not_answer(monkeypatch):
    monkeypatch.setattr(guidelines, "candidate_urls", lambda _: ["https://medlineplus.gov/bleeding.html"])
    monkeypatch.setattr(guidelines, "generate", lambda **_: _url_response(
        "NO_ANSWER", [("https://medlineplus.gov/bleeding.html", True)]))

    assert guidelines._gemini_url_answer("How much bleeding is normal?", "Question: ...") is None


def test_ask_uses_url_fallback_when_search_and_claude_fail(monkeypatch):
    def search_down(_):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(guidelines, "_gemini_answer", search_down)
    monkeypatch.setattr(guidelines, "_claude_answer", search_down)
    monkeypatch.setattr(guidelines, "_gemini_url_answer",
                        lambda q, _: {"answer": f"answer to {q}", "citations": [], "source": "web"})

    assert guidelines.ask("Is my blood pressure high?")["answer"] == "answer to Is my blood pressure high?"
