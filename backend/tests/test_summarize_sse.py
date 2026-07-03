"""SSE summarize endpoint integration tests."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MOCK_TRANSCRIPT = {
    "title": "Test Video",
    "url": "https://example.com/watch?v=abc",
    "lang": "en",
    "is_auto": False,
    "duration_sec": 120.0,
    "source": "subtitle",
    "cues": [
        {
            "index": 0,
            "start": "00:00:01,000",
            "end": "00:00:04,000",
            "start_sec": 1.0,
            "end_sec": 4.0,
            "text": "Hello world",
        }
    ],
    "plain_text": "Hello world",
    "char_count": 11,
    "truncated": False,
}

MOCK_INFO = {"title": "Test Video", "duration": 120}

MULTI_CUE_TRANSCRIPT = {
    **MOCK_TRANSCRIPT,
    "duration_sec": 600.0,
    "cues": [
        {
            "index": 0,
            "start": "00:00:00,000",
            "end": "00:00:05,000",
            "start_sec": 0.0,
            "end_sec": 5.0,
            "text": "Opening context",
        },
        {
            "index": 1,
            "start": "00:02:00,000",
            "end": "00:02:05,000",
            "start_sec": 120.0,
            "end_sec": 125.0,
            "text": "First topic details",
        },
        {
            "index": 2,
            "start": "00:05:00,000",
            "end": "00:05:05,000",
            "start_sec": 300.0,
            "end_sec": 305.0,
            "text": "Closing remarks",
        },
    ],
    "plain_text": "Opening context. First topic details. Closing remarks.",
}


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event = "message"
        data_lines = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            events.append((event, json.loads("\n".join(data_lines))))
    return events


def test_summarize_empty_url_returns_400():
    res = client.post("/api/summarize", json={"url": "  "})
    assert res.status_code == 400


@patch("app.main.settings")
@patch("app.summarize_service.fetch_transcript_for_url")
@patch("app.ai.summarize_stream_markdown")
def test_summarize_sse_happy_path(mock_stream, mock_fetch, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.return_value = (MOCK_TRANSCRIPT, MOCK_INFO)
    mock_stream.return_value = iter(["# TL;DR\n", "Short summary\n"])

    with patch("app.summarize_service.markdown_to_structured_summary") as mock_parse:
        mock_parse.return_value = {
            "tldr": "Short summary",
            "key_points": ["point"],
            "chapters": [],
            "output_lang": "English",
        }
        res = client.post(
            "/api/summarize",
            json={"url": "https://example.com/watch?v=abc", "output_lang": "English"},
        )

    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    events = _parse_sse(res.text)
    names = [e[0] for e in events]
    assert names[0] == "stage"
    assert "transcript" in names
    assert "summary_delta" in names
    assert "summary" in names
    assert names[-1] == "done"


@patch("app.main.settings")
@patch("app.summarize_service.fetch_transcript_for_url")
@patch("app.ai.summarize_stream_markdown")
def test_summarize_repeated_zero_labels_are_realigned(mock_stream, mock_fetch, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.return_value = (MULTI_CUE_TRANSCRIPT, {"title": "Test Video", "duration": 600})
    mock_stream.return_value = iter([
        "# TL;DR\nSummary\n\n",
        "## [00:00] Opening\nOpening context\n\n",
        "## [00:00] First topic\nFirst topic details\n\n",
        "## [00:00] Closing\nClosing remarks\n",
    ])

    res = client.post(
        "/api/summarize",
        json={"url": "https://example.com/watch?v=abc", "output_lang": "English"},
    )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    summary_events = [d for e, d in events if e == "summary"]
    assert summary_events
    starts = [ch["start_sec"] for ch in summary_events[0]["chapters"]]
    assert len(set(starts)) == 3
    assert starts == sorted(starts)
    assert starts != [0.0, 0.0, 0.0]


@patch("app.main.settings")
@patch("app.summarize_service.fetch_transcript_for_url")
def test_summarize_sse_no_subtitles(mock_fetch, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.side_effect = ValueError(
        "no_subtitles:No subtitles available for this video."
    )

    res = client.post(
        "/api/summarize",
        json={"url": "https://example.com/watch?v=abc"},
    )
    events = _parse_sse(res.text)
    error_events = [d for e, d in events if e == "error"]
    assert error_events
    assert error_events[0]["code"] == "no_subtitles"


def test_parse_markdown_to_summary():
    from app import ai

    md = (
        "# TL;DR\nOne line overview\n\n"
        "## Key Points\n- First point\n- Second point\n\n"
        "## [01:30] Intro\nOpening section summary\n"
    )
    result = ai.parse_markdown_to_summary(md)
    assert result["tldr"] == "One line overview"
    assert len(result["key_points"]) == 2
    assert result["chapters"][0]["start_label"] == "01:30"
