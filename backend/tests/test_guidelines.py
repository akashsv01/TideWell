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
    monkeypatch.setattr(guidelines, "_index", lambda: [_entry("Postpartum Blood Pressure")])

    result = guidelines.ask("What should I do about a new concern after delivery?")

    assert result["source"] == "none"
    assert result["citations"] == []
    assert "couldn't find trusted guidance" in result["answer"]
