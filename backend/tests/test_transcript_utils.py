"""Unit tests for transcript_utils."""
from app import transcript_utils as tu


def _cue(start: str, end: str, text: str) -> dict:
    return {"start": start, "end": end, "text": text}


def test_ts_to_sec():
    assert tu.ts_to_sec("00:00:01,000") == 1.0
    assert tu.ts_to_sec("00:01:02,500") == 62.5
    assert tu.ts_to_sec("01:02:03,000") == 3723.0
    assert tu.ts_to_sec("00:01:02") == 62.0


def test_enrich_cues():
    cues = [_cue("00:00:01,000", "00:00:04,000", "Hello")]
    enriched = tu.enrich_cues(cues)
    assert enriched[0]["index"] == 0
    assert enriched[0]["start_sec"] == 1.0
    assert enriched[0]["end_sec"] == 4.0


def test_chunk_transcript_empty():
    assert tu.chunk_transcript([]) == []


def test_chunk_transcript_splits():
    cues = [
        _cue("00:00:00,000", "00:00:01,000", "A" * 100)
        for _ in range(20)
    ]
    enriched = tu.enrich_cues(cues)
    chunks = tu.chunk_transcript(enriched, max_chars=500, overlap_cues=1)
    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text


def test_format_and_chunk_transcript_with_timestamps():
    cues = tu.enrich_cues([
        _cue("00:00:03,000", "00:00:05,000", "Intro"),
        _cue("00:02:00,000", "00:02:05,000", "Main"),
    ])
    text = tu.format_cues_with_timestamps(cues)
    assert "[0:03] Intro" in text
    assert "[2:00] Main" in text

    chunks = tu.chunk_transcript(cues, max_chars=100, include_timestamps=True)
    assert chunks
    assert "[0:03] Intro" in chunks[0].text


def test_align_chapter_times():
    cues = tu.enrich_cues([
        _cue("00:00:00,000", "00:00:10,000", "Intro"),
        _cue("00:03:24,000", "00:03:30,000", "Main topic"),
        _cue("00:10:00,000", "00:10:05,000", "Outro"),
    ])
    chapters = [
        {"title": "Intro", "summary": "Opening", "start_label": "0:00"},
        {"title": "Core", "summary": "Main", "start_label": "3:24"},
    ]
    aligned = tu.align_chapter_times(cues, chapters, duration_sec=600)
    assert len(aligned) == 2
    assert aligned[0]["start_label"] == "0:00"
    assert aligned[1]["start_sec"] == 204.0


def test_align_chapter_times_duplicate_labels():
    """Duplicate LLM labels (all 0:03) must not collapse every chapter to the same cue."""
    cues = tu.enrich_cues([
        _cue("00:00:03,000", "00:00:08,000", "Welcome everyone"),
        _cue("00:02:00,000", "00:02:05,000", "First main topic here"),
        _cue("00:05:00,000", "00:05:05,000", "Second section content"),
        _cue("00:08:00,000", "00:08:05,000", "Third part of talk"),
        _cue("00:11:00,000", "00:11:05,000", "Fourth segment begins"),
        _cue("00:14:00,000", "00:14:05,000", "Closing remarks today"),
    ])
    chapters = [
        {"title": "Welcome", "summary": "Opening welcome", "start_label": "0:03"},
        {"title": "First Topic", "summary": "First main topic", "start_label": "0:03"},
        {"title": "Second Section", "summary": "Second section", "start_label": "0:03"},
        {"title": "Third Part", "summary": "Third part", "start_label": "0:03"},
        {"title": "Fourth Segment", "summary": "Fourth segment", "start_label": "0:03"},
        {"title": "Closing", "summary": "Closing remarks", "start_label": "0:03"},
    ]
    aligned = tu.align_chapter_times(cues, chapters, duration_sec=900)
    starts = [ch["start_sec"] for ch in aligned]
    assert len(set(starts)) == len(starts), "each chapter needs a distinct start time"
    assert starts == sorted(starts), "chapter times must increase monotonically"


def test_align_chapter_times_no_labels():
    """Chapters without timestamps should spread across the transcript."""
    cues = tu.enrich_cues([
        _cue("00:00:00,000", "00:00:05,000", "A"),
        _cue("00:03:00,000", "00:03:05,000", "B"),
        _cue("00:06:00,000", "00:06:05,000", "C"),
    ])
    chapters = [
        {"title": "Part 1", "summary": "First"},
        {"title": "Part 2", "summary": "Second"},
        {"title": "Part 3", "summary": "Third"},
    ]
    aligned = tu.align_chapter_times(cues, chapters, duration_sec=360)
    starts = [ch["start_sec"] for ch in aligned]
    assert len(set(starts)) == 3
    assert starts[0] < starts[1] < starts[2]
