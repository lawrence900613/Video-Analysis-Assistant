"""SSE chat Q&A service grounded in transcript (Phase 2)."""
from __future__ import annotations

import asyncio
import re
from typing import AsyncIterator, Optional

from fastapi import Request

from . import ai
from .config import get_settings
from .summarize_service import fetch_transcript_for_url, format_sse_event
from .transcript_utils import (
    TranscriptChunk,
    format_cues_with_timestamps,
    retrieve_chunks,
    select_relevant_cues,
    ts_to_sec,
)

settings = get_settings()


def _build_context(
    transcript: dict,
    summary: Optional[dict],
    question: str,
) -> tuple[str, list[TranscriptChunk]]:
    """Build LLM context: full transcript for short videos, retrieved chunks + TL;DR for long."""
    plain = transcript.get("plain_text") or ""
    cues = transcript.get("cues") or []
    title = transcript.get("title") or "Video"

    parts: list[str] = []
    if summary and summary.get("tldr"):
        parts.append(f"TL;DR: {summary['tldr']}")

    citation_chunks = retrieve_chunks(
        cues,
        question,
        top_k=5,
        chunk_max_chars=settings.chunk_max_chars,
    )

    if len(plain) <= settings.max_subtitle_chars:
        timestamped = format_cues_with_timestamps(cues)
        parts.append(f"Full transcript with timestamps:\n{timestamped}")
    else:
        if citation_chunks:
            chunk_text = "\n\n---\n\n".join(
                format_cues_with_timestamps(cues[c.cue_range[0] : c.cue_range[1] + 1])
                for c in citation_chunks
            )
            parts.append(f"Relevant transcript excerpts:\n{chunk_text}")
        else:
            parts.append(f"Transcript (truncated):\n{plain[:settings.max_subtitle_chars]}")

    return "\n\n".join(parts), citation_chunks


