"""FastAPI 应用入口：解析 / 下载 / AI 总结 / 字幕翻译。"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from . import ai, downloader
from .config import get_settings

settings = get_settings()

app = FastAPI(title="万能视频下载", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# 请求模型
# --------------------------------------------------------------------------

class UrlBody(BaseModel):
    url: str


class DownloadBody(BaseModel):
    url: str
    format_id: str


class TranslateBody(BaseModel):
    url: str
    target_lang: str = "简体中文"


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ffmpeg": downloader.has_ffmpeg(),
        "llm_ready": settings.llm_ready,
    }


@app.post("/api/parse")
def api_parse(body: UrlBody):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="请输入视频链接")
    try:
        return downloader.parse(url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"解析失败：{_clean_err(e)}")


@app.post("/api/download")
def api_download(body: DownloadBody):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="请输入视频链接")
    try:
        filepath = downloader.download(url, body.format_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"下载失败：{_clean_err(e)}")

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
        filename=filepath.name,
        media_type="application/octet-stream",
        background=BackgroundTask(_cleanup),
    )


@app.post("/api/summary")
def api_summary(body: UrlBody):
    if not settings.llm_ready:
        raise HTTPException(status_code=503, detail="未配置大模型 API Key，无法使用 AI 总结")
    url = body.url.strip()
    try:
        sub = downloader.fetch_subtitle(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"获取字幕失败：{_clean_err(e)}")

    if not sub["plain_text"].strip():
        raise HTTPException(status_code=422, detail="字幕内容为空，无法总结")

    info = downloader.parse(url)
    try:
        summary = ai.summarize(info["title"], sub["plain_text"])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI 总结失败：{_clean_err(e)}")

    return {
        "title": info["title"],
        "lang": sub["lang"],
        "is_auto": sub["is_auto"],
        "summary": summary,
    }


@app.post("/api/translate")
def api_translate(body: TranslateBody):
    if not settings.llm_ready:
        raise HTTPException(status_code=503, detail="未配置大模型 API Key，无法使用字幕翻译")
    url = body.url.strip()
    try:
        sub = downloader.fetch_subtitle(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"获取字幕失败：{_clean_err(e)}")

    if not sub["cues"]:
        raise HTTPException(status_code=422, detail="字幕内容为空，无法翻译")

    try:
        translated = ai.translate_cues(sub["cues"], body.target_lang)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI 翻译失败：{_clean_err(e)}")

    srt = downloader.cues_to_srt(translated)
    return PlainTextResponse(
        content=srt,
        media_type="application/x-subrip",
        headers={"Content-Disposition": 'attachment; filename="subtitle.srt"'},
    )


def _clean_err(e: Exception) -> str:
    msg = str(e)
    # 去除 yt-dlp 的 ANSI / 前缀噪音
    msg = msg.replace("ERROR: ", "").strip()
    return msg[:300] if msg else e.__class__.__name__


# --------------------------------------------------------------------------
# 前端静态托管（生产：frontend/dist）
# --------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="static")


def main():
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=bool(os.getenv("RELOAD")))


if __name__ == "__main__":
    main()
