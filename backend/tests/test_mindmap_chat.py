"""Tests for Phase 2 mindmap and chat endpoints."""
from __future__ import annotations

import json
from unittest.mock import patch

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
            "text": "Hello world about testing",
        },
        {
            "index": 1,
            "start": "00:03:24,000",
            "end": "00:03:28,000",
            "start_sec": 204.0,
            "end_sec": 208.0,
            "text": "Important detail here",
        },
    ],
    "plain_text": "Hello world about testing. Important detail here.",
    "char_count": 45,
    "truncated": False,
}

MOCK_SUMMARY = {
    "tldr": "A test video",
    "key_points": ["Testing"],
    "chapters": [],
}

MOCK_MINDMAP = {
    "root": {
        "id": "root",
        "label": "Test Video",
        "type": "root",
        "children": [
            {
                "id": "c1",
                "label": "Intro",
                "type": "chapter",
                "start_sec": 1,
                "children": [{"id": "p1", "label": "Hello", "type": "point", "children": []}],
            }
        ],
    }
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


@patch("app.routes.mindmap.settings")
@patch("app.mindmap_service.ai.generate_mindmap_llm")
@patch("app.mindmap_service.fetch_transcript_for_url")
def test_mindmap_happy_path(mock_fetch, mock_llm, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.return_value = (MOCK_TRANSCRIPT, {"title": "Test Video"})
    mock_llm.return_value = MOCK_MINDMAP

    res = client.post(
        "/api/mindmap",
        json={
            "url": "https://example.com/watch?v=abc",
            "output_lang": "English",
            "summary": MOCK_SUMMARY,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["mindmap"]["root"]["label"] == "Test Video"
    assert "markdown" in data
    assert "# Test Video" in data["markdown"]


@patch("app.routes.mindmap.settings")
def test_mindmap_no_llm(mock_settings):
    mock_settings.llm_ready = False
    res = client.post("/api/mindmap", json={"url": "https://example.com"})
    assert res.status_code == 503


@patch("app.routes.chat_sse.settings")
@patch("app.chat_service.ai.answer_question_stream")
@patch("app.chat_service.fetch_transcript_for_url")
def test_chat_sse_happy_path(mock_fetch, mock_stream, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.return_value = (MOCK_TRANSCRIPT, {"title": "Test Video"})
    mock_stream.return_value = iter(["The author mentions testing at ", "[03:24]."])

    res = client.post(
        "/api/chat",
        json={
            "url": "https://example.com/watch?v=abc",
            "output_lang": "English",
            "messages": [{"role": "user", "content": "When is testing mentioned?"}],
        },
    )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    names = [e[0] for e in events]
    assert "stage" in names
    assert "answer_delta" in names
    assert "answer" in names
    assert names[-1] == "done"

    answer_events = [d for e, d in events if e == "answer"]
    assert answer_events
    assert answer_events[0]["citations"]


@patch("app.routes.chat_sse.settings")
@patch("app.chat_service.ai.answer_question_stream")
@patch("app.chat_service.fetch_transcript_for_url")
def test_chat_zero_timestamp_falls_back_to_relevant_cue(mock_fetch, mock_stream, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.return_value = (MOCK_TRANSCRIPT, {"title": "Test Video"})
    mock_stream.return_value = iter(["The important detail is discussed at [00:00]."])

    res = client.post(
        "/api/chat",
        json={
            "url": "https://example.com/watch?v=abc",
            "output_lang": "English",
            "messages": [{"role": "user", "content": "What is the important detail?"}],
        },
    )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    answer_events = [d for e, d in events if e == "answer"]
    assert answer_events
    assert answer_events[0]["citations"][0]["cue_index"] == 1
    assert answer_events[0]["citations"][0]["start_sec"] == 204.0


@patch("app.routes.chat_sse.settings")
@patch("app.chat_service.ai.answer_question_stream")
@patch("app.chat_service.fetch_transcript_for_url")
def test_chat_repeated_zero_timestamps_are_realigned(mock_fetch, mock_stream, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.return_value = (MOCK_TRANSCRIPT, {"title": "Test Video"})
    mock_stream.return_value = iter([
        "Testing starts at [00:00], but the important detail is at [00:00]."
    ])

    res = client.post(
        "/api/chat",
        json={
            "url": "https://example.com/watch?v=abc",
            "output_lang": "English",
            "messages": [{"role": "user", "content": "Where is the important detail?"}],
        },
    )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    answer_events = [d for e, d in events if e == "answer"]
    assert answer_events
    assert answer_events[0]["citations"][0]["cue_index"] == 1
    assert answer_events[0]["citations"][0]["start_sec"] == 204.0


@patch("app.routes.chat_sse.settings")
@patch("app.chat_service.ai.answer_question_stream")
@patch("app.chat_service.fetch_transcript_for_url")
def test_chat_mixed_repeated_zero_timestamps_are_realigned(mock_fetch, mock_stream, mock_settings):
    mock_settings.llm_ready = True
    mock_fetch.return_value = (MOCK_TRANSCRIPT, {"title": "Test Video"})
    mock_stream.return_value = iter([
        "The model repeats [00:00], then cites [03:24], and repeats [00:00] again."
    ])

    res = client.post(
        "/api/chat",
        json={
            "url": "https://example.com/watch?v=abc",
            "output_lang": "English",
            "messages": [{"role": "user", "content": "Where is the important detail?"}],
        },
    )

    assert res.status_code == 200
    events = _parse_sse(res.text)
    answer_events = [d for e, d in events if e == "answer"]
    assert answer_events
    starts = [cite["start_sec"] for cite in answer_events[0]["citations"]]
    assert starts == sorted(set(starts))
    assert starts != [1.0]
    assert 204.0 in starts


def test_retrieve_chunks():
    from app.transcript_utils import retrieve_chunks

    chunks = retrieve_chunks(MOCK_TRANSCRIPT["cues"], "important detail", top_k=2)
    assert chunks
    assert "Important" in chunks[0].text


def test_extract_citations():
    from app.ai import extract_citations_from_answer

    answer = "See [03:24] for the key point."
    citations = extract_citations_from_answer(answer, MOCK_TRANSCRIPT["cues"])
    assert len(citations) == 1
    assert citations[0]["cue_index"] == 1
