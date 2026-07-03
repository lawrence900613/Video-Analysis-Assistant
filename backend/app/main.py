"""FastAPI entry point: parse, download, AI summary, and subtitle translation."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from . import ai, downloader
from .config import get_settings
from . import download_jobs
from . import summarize_service
from .routes import chat_sse, mindmap
from .downloader import normalize_url

settings = get_settings()

app = FastAPI(title="Video Analysis Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mindmap.router)
app.include_router(chat_sse.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Safety net: turn any uncaught error (e.g. response serialization) into a
    clean JSON message instead of a raw 500 stack trace leaking to the client."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unexpected server error: {_clean_err(exc)}"},
    )


# --------------------------------------------------------------------------
# Request models
# --------------------------------------------------------------------------

class UrlBody(BaseModel):
    url: str


class SummaryBody(BaseModel):
    url: str
    output_lang: str = "English"


class DownloadBody(BaseModel):
    url: str
    format_id: str


class TranslateBody(BaseModel):
    url: str
    target_lang: str = "English"
    prefer_lang: Optional[str] = None


class SubtitlesBody(BaseModel):
    url: str
    prefer_lang: Optional[str] = None


class SummarizeBody(BaseModel):
    url: str
    prefer_lang: Optional[str] = None
    output_lang: str = "English"
    force_refresh: bool = False


class TranscriptBody(BaseModel):
    url: str
    prefer_lang: Optional[str] = None


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ffmpeg": downloader.has_ffmpeg(),
        "llm_ready": settings.llm_ready,
        "whisper_ready": False,
        "analysis_features": ["summarize_sse", "transcript", "mindmap", "chat"],
    }


@app.post("/api/parse")
def api_parse(body: UrlBody):
    url = normalize_url(body.url.strip())
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    try:
        return downloader.parse(url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Parse failed: {_clean_err(e)}")


@app.post("/api/download/start")
def api_download_start(body: DownloadBody):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    job_id = download_jobs.start_download(url, body.format_id)
    return {"job_id": job_id}


@app.get("/api/download/{job_id}/progress")
def api_download_progress(job_id: str):
    job = download_jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found")
    return job.snapshot()


@app.post("/api/download/{job_id}/cancel")
def api_download_cancel(job_id: str):
    result = download_jobs.cancel_job(job_id)
    status = result["status"]
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Download job not found")
    if status == "already_finished":
        raise HTTPException(
            status_code=409,
            detail=f"Download already finished ({result.get('stage')})",
        )
    return result


@app.get("/api/download/{job_id}/file")
def api_download_file(job_id: str):
    job = download_jobs.take_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found")
    if job.stage == "cancelled":
        raise HTTPException(status_code=410, detail="Download was cancelled")
    if job.stage == "error":
        raise HTTPException(status_code=422, detail=job.error or "Download failed")
    if job.stage != "ready" or not job.filepath:
        raise HTTPException(status_code=409, detail="Download not ready yet")

    filepath = job.filepath

    def _cleanup():
        try:
            folder = filepath.parent
            for p in folder.iterdir():
                p.unlink(missing_ok=True)
            folder.rmdir()
        except Exception:
            pass

    return FileResponse(
        path=filepath,
        media_type="application/octet-stream",
        headers={"Content-Disposition": _content_disposition(filepath.name)},
        background=BackgroundTask(_cleanup),
    )


@app.post("/api/download")
def api_download(body: DownloadBody):
    """Legacy single-request download (blocks until complete)."""
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    try:
        filepath = downloader.download(url, body.format_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Download failed: {_clean_err(e)}")

    def _cleanup():
        try:
            folder = filepath.parent
            for p in folder.iterdir():
                p.unlink(missing_ok=True)
            folder.rmdir()
        except Exception:
            pass

    return FileResponse(
        path=filepath,
        media_type="application/octet-stream",
        headers={"Content-Disposition": _content_disposition(filepath.name)},
        background=BackgroundTask(_cleanup),
    )


def _content_disposition(filename: str) -> str:
    """Build a robust Content-Disposition header.

    Emits both an ASCII fallback (`filename=`) and a UTF-8 encoded name
    (`filename*=`) so non-ASCII titles keep their correct extension across
    browsers, instead of being saved as .txt.
    """
    # ASCII fallback: drop non-ASCII chars but keep the extension.
    ascii_name = filename.encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_name or ascii_name.startswith("."):
        ext = Path(filename).suffix or ".bin"
        ascii_name = f"video{ext}"
    ascii_name = ascii_name.replace('"', "")
    return f"attachment; filename=\"{ascii_name}\"; filename*=utf-8''{quote(filename)}"


@app.post("/api/summary")
def api_summary(body: SummaryBody):
    """Deprecated: use POST /api/summarize (SSE). Kept for backward compatibility."""
    if not settings.llm_ready:
        raise HTTPException(status_code=503, detail="LLM API key not configured; AI summary unavailable")
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    try:
        result = summarize_service.summarize_sync(url, body.output_lang)
    except ValueError as e:
        code_msg = str(e)
        if ":" in code_msg:
            _, detail = code_msg.split(":", 1)
        else:
            detail = code_msg
        raise HTTPException(status_code=422, detail=detail)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI summary failed: {_clean_err(e)}")

    return {
        "title": result["title"],
        "lang": result["lang"],
        "is_auto": result["is_auto"],
        "summary": result["summary_md"],
        "deprecated": True,
    }


@app.post("/api/summarize")
async def api_summarize(body: SummarizeBody, request: Request):
    """SSE stream: transcript + streaming summary."""
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    if not settings.llm_ready:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured; AI summary unavailable",
        )

    async def event_generator():
        async for event in summarize_service.stream_summarize(
            url,
            body.prefer_lang,
            body.output_lang,
            request,
        ):
            yield event.encode("utf-8")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/transcript")
def api_transcript(body: TranscriptBody):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    try:
        transcript, info = summarize_service.fetch_transcript_for_url(url, body.prefer_lang)
    except ValueError as e:
        code_msg = str(e)
        detail = code_msg.split(":", 1)[-1] if ":" in code_msg else code_msg
        if code_msg.startswith("bilibili_login_required:") or code_msg.startswith("login_required:"):
            raise HTTPException(status_code=401, detail=detail) from e
        raise HTTPException(status_code=422, detail=detail)
    except RuntimeError as e:
        code_msg = str(e)
        if code_msg.startswith("rate_limited:"):
            raise HTTPException(status_code=429, detail=code_msg.split(":", 1)[-1])
        raise HTTPException(status_code=422, detail=f"Failed to fetch transcript: {_clean_err(e)}")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to fetch transcript: {_clean_err(e)}")

    return {
        "title": info["title"],
        "lang": transcript["lang"],
        "is_auto": transcript["is_auto"],
        "duration": info.get("duration"),
        "cues": transcript["cues"],
        "plain_text": transcript["plain_text"],
        "truncated": transcript["truncated"],
        "source": transcript["source"],
    }


@app.post("/api/translate")
def api_translate(body: TranslateBody):
    if not settings.llm_ready:
        raise HTTPException(status_code=503, detail="LLM API key not configured; subtitle translation unavailable")
    url = body.url.strip()
    try:
        prefer = [body.prefer_lang] if body.prefer_lang else None
        sub = downloader.fetch_subtitle(url, prefer)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to fetch subtitles: {_clean_err(e)}")

    if not sub["cues"]:
        raise HTTPException(status_code=422, detail="Subtitle content is empty; cannot translate")

    try:
        translated = ai.translate_cues(sub["cues"], body.target_lang)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI translation failed: {_clean_err(e)}")

    srt = downloader.cues_to_srt(translated)
    return PlainTextResponse(
        content=srt,
        media_type="application/x-subrip",
        headers={"Content-Disposition": 'attachment; filename="subtitle.srt"'},
    )


@app.post("/api/subtitles")
def api_subtitles(body: SubtitlesBody):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a video URL")
    try:
        prefer = [body.prefer_lang] if body.prefer_lang else None
        sub = downloader.fetch_subtitle(url, prefer)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to fetch subtitles: {_clean_err(e)}")

    if not sub["cues"]:
        raise HTTPException(status_code=422, detail="Subtitle content is empty; cannot export")

    srt = downloader.cues_to_srt(sub["cues"])
    lang = sub["lang"] or "unknown"
    return PlainTextResponse(
        content=srt,
        media_type="application/x-subrip",
        headers={
            "Content-Disposition": f'attachment; filename="subtitle_{lang}.srt"',
            "X-Subtitle-Lang": lang,
            "X-Subtitle-Auto": "1" if sub["is_auto"] else "0",
        },
    )


def _clean_err(e: Exception) -> str:
    msg = str(e)
    # Strip ANSI color codes and yt-dlp noise
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)
    msg = re.sub(r"^ERROR:\s*", "", msg, flags=re.IGNORECASE).strip()
    if "429" in msg or "too many requests" in msg.lower():
        return (
            "YouTube subtitle service is temporarily rate-limited (HTTP 429). "
            "Please wait a minute and try again."
        )
    return msg[:300] if msg else e.__class__.__name__


# --------------------------------------------------------------------------
# Frontend static hosting (production: frontend/dist)
# --------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="static")


def main():
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=bool(os.getenv("RELOAD")))


if __name__ == "__main__":
    main()
