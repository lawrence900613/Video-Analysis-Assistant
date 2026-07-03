"""SSE summarize orchestration (v2 additive path)."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Callable, Optional

from fastapi import Request

from . import ai, downloader
from .config import get_settings
from .transcript_utils import (
    align_chapter_times,
    build_transcript,
    chunk_transcript,
    format_cues_with_timestamps,
)

settings = get_settings()

ShouldCancel = Callable[[], bool]


def format_sse_event(event: str, data: dict) -> str:
    """Format one Server-Sent Event block."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def markdown_to_structured_summary(
    title: str,
    transcript: str,
    markdown: str,
    output_lang: str,
) -> dict:
    """Parse streamed Markdown; fallback to non-streaming structured summary."""
    from datetime import datetime, timezone

    try:
        summary = ai.parse_markdown_to_summary(markdown)
    except ValueError:
        summary = ai.summarize_structured(title, transcript, output_lang)
    summary["output_lang"] = output_lang
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    return summary


def _max_duration() -> int:
    return settings.max_analysis_duration_sec or 2 * 3600


def fetch_transcript_for_url(url: str, prefer_lang: Optional[str] = None) -> tuple[dict, dict]:
    """Fetch subtitles and return (Transcript dict, parse info)."""
    url = downloader.normalize_url(url.strip())
    raw_info = downloader.extract_info(url, probe_subtitles=True)
    info = downloader.format_parse_result(raw_info, url)
    duration = info.get("duration")

    if duration and duration > _max_duration():
        raise ValueError(
            f"duration_exceeded:Video exceeds the 2-hour analysis limit ({int(duration // 60)} min). "
            "Analysis is not available for videos longer than 2 hours."
        )

    prefer = [prefer_lang] if prefer_lang else None
    try:
        sub = downloader.fetch_subtitle(url, prefer, info=raw_info)
    except downloader.SubtitleRateLimitError as e:
        raise RuntimeError(f"rate_limited:{e}") from e
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to fetch subtitles: {e}") from e

    if not sub["cues"]:
        raise ValueError(
            "no_subtitles:No subtitles available for this video. AI understanding requires subtitles."
        )

    transcript = build_transcript(
        title=info["title"],
        url=url,
        lang=sub["lang"],
        is_auto=sub["is_auto"],
        cues=sub["cues"],
        plain_text=sub["plain_text"],
        duration_sec=duration,
        source="subtitle",
        max_chars=settings.max_subtitle_chars,
    )
    return transcript, info


def summarize_sync(
    url: str,
    output_lang: str = "English",
    prefer_lang: Optional[str] = None,
) -> dict:
    """Non-streaming summary for /api/summary compatibility."""
    transcript, info = fetch_transcript_for_url(url, prefer_lang)
    plain = transcript["plain_text"]
    if not plain.strip():
        raise ValueError("subtitle_empty:Subtitle content is empty; cannot summarize")

    title = info["title"]
    cues = transcript["cues"]
    duration = info.get("duration")
    timestamped_plain = format_cues_with_timestamps(cues)

    needs_chunk = len(plain) > settings.max_subtitle_chars or (
        duration and duration > 20 * 60
    )

    if needs_chunk:
        chunks = chunk_transcript(cues, max_chars=settings.chunk_max_chars, include_timestamps=True)
        partials = [
            ai.map_summarize_chunk(title, chunk.text, i, len(chunks), output_lang)
            for i, chunk in enumerate(chunks)
        ]
        structured = ai.reduce_summaries(title, partials, output_lang)
    else:
        structured = ai.summarize_structured(title, timestamped_plain, output_lang, cues)

    if structured.get("chapters"):
        structured["chapters"] = align_chapter_times(cues, structured["chapters"], duration)

    return {
        "title": info["title"],
        "lang": transcript["lang"],
        "is_auto": transcript["is_auto"],
        "summary_md": ai.structured_to_markdown(structured),
    }


def _error_event(code: str, message: str) -> str:
    return format_sse_event("error", {"code": code, "message": message})


