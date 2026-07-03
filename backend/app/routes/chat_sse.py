"""POST /api/chat — SSE streaming Q&A."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import get_settings
from .. import chat_service

router = APIRouter()
settings = get_settings()


class ChatMessageBody(BaseModel):
    role: str
    content: str


class ChatBody(BaseModel):
    url: str
    prefer_lang: Optional[str] = None
    output_lang: str = "English"
    messages: list[ChatMessageBody]
    transcript: Optional[dict[str, Any]] = None
    summary: Optional[dict[str, Any]] = None


@router.post("/api/chat")
async def api_chat(body: ChatBody, request: Request):
    if not settings.llm_ready:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured; AI chat unavailable",
        )
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    async def event_generator():
        async for chunk in chat_service.stream_chat(
            url,
            messages,
            output_lang=body.output_lang,
            prefer_lang=body.prefer_lang,
            transcript=body.transcript,
            summary=body.summary,
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