def _last_user_message(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return (msg.get("content") or "").strip()
    return ""


def _citation_labels(answer: str) -> list[float]:
    labels: list[float] = []
    for label in re.findall(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]", answer or ""):
        parts = label.split(":")
        try:
            if len(parts) == 2:
                labels.append(int(parts[0]) * 60 + int(parts[1]))
            else:
                labels.append(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
        except ValueError:
            continue
    return labels


def _has_untrusted_zero_labels(labels: list[float]) -> bool:
    """Treat repeated or exclusive near-zero LLM citations as hallucinated timestamps."""
    zeroish_count = sum(1 for label in labels if label <= 1)
    return bool(labels) and (zeroish_count == len(labels) or zeroish_count > 1)


def _cue_citations(cues: list[dict]) -> list[dict]:
    citations: list[dict] = []
    seen: set[int] = set()
    for i, cue in enumerate(cues):
        cue_index = cue.get("index", i)
        if cue_index in seen:
            continue
        seen.add(cue_index)
        start_sec = cue.get("start_sec", ts_to_sec(cue["start"]))
        citations.append({
            "start_sec": start_sec,
            "end_sec": cue.get("end_sec", start_sec + 5),
            "quote": cue.get("text", "")[:200],
            "cue_index": cue_index,
        })
    return citations


def _drop_zeroish_citations(citations: list[dict]) -> list[dict]:
    """Discard citations produced from hallucinated [00:00]-style labels."""
    return [
        citation
        for citation in citations
        if citation.get("start_sec", 0) > 1
    ]


def _ordered_distinct_citations(citations: list[dict]) -> list[dict]:
    """Keep one citation per cue and present them in transcript order."""
    distinct: dict[int, dict] = {}
    for citation in citations:
        cue_index = citation.get("cue_index")
        if cue_index is None:
            cue_index = len(distinct)
        if cue_index not in distinct:
            distinct[cue_index] = citation
    return sorted(
        distinct.values(),
        key=lambda citation: (
            citation.get("start_sec", 0),
            citation.get("cue_index", 0),
        ),
    )


async def stream_chat(
    url: str,
    messages: list[dict],
    output_lang: str = "English",
    prefer_lang: Optional[str] = None,
    transcript: Optional[dict] = None,
    summary: Optional[dict] = None,
    request: Optional[Request] = None,
) -> AsyncIterator[str]:
    """Yield SSE events for multi-turn Q&A."""
    cancel_state = {"cancelled": False}

    async def watch_disconnect() -> None:
        if not request:
            return
        while not cancel_state["cancelled"]:
            if await request.is_disconnected():
                cancel_state["cancelled"] = True
                return
            await asyncio.sleep(0.3)

    watch_task = asyncio.create_task(watch_disconnect()) if request else None

    def _cancelled() -> bool:
        return cancel_state["cancelled"]

    try:
        url = url.strip()
        if not url:
            yield format_sse_event("error", {"code": "invalid_url", "message": "Please enter a video URL"})
            return

        if not messages:
            yield format_sse_event("error", {"code": "invalid_request", "message": "messages cannot be empty"})
            return

        yield format_sse_event("stage", {"name": "retrieving"})

        try:
            if transcript is None:
                transcript, _info = await asyncio.to_thread(
                    fetch_transcript_for_url, url, prefer_lang
                )
        except ValueError as e:
            msg = str(e)
            code = msg.split(":", 1)[0] if ":" in msg else "parse_failed"
            detail = msg.split(":", 1)[-1] if ":" in msg else msg
            yield format_sse_event("error", {"code": code, "message": detail})
            return
        except Exception as e:  # noqa: BLE001
            yield format_sse_event("error", {"code": "parse_failed", "message": str(e)})
            return

        if _cancelled():
            return

        if not transcript.get("plain_text", "").strip():
            yield format_sse_event(
                "error",
                {"code": "subtitle_empty", "message": "Subtitle content is empty; cannot answer questions"},
            )
            return

        question = _last_user_message(messages)
        context, citation_chunks = _build_context(transcript, summary, question)
        title = transcript.get("title") or "Video"
        cues = transcript.get("cues") or []

        yield format_sse_event("stage", {"name": "answering"})

        answer_parts: list[str] = []
        try:
            stream_iter = ai.answer_question_stream(title, context, messages, output_lang)
            for delta in stream_iter:
                if _cancelled():
                    return
                answer_parts.append(delta)
                yield format_sse_event("answer_delta", {"text": delta})
                await asyncio.sleep(0)
        except Exception as e:  # noqa: BLE001
            yield format_sse_event("error", {"code": "llm_failed", "message": f"AI chat failed: {e}"})
            return

        if _cancelled():
            return

        full_answer = "".join(answer_parts)
        citations = ai.extract_citations_from_answer(full_answer, cues)
        labels = _citation_labels(full_answer)
        untrusted_zero_labels = _has_untrusted_zero_labels(labels)
        if untrusted_zero_labels:
            citations = _drop_zeroish_citations(citations)
        if not citations or untrusted_zero_labels:
            relevant_cues = select_relevant_cues(
                cues,
                f"{question}\n{full_answer}",
                top_k=3,
            )
            if untrusted_zero_labels:
                relevant_cues = [
                    cue
                    for cue in relevant_cues
                    if cue.get("start_sec", ts_to_sec(cue["start"])) > 1
                ]
            if not relevant_cues and citation_chunks:
                relevant_cues = [
                    cues[chunk.cue_range[0]]
                    for chunk in citation_chunks[:3]
                    if (
                        cues
                        and chunk.cue_range[0] < len(cues)
                        and (
                            not untrusted_zero_labels
                            or cues[chunk.cue_range[0]].get(
                                "start_sec",
                                ts_to_sec(cues[chunk.cue_range[0]]["start"]),
                            )
                            > 1
                        )
                    )
                ]
            fallback = _cue_citations(relevant_cues)
            if fallback:
                citations = citations + fallback
        citations = _ordered_distinct_citations(citations)
        yield format_sse_event(
            "answer",
            {"answer": full_answer, "citations": citations, "model": settings.llm_model},
        )
        yield format_sse_event("done", {"ok": True})
    finally:
        if watch_task:
            watch_task.cancel()