def _classify_fetch_error(msg: str) -> tuple[str, str]:
    if "duration_exceeded" in msg:
        return "duration_exceeded", msg.split(":", 1)[-1]
    if "bilibili_login_required" in msg or "login_required" in msg:
        return "login_required", msg.split(":", 1)[-1]
    if "no_subtitles" in msg:
        return "no_subtitles", msg.split(":", 1)[-1]
    if "rate_limited" in msg:
        return "rate_limited", msg.split(":", 1)[-1]
    return "parse_failed", msg.split(":", 1)[-1] if ":" in msg else msg


async def stream_summarize(
    url: str,
    prefer_lang: Optional[str] = None,
    output_lang: str = "English",
    request: Optional[Request] = None,
    should_cancel: Optional[ShouldCancel] = None,
) -> AsyncIterator[str]:
    """Yield SSE-formatted strings for POST /api/summarize."""

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
        if cancel_state["cancelled"]:
            return True
        if should_cancel and should_cancel():
            return True
        return False

    try:
        url = url.strip()
        if not url:
            yield _error_event("invalid_url", "Please enter a video URL")
            return

        yield format_sse_event("stage", {"name": "fetching_transcript"})

        try:
            transcript, info = await asyncio.to_thread(
                fetch_transcript_for_url, url, prefer_lang
            )
        except ValueError as e:
            code, message = _classify_fetch_error(str(e))
            yield _error_event(code, message)
            return
        except RuntimeError as e:
            code, message = _classify_fetch_error(str(e))
            yield _error_event(code, message)
            return
        except Exception as e:  # noqa: BLE001
            yield _error_event("parse_failed", f"Failed to fetch subtitles: {e}")
            return

        if _cancelled():
            return

        if not transcript["plain_text"].strip():
            yield _error_event("subtitle_empty", "Subtitle content is empty; cannot summarize")
            return

        yield format_sse_event("transcript", transcript)

        title = info["title"]
        plain = transcript["plain_text"]
        cues = transcript["cues"]
        duration = info.get("duration")
        timestamped_plain = format_cues_with_timestamps(cues)

        needs_chunk = len(plain) > settings.max_subtitle_chars or (
            duration and duration > 20 * 60
        )

        markdown_parts: list[str] = []

        try:
            if needs_chunk:
                yield format_sse_event("stage", {"name": "chunking"})
                chunks = chunk_transcript(cues, max_chars=settings.chunk_max_chars, include_timestamps=True)
                chunk_total = len(chunks)
                yield format_sse_event(
                    "stage", {"name": "chunking", "chunk_total": chunk_total}
                )

                partials = []
                for i, chunk in enumerate(chunks):
                    if _cancelled():
                        return
                    yield format_sse_event(
                        "stage",
                        {"name": "map", "chunk_current": i + 1, "chunk_total": chunk_total},
                    )
                    partial = await asyncio.to_thread(
                        ai.map_summarize_chunk,
                        title,
                        chunk.text,
                        i,
                        chunk_total,
                        output_lang,
                    )
                    partials.append(partial)

                if _cancelled():
                    return

                yield format_sse_event("stage", {"name": "reducing"})
                stream_iter = ai.reduce_summaries_stream(title, partials, output_lang)
            else:
                yield format_sse_event("stage", {"name": "summarizing"})
                stream_iter = ai.summarize_stream_markdown(title, timestamped_plain, output_lang)

            for delta in stream_iter:
                if _cancelled():
                    return
                markdown_parts.append(delta)
                yield format_sse_event("summary_delta", {"text": delta})
                # Yield control so SSE chunks flush before the next LLM token.
                await asyncio.sleep(0)

        except Exception as e:  # noqa: BLE001
            yield _error_event("llm_failed", f"AI summary failed: {e}")
            return

        if _cancelled():
            return

        full_markdown = "".join(markdown_parts)
        try:
            summary = markdown_to_structured_summary(title, timestamped_plain, full_markdown, output_lang)
            if summary.get("chapters"):
                summary["chapters"] = align_chapter_times(
                    cues, summary["chapters"], duration
                )
            summary["output_lang"] = output_lang
            yield format_sse_event("summary", summary)
        except Exception as e:  # noqa: BLE001
            yield _error_event("llm_failed", f"Failed to parse summary: {e}")
            return

        yield format_sse_event("done", {"ok": True})
    finally:
        if watch_task:
            watch_task.cancel()
