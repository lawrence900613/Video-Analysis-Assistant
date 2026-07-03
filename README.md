# Video Analysis Assistant

A universal video downloader. Download any platform's video anytime, anywhere, with one click. Built on the open-source
[yt-dlp](https://github.com/yt-dlp/yt-dlp) (supports 1000+ video sites), it offers
**video download + AI video summary + subtitle translation**. The frontend is React, the backend is FastAPI:
lightweight, database-free, and mobile-friendly.

> For technical study and exchange only. Please respect each platform's copyright rules, use downloads
> for personal learning only, and be mindful of account risks.

## Docs

See [docs/README.md](docs/README.md) for the full index. **Current implementation references:**

- [AI video understanding (SSE, mindmap, chat)](docs/04-ai-video-understanding-implementation.md)
- [Frontend UI (landing, workbench, i18n)](docs/05-frontend-ui-implementation.md)
- [Video download (yt-dlp, progress, ffmpeg)](docs/VIDEO_DOWNLOAD.md)

Historical: [01 requirements](docs/01-requirements-analysis.md), [02 design](docs/02-design-document.md), [02/03 AI design drafts](docs/02-ai-video-understanding-design.md).

## Features

- Paste a link to parse instantly and choose quality / format (including best-quality auto-merge and audio-only MP3)
- Server-side download relayed to the browser; works on phone / tablet / desktop
- AI video summary: auto-extract subtitles → LLM generates Chinese key points and outline
- Subtitle translation: extract subtitles → LLM translation → export standard SRT
- AI video workbench UI with streaming summary, transcript, mind map, and Q&A
- One-click Chinese/English language switch

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18 + Vite 5 + Tailwind CSS 3 |
| Backend | FastAPI + Uvicorn |
| Download core | yt-dlp (wrapped directly, source unmodified) |
| AI | OpenAI-compatible protocol (OpenAI / DeepSeek / Moonshot / Qwen, etc.) |

## Directory Structure

```
Video-Analysis-Assistant/
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI routes + static hosting
│   │   ├── downloader.py   # yt-dlp wrapper: parse/download/subtitles
│   │   ├── ai.py           # LLM: summary/translation
│   │   └── config.py       # .env config
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # React (Vite + Tailwind)
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── i18n.jsx
│       └── components/
├── docs/                   # Requirements analysis / design document
└── README.md
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- ffmpeg (needed for HD video merge and MP3 transcode; auto-degrades to single-file formats when missing)
  - Windows: `winget install Gyan.FFmpeg` or download from https://ffmpeg.org and add to PATH
  - macOS: `brew install ffmpeg`

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Configure the LLM (required for AI summary / translation)
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
# Edit .env and fill in LLM_API_KEY / LLM_BASE_URL / LLM_MODEL

# Start the backend (http://localhost:8000)
uvicorn app.main:app --reload --port 8000
```

> Downloading videos does not require the LLM; only AI summary / subtitle translation does.

### 2. Frontend (development)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 , /api is proxied to backend :8000
```

Open http://localhost:5173 to use it.

### 3. Production (backend serves the frontend)

```bash
cd frontend
npm run build            # produces frontend/dist

cd ../backend
uvicorn app.main:app --port 8000
# Visit http://localhost:8000 (backend serves frontend/dist automatically)
```

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Health check (ffmpeg / LLM readiness) |
| POST | `/api/parse` | Parse video info and quality options `{ url }` |
| POST | `/api/download` | Download and relay the file `{ url, format_id }` |
| POST | `/api/summary` | AI video summary `{ url }` |
| POST | `/api/translate` | Translate subtitles and export SRT `{ url, target_lang }` |

API docs: after starting the backend, visit http://localhost:8000/docs

## LLM Configuration Example (backend/.env)

```env
# DeepSeek example
LLM_API_KEY=sk-xxxxxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

For other services, just change `LLM_BASE_URL` and `LLM_MODEL` (OpenAI / Moonshot / Qwen, etc. all use the OpenAI-compatible protocol).

## FAQ

- **AI summary/translation reports "no subtitles available"**: the video has no manual or auto subtitles. Whisper speech-to-text can be integrated later.
- **HD quality missing**: without ffmpeg, video-only streams cannot be merged, so only directly downloadable formats are shown.
- **A platform fails to parse**: upgrading yt-dlp usually fixes it: `pip install -U yt-dlp`.
