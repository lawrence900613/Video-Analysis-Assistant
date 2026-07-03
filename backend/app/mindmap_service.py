"""Mind map generation service (Phase 2)."""
from __future__ import annotations

from typing import Optional

from . import ai
from .config import get_settings
from .summarize_service import fetch_transcript_for_url

settings = get_settings()


def generate_mindmap(
    url: str,
    output_lang: str = "English",
    prefer_lang: Optional[str] = None,
    summary: Optional[dict] = None,
    transcript: Optional[dict] = None,
) -> dict:
    """Generate LLM mind map from transcript + optional structured summary."""
    if transcript is None:
        transcript, info = fetch_transcript_for_url(url, prefer_lang)
    else:
        info = {"title": transcript.get("title") or "Video"}

    plain = transcript.get("plain_text") or ""
    if not plain.strip():
        raise ValueError("subtitle_empty:Subtitle content is empty; cannot generate mind map")

    title = transcript.get("title") or info.get("title") or "Video"
    mindmap = ai.generate_mindmap_llm(title, plain, summary, output_lang)
    markdown = ai.mindmap_tree_to_markdown(mindmap["root"])

    return {
        "mindmap": mindmap,
        "markdown": markdown,
        "model": settings.llm_model,
    }
