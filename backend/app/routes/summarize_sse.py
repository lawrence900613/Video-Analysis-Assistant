"""POST /api/summarize — SSE streaming endpoint (v2 additive, optional router)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import get_settings
from ..summarize_service import stream_summarize

router = APIRouter()
settings = get_settings()


class SummarizeBody(BaseModel):
    url: str
    prefer_lang: Optional[str] = None
    output_lang: str = "English"
    force_refresh: bool = False


@router.post("/api/summarize")
async def api_summarize_sse(body: SummarizeBody, request: Request):
    """Stream transcript + summary via Server-Sent Events."""
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    if not settings.llm_ready:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured; AI summary unavailable",
        )

    async def event_generator():
        async for chunk in stream_summarize(
            url,
            prefer_lang=body.prefer_lang,
            output_lang=body.output_lang,
            request=request,
        ):
            yield chunk.encode("utf-8")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
