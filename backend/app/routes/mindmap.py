"""POST /api/mindmap — LLM mind map generation."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_settings
from .. import mindmap_service

router = APIRouter()
settings = get_settings()


class MindmapBody(BaseModel):
    url: str
    prefer_lang: Optional[str] = None
    output_lang: str = "English"
    summary: Optional[dict[str, Any]] = None
    transcript: Optional[dict[str, Any]] = None


@router.post("/api/mindmap")
def api_mindmap(body: MindmapBody):
    if not settings.llm_ready:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured; mind map unavailable",
        )
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")

    try:
        return mindmap_service.generate_mindmap(
            url,
            output_lang=body.output_lang,
            prefer_lang=body.prefer_lang,
            summary=body.summary,
            transcript=body.transcript,
        )
    except ValueError as e:
        detail = str(e).split(":", 1)[-1] if ":" in str(e) else str(e)
        raise HTTPException(status_code=422, detail=detail) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Mind map generation failed: {e}") from e
