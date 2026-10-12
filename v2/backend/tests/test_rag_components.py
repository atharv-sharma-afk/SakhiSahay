from __future__ import annotations

from app.knowledge.chunk import chunk_text
from app.rag.citations import validate_citations
from app.rag.language import detect_language, resolve_language
from app.rag.prompt_builder import build_prompt
from app.rag.safety import screen_question
from app.rag.vector_store import ChunkPayload, ScoredChunk


def _chunk(i: int, url: str, text: str = "evidence text") -> ScoredChunk:
    return ScoredChunk(
        score=0.9,
        payload=ChunkPayload(
            chunk_id=f"src-{i}::000",
            source_id=f"src-{i}",
            title=f"Title {i}",
            publisher="WHO",
            url=url,
            doc_type="fact_sheet",
            topic="menstrual_health",
            section="Key facts",
            language="en",
            published_date=None,
            updated_date=None,
            accessed_date="2026-10-11",
            license_note=None,
            text=text,
        ),
    )


# ---- citations ---------------------------------------------------------------


def test_invalid_markers_and_foreign_urls_are_removed():
    chunks = [_chunk(1, "https://www.who.int/a"), _chunk(2, "https://www.nhs.uk/b")]
    answer = "Cramps are common [S1]. See [S7] and https://example.com/fake plus https://www.nhs.uk/b [S2]."
    result = validate_citations(answer, chunks)
    assert result.cited_indices == [1, 2]
    assert result.removed_markers == 1
    assert result.removed_urls == 1
    assert "[S7]" not in result.text
    assert "example.com" not in result.text
    assert "https://www.nhs.uk/b" in result.text
    assert result.explicit


def test_answer_without_markers_is_flagged_not_explicit():
    result = validate_citations("Plain answer with no citations.", [_chunk(1, "https://www.who.int/a")])
    assert result.cited_indices == []
    assert result.explicit is False


# ---- safety ------------------------------------------------------------------


def test_urgent_patterns_in_three_languages():
    assert screen_question("I am soaking a pad every hour and feel faint").level == "urgent"
    assert screen_question("Main pregnant hoon aur bleeding ho rahi hai").level == "urgent"
    assert screen_question("मुझे बहुत तेज़ दर्द हो रहा है").level == "urgent"
    assert screen_question("I am pregnant and have shoulder pain with spotting").level == "urgent"


def test_advisory_patterns():
    diag = screen_question("Do I have PCOS? My periods are irregular.")
    assert diag.level == "advisory" and "diagnosis_request" in diag.flags
    med = screen_question("Which tablet should I take for period pain?")
    assert "medication_request" in med.flags
    hinglish = screen_question("Period dard ke liye konsi dawai lu?")
    assert "medication_request" in hinglish.flags


def test_ordinary_questions_are_not_flagged():
    assert screen_question("What is a normal menstrual cycle length?").level == "none"
    assert screen_question("What is endometriosis?").level == "none"


# ---- language ----------------------------------------------------------------


def test_language_detection():
    assert detect_language("What causes period pain?") == "en"
    assert detect_language("माहवारी में दर्द क्यों होता है?") == "hi"
    assert detect_language("Periods mein itna dard kyun hota hai?") == "hinglish"
    assert detect_language("PCOS kya hai aur iske symptoms kya hain") == "hinglish"
    assert resolve_language("What is PMS?", "hi") == ("en", "hi")
    assert resolve_language("Periods me dard kyu hota hai", "auto") == ("hinglish", "hinglish")


# ---- chunking ----------------------------------------------------------------


def test_chunking_tracks_sections_and_respects_size():
    text = "## Key facts\n\n" + ("Sentence one about periods. " * 30) + "\n\n## Causes\n\n" + ("Another fact here. " * 40)
    chunks = chunk_text(text, max_chars=500, min_chars=100)
    assert chunks, "expected chunks"
    assert all(c.char_count <= 560 for c in chunks)  # small slack for the overlap paragraph
    assert {c.section for c in chunks} == {"Key facts", "Causes"}
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_short_document_becomes_single_chunk():
    chunks = chunk_text("## Only\n\nShort paragraph.")
    assert len(chunks) == 1 and chunks[0].section == "Only"


# ---- prompt & response parsing ----------------------------------------------


def test_prompt_contains_numbered_evidence_and_compact_system():
    chunks = [_chunk(1, "https://www.who.int/a", "Alpha text"), _chunk(2, "https://www.nhs.uk/b", "Beta text")]
    prompt = build_prompt("What is PMS?", chunks, "hi", "Hindi", tracker_context="- Logged periods: 3")
    assert "[S1] Alpha text" in prompt.user
    assert "[S2] Beta text" in prompt.user
    assert prompt.evidence_ids == [1, 2]
    assert "You are Sakhi, a women's health information assistant." in prompt.system
    assert "INSUFFICIENT_EVIDENCE: true or false." in prompt.system
    assert "Logged periods: 3" in prompt.user
    assert "Hindi (Devanagari)" in prompt.user


def test_parse_model_response_structured_format():
    from app.rag.citations import parse_model_response
    raw = (
        "ANSWER: A normal cycle lasts 21 to 35 days [S1].\n"
        "INSUFFICIENT_EVIDENCE: false\n"
        "SOURCE_IDS: S1"
    )
    parsed = parse_model_response(raw)
    assert parsed.answer == "A normal cycle lasts 21 to 35 days [S1]."
    assert parsed.insufficient_evidence is False
    assert parsed.source_ids == ["S1"]


def test_parse_model_response_insufficient_evidence():
    from app.rag.citations import parse_model_response
    raw = (
        "ANSWER: The provided context does not cover scooter repairs.\n"
        "INSUFFICIENT_EVIDENCE: true\n"
        "SOURCE_IDS: none"
    )
    parsed = parse_model_response(raw)
    assert parsed.insufficient_evidence is True


def test_text_overlap_and_retriever_deduplication():
    from app.rag.retriever import _text_overlap, _filter_and_prune
    t1 = "A normal menstrual cycle length is typically 28 days but can range from 21 to 35 days."
    t2 = "A normal menstrual cycle is typically 28 days and ranges from 21 to 35 days."
    t3 = "Endometriosis is a condition where endometrial tissue grows outside the uterus."

    assert _text_overlap(t1, t2) > 0.60
    assert _text_overlap(t1, t3) < 0.20

    c1 = _chunk(1, "https://who.int/1", t1)
    c2 = _chunk(2, "https://who.int/2", t2)
    c3 = _chunk(3, "https://who.int/3", t3)

    kept = _filter_and_prune([c1, c2, c3], limit=4, dropoff_threshold=0.06, token_budget=1000)
    # c2 is a duplicate of c1 and should be pruned
    assert len(kept) == 2
    assert kept[0].payload.chunk_id == "src-1::000"
    assert kept[1].payload.chunk_id == "src-3::000"

