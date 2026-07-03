# Video Download Feature Summary

> This document covers implementation details, setup, and troubleshooting for the video download feature.  
> For project overview, see [README.md](../README.md). For AI and UI, see [04](./04-ai-video-understanding-implementation.md) and [05](./05-frontend-ui-implementation.md). Doc index: [docs/README.md](./README.md).

---

## Overview

After a user pastes a video URL, the system runs the full pipeline: **parse URL → choose quality/format → download with progress → save file in the browser**.

| Stage | Description |
| --- | --- |
| Parse | `POST /api/parse` returns title, thumbnail, duration, available quality options, subtitle languages, etc. |
| Select quality | The frontend shows resolution choices (including best-quality auto-merge and audio-only MP3) |
| Download | Async job flow: `start` → poll `progress` → on completion, trigger native browser save via the `file` endpoint |
| Cancel | Click the button again during download, or use `AbortController` to call `cancel` |

---

## Supported Platforms

The download core is [yt-dlp](https://github.com/yt-dlp/yt-dlp), which supports [1000+ sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) in theory. Development and testing focused on the following:

| Platform | Status | Notes |
| --- | --- | --- |
| **YouTube** | ✅ | Anonymous downloads use `android_vr` + `web` clients for the full DASH quality ladder |
| **Instagram** | ✅ | Requires **Python ≥ 3.10** + **curl_cffi** (browser TLS fingerprint impersonation); anonymous access without cookies |
| **Bilibili** | ✅ | `dm_img` parameter patch fixes HTTP **412** anonymous parse failures |
| **Twitch** | UI showcase | Listed in the platform gallery; actual downloads use yt-dlp’s generic extractor |
| **TikTok / X / Xiaohongshu, etc.** | yt-dlp dependent | Behavior may change with yt-dlp version updates |

Full site list: [yt-dlp supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## Architecture

```
┌─────────────────┐     REST API      ┌──────────────────────────────────┐
│  React frontend │ ◄──────────────► │  FastAPI (backend/app/main.py)   │
│  api.js polling │                   │  ├── downloader.py  (yt-dlp wrap) │
│  ResultCard UI  │                   │  └── download_jobs.py (in-memory) │
└─────────────────┘                   └──────────────────────────────────┘
                                              │
                                              ▼
                                    yt-dlp + curl_cffi + ffmpeg
```

### Download Job Flow

1. **`POST /api/download/start`** — Creates a background thread job and returns `job_id`
2. **`GET /api/download/{job_id}/progress`** — Returns `stage`, `percent`, `speed_bps`, `eta_seconds`
3. **`POST /api/download/{job_id}/cancel`** — Requests cancellation and cleans up the temp directory
4. **`GET /api/download/{job_id}/file`** — One-shot file retrieval when ready; response includes `Content-Disposition`; temp file is deleted after the response

> A synchronous `POST /api/download` endpoint (blocks until complete) is retained for compatibility and debugging.

---

## Key Backend Features

| Module | Capability |
| --- | --- |
| **URL normalization** (`normalize_url`) | Strips tracking params (`utm_*`, `igsh`, `fbclid`, etc.) while preserving valid query keys such as YouTube `v` |
| **Bilibili 412 patch** (`_patch_bilibili_dm_img`) | Injects `dm_img_*` / `web_location` placeholder params into `wbi/playurl` requests without modifying yt-dlp source |
| **Windows ffmpeg detection** (`_effective_path`) | Merges process PATH with Machine/User registry Path so subprocesses find ffmpeg after WinGet install |
| **Content-Disposition** | Sends both ASCII `filename=` and UTF-8 `filename*=` so non-ASCII titles are not saved as `.txt` |
| **Async jobs** | Thread + in-memory dict; progress hooks report speed and ETA; cancel raises `DownloadCancelled` and `rmtree`s the temp dir |
| **Quality options** | Grouped by resolution; skips video-only streams that need merge when ffmpeg is absent; optional MP3 post-processing |

Related files:

- `backend/app/downloader.py` — parse, download, subtitles
- `backend/app/download_jobs.py` — job lifecycle
- `backend/app/main.py` — API routes
- `backend/app/config.py` — `.env` and `DOWNLOAD_DIR`

---

## Key Frontend Features

| Feature | Implementation |
| --- | --- |
| **Real progress bar** | Polls progress API; shows percent, speed, ETA, merge/transfer stage |
| **Cancel download** | Second click during download → `AbortController` + `cancel` API |
| **Step indicator** | `ResultFlow` in result area (paste → parse → select format → download); `computeFlowStep` drives step highlight |
| **Thumbnail fix** | `<img referrerPolicy="no-referrer">` avoids blank images from CDN hotlink protection |
| **Native download** | On completion, `<a click>` to `/file` — no fetch→blob→objectURL (fixes Chrome/Edge `{uuid}.tmp` leftovers) |
| **Platform gallery** | Clickable cards open platform sites; Douyin (zh) / TikTok (en) by UI language |

Related files:

- `frontend/src/api.js` — `downloadVideo`, `cancelDownload`
- `frontend/src/components/ResultCard.jsx` — download UI, `ResultFlow`, progress
- `frontend/src/utils/progress.js` — step computation and formatting
- `frontend/src/utils/history.js` — `formatViews()` only (playback count display)

---

## Environment Setup

### Python virtual environment

Use a **Python 3.12** virtual environment (Instagram anonymous extraction depends on a recent runtime):

```powershell
cd backend
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Do **not** use an older **Python 3.9** venv: Instagram `curl_cffi` impersonation will not work correctly.

### Core dependencies (`backend/requirements.txt`)

| Package | Purpose |
| --- | --- |
| `yt-dlp>=2026.6.9` | Download core; includes refactored Instagram extractor |
| `curl_cffi>=0.7` | Browser TLS fingerprint for anonymous Instagram access |
| `fastapi` / `uvicorn` | HTTP server |

### ffmpeg

HD merge (video+audio) and MP3 transcoding require ffmpeg:

```powershell
winget install Gyan.FFmpeg
```

Restart the terminal after install. Backend `/api/health` with `ffmpeg: true` indicates successful detection.

### Optional: Cookie configuration

In `backend/.env` (see `.env.example`):

```env
YTDLP_COOKIES=cookies.txt
# or
YTDLP_COOKIES_FROM_BROWSER=edge
```

Use for private videos, age-restricted content, 403 errors, and similar cases.

---

## How to Run

### Backend

```powershell
cd backend
.\.venv312\Scripts\Activate.ps1
copy .env.example .env   # first run; AI features need LLM_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (development)

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000` by default.

### Production (single-server)

```powershell
cd frontend && npm run build
cd ..\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If `frontend/dist` exists, FastAPI serves static assets automatically.

### Unit tests

```powershell
cd backend
pip install -r requirements-dev.txt
pytest -q
```

---

## API Quick Reference

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Health check (ffmpeg, LLM readiness) |
| POST | `/api/parse` | Parse video metadata |
| POST | `/api/download/start` | Start async download |
| GET | `/api/download/{id}/progress` | Query progress |
| POST | `/api/download/{id}/cancel` | Cancel job |
| GET | `/api/download/{id}/file` | Download file (one-shot) |

---

## Known Limitations

1. **Private / age-restricted content** — Requires Cookie config or browser cookie import; anonymous access is not guaranteed on all sites.
2. **In-memory job storage** — Job state lives in process memory; **job IDs are invalid after service restart**; not suitable for horizontal scaling across instances.
3. **No global concurrency queue** — Many simultaneous downloads consume disk and bandwidth; use moderately on a single machine.
4. **Platform policy changes** — Run `pip install -U yt-dlp` regularly; Bilibili, Instagram, and others may adjust anti-bot measures again.
5. **No ffmpeg fallback for merge/MP3** — Progressive single-file streams still work, but highest-quality merge and MP3 conversion are unavailable without ffmpeg.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Instagram empty response / parse failure | Python 3.9 venv or missing curl_cffi | Switch to `.venv312` (3.12), `pip install curl_cffi` |
| Bilibili HTTP 412 | Missing dm_img anti-bot params | Confirm `_patch_bilibili_dm_img()` in `downloader.py` runs on module import |
| `/api/health` shows `ffmpeg: false` | PATH missing WinGet install location | `winget install Gyan.FFmpeg`, restart terminal; backend also reads registry Path on Windows |
| Port 8000 in use | Stale uvicorn process | `netstat -ano \| findstr :8000`, end the process, or change `PORT` in `.env` |
| Thumbnail not showing | Referrer policy / CDN block | Frontend uses `referrerPolicy="no-referrer"`; persistent failure is often a temporary CDN issue |
| Download filename becomes `.txt` | Content-Disposition encoding | Fixed: backend sends `filename*` UTF-8 encoding |
| `{uuid}.tmp` in Downloads folder | Blob download revoked objectURL too early | **Fixed**: native `/file` download instead |
| YouTube 403 / format unavailable | Platform policy or login required | Upgrade yt-dlp; configure cookies if needed |
| Disk still used after cancel | Cancel cleanup failed | Check `backend/downloads/`; cancel should `rmtree` the job directory |

---

## File Layout

```
backend/
├── app/
│   ├── downloader.py      # yt-dlp wrapper, Bilibili patch, ffmpeg detection
│   ├── download_jobs.py   # async jobs and cancellation
│   └── main.py            # REST routes
├── tests/
│   ├── test_downloader.py
│   └── test_download_jobs.py
├── requirements.txt
└── .env.example

frontend/src/
├── api.js                 # downloadVideo flow
├── components/
│   └── ResultCard.jsx     # workbench, ResultFlow, progress, cancel
└── utils/
    ├── progress.js
    └── history.js         # formatViews() only
```

---

*Document version: aligned with the video download feature implementation.*
