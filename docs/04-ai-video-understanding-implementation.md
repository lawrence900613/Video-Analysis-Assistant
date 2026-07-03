# AI Video Understanding Implementation (Current Authoritative Reference)

> Status: Consolidated from current code. Documents `02` and `03` remain useful as historical design background; prefer this document for ongoing development.  
> Frontend UI layout and visual system: [05-frontend-ui-implementation.md](./05-frontend-ui-implementation.md). Full index: [README.md](./README.md).

## 1. Current feature status

Implemented AI video understanding capabilities:

| Feature | Status | Entry / files |
| --- | --- | --- |
| Summary SSE | Implemented | `POST /api/summarize`, `backend/app/summarize_service.py`, `frontend/src/components/SummarizeSSESection.jsx` |
| Timestamped transcript | Implemented | `POST /api/transcript`; summarize SSE also pushes transcript in an early event |
| Mind map (markmap) | Implemented | `POST /api/mindmap` returns LLM tree + Markdown; frontend renders with `markmap-view` |
| AI Q&A SSE with citations | Implemented | `POST /api/chat` SSE; streaming answer + cue-aligned citations |

The production UI mount point is `SummarizeSSESection` inside `ResultCard.jsx`. The repo still contains legacy `UnderstandingSection.jsx`, but the result page does not use it.

## 2. Current architecture and data flow

Core pipeline:

```text
User pastes URL
  -> POST /api/parse
  -> Frontend shows download area + AI understanding area
  -> User clicks "Understand with AI"
  -> POST /api/summarize (SSE)
  -> Backend parse / fetch transcript
  -> SSE transcript event arrives first
  -> SSE summary_delta streams summary
  -> SSE summary final structured payload
  -> Frontend caches transcript / summary
  -> Mind map / chat reuse transcript / summary
```

Important behavior:

- AI analysis does **not** start automatically after parse; the user must click "Understand with AI".
- Transcript loading has two paths: returned by `/api/summarize` `transcript` event when understanding starts; or explicit load on the Transcript tab via `/api/transcript`.
- Mind map and Chat tabs are gated: require existing `transcript` or `summary`.
- Mind map is **not** auto-generated after summary; user opens the tab and clicks generate. Frontend passes cached `summary` and `transcript` to avoid re-fetching subtitles.
- Chat requires transcript; frontend passes transcript/summary; backend does not re-fetch subtitles.
- Scroll anchor fix during streaming: `SummarizeSSESection` and `ChatPanel` add `page-scroll-anchor-disabled` on `documentElement` while streaming to avoid page jump on token updates; chat auto-scrolls only when the user is near the bottom.

## 3. API reference

### `GET /api/health`

Response:

```json
{
  "status": "ok",
  "ffmpeg": true,
  "llm_ready": true,
  "whisper_ready": false,
  "analysis_features": ["summarize_sse", "transcript", "mindmap", "chat"]
}
```

`whisper_ready` is currently always `false`.

### `POST /api/parse`

Request:

```json
{ "url": "https://..." }
```

Main response fields:

| Field | Description |
| --- | --- |
| `id` / `title` / `uploader` / `thumbnail` / `duration` / `duration_string` | Basic video metadata |
| `webpage_url` / `extractor` / `view_count` | Page URL, platform, view count from yt-dlp |
| `options` | Download quality list: `id`, `label`, `ext`, `height`, `filesize`, `needs_merge`, `recommended`, `audio_only` |
| `has_subtitles` | Confirmed real subtitles available |
| `subtitle_uncertain` | `true` for Bilibili when public metadata did not confirm subtitles; frontend still allows AI attempt |
| `subtitle_requires_cookies` | `true` when `subtitle_uncertain=true` and backend has no cookies configured |
| `subtitle_langs` | Available subtitle languages (excludes danmaku) |
| `ffmpeg` | Whether backend can find ffmpeg |

### `POST /api/transcript`

Request:

```json
{
  "url": "https://...",
  "prefer_lang": "zh-Hans"
}
```

Response:

```json
{
  "title": "...",
  "lang": "zh-Hans",
  "is_auto": true,
  "duration": 1234,
  "cues": [
    {
      "index": 0,
      "start": "00:00:01,000",
      "end": "00:00:03,000",
      "start_sec": 1.0,
      "end_sec": 3.0,
      "text": "..."
    }
  ],
  "plain_text": "...",
  "truncated": false,
  "source": "subtitle"
}
```

Errors:

- 400: empty URL
- 401: Bilibili or platform requires login cookies
- 422: no subtitles, empty subtitles, parse failure
- 429: YouTube subtitle rate limit

### `POST /api/summarize` (SSE)

Request:

```json
{
  "url": "https://...",
  "prefer_lang": "zh-Hans",
  "output_lang": "Simplified Chinese",
  "force_refresh": false
}
```

HTTP headers:

```text
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

Events:

| event | data | Description |
| --- | --- | --- |
| `stage` | `{ "name": "fetching_transcript" }` | Start fetching subtitles |
| `transcript` | Transcript object | Pushed immediately after subtitle fetch succeeds |
| `stage` | `{ "name": "summarizing" }` | Short video single-pass streaming summary |
| `stage` | `{ "name": "chunking", "chunk_total": 5 }` | Long video chunking |
| `stage` | `{ "name": "map", "chunk_current": 2, "chunk_total": 5 }` | Map-Reduce map progress |
| `stage` | `{ "name": "reducing" }` | Long video reduce phase begins streaming |
| `summary_delta` | `{ "text": "..." }` | Markdown token chunk |
| `summary` | VideoSummary object | Final structured summary |
| `error` | `{ "code": "...", "message": "..." }` | Business error |
| `done` | `{ "ok": true }` | Normal completion |

`summary` structure:

```json
{
  "tldr": "...",
  "key_points": ["..."],
  "chapters": [
    {
      "title": "...",
      "summary": "...",
      "start_sec": 12.0,
      "end_sec": 80.0,
      "start_label": "0:12",
      "end_label": "1:20"
    }
  ],
  "output_lang": "Simplified Chinese",
  "generated_at": "2026-..."
}
```

Main error codes: `invalid_url`, `duration_exceeded`, `login_required`, `no_subtitles`, `subtitle_empty`, `rate_limited`, `parse_failed`, `llm_failed`.

### `POST /api/mindmap`

Request:

```json
{
  "url": "https://...",
  "prefer_lang": "zh-Hans",
  "output_lang": "Simplified Chinese",
  "summary": { "...": "optional if frontend cached" },
  "transcript": { "...": "optional if frontend cached" }
}
```

Response:

```json
{
  "mindmap": {
    "root": {
      "id": "root",
      "label": "...",
      "type": "root",
      "children": []
    }
  },
  "markdown": "# ...\n## ...",
  "model": "deepseek-chat"
}
```

Implementation notes:

- Backend uses `ai.generate_mindmap_llm()` for JSON tree, then `mindmap_tree_to_markdown()` for markmap Markdown.
- Frontend `MindMapPanel` uses `markmap-lib` + `markmap-view`; lazy-loaded via `lazy()` to reduce initial bundle size.

### `POST /api/chat` (SSE)

Request:

```json
{
  "url": "https://...",
  "prefer_lang": "zh-Hans",
  "output_lang": "Simplified Chinese",
  "messages": [
    { "role": "user", "content": "What is this video mainly about?" }
  ],
  "transcript": { "...": "recommended from frontend" },
  "summary": { "...": "optional" }
}
```

Events:

| event | data | Description |
| --- | --- | --- |
| `stage` | `{ "name": "retrieving" }` | Prepare transcript / context |
| `stage` | `{ "name": "answering" }` | Start LLM streaming answer |
| `answer_delta` | `{ "text": "..." }` | Answer token chunk |
| `answer` | `{ "answer": "...", "citations": [...], "model": "..." }` | Final answer and citations |
| `error` | `{ "code": "...", "message": "..." }` | Business error |
| `done` | `{ "ok": true }` | Normal completion |

Citation structure:

```json
{
  "start_sec": 12.0,
  "end_sec": 18.0,
  "quote": "subtitle excerpt",
  "cue_index": 3
}
```

Backend first tries to extract citations from `[mm:ss]` / `[hh:mm:ss]` in the LLM answer and align to cues; if citations are missing or unreliable `[00:00]` appears, keyword-recalled cues are used as fallback.

## 4. Subtitle handling details

### General strategy

- URLs are normalized via `downloader.normalize_url()` to strip common share/tracking params.
- Subtitle priority: user `prefer_lang` → default preference `zh-Hans` / `zh-CN` / `zh` / `zh-Hant` / `en` / `en-US` / `en-GB` → common language fallback.
- Real subtitles exclude Bilibili `danmaku`; danmaku is never used as transcript.
- `build_transcript()` adds `index`, `start_sec`, `end_sec` per cue for chapter alignment and citation jump.
- `MAX_SUBTITLE_CHARS` affects plain-text truncation sent to the LLM; long videos use `CHUNK_MAX_CHARS` chunking for summary.

### YouTube

- `extract_info(..., probe_subtitles=True)` for subtitle metadata.
- Subtitle track candidates: `vtt`, `srt`, `srv3`, `srv1`, `ttml`, `json3`.
- If track has direct `url`, prefer yt-dlp `urlopen` to read content.
- On direct read failure, fallback to yt-dlp writing subtitle files and reading from temp dir.
- Retries with exponential backoff for 408/429/5xx, timeouts, connection resets; 429 becomes `SubtitleRateLimitError`.
- Chinese preference matches zh variants (e.g. `zh-Hans` can match `zh-CN` tracks).

### Bilibili

- `normalize_url()` canonicalizes bare `bilibili.com` to `www.bilibili.com`.
- `downloader.py` non-invasive monkey patch on yt-dlp Bilibili playinfo requests adds `dm_img_*` / `web_location` to mitigate anonymous HTTP 412.
- `parse()` calls `bilibili_subtitles.public_subtitle_langs()` for cookie-free public subtitle probe when yt-dlp metadata is uncertain.
- `bilibili_subtitles.py`:
  - Warms anonymous opener with Bilibili-issued buvid cookies;
  - Queries `x/v2/subtitle/web/view` protobuf API and extracts subtitle URLs from length-delimited fields;
  - Decodes encrypted `//subtitle.bilibili.com/...` paths to readable `aisubtitle.hdslb.com` URLs;
  - Falls back to `x/player/v2` / `x/player/wbi/v2` when web/view has no result.
- `_fetch_bilibili_subtitle()` prefers public subtitles; tries player API when public subtitles unavailable.
- Login-only subtitles require cookies in `backend/.env`:
  - Prefer `YTDLP_COOKIES=/path/to/cookies.txt` (Netscape format).
  - `YTDLP_COOKIES_FROM_BROWSER=edge/chrome` as fallback using browser profile on the backend machine.

## 5. Frontend components and state machine

Production UI (full page structure in [05](./05-frontend-ui-implementation.md)):

```text
ResultCard (two-column workbench + ResultFlow workflow bar)
  -> SummarizeSSESection (dark header + tabbed panels)
       -> StreamingProgress
       -> StreamingSummaryPanel / SummaryPanel
       -> TranscriptPanel
       -> MindMapPanel (lazy)
       -> ChatPanel
```

**Removed**: parse history (`HistoryPanel` / localStorage `vaa_history`). No History nav entry.

**ResultFlow**: after successful parse, shows 4 steps in the result area (paste → parse → choose format → download) so users still see workflow context after scrolling past the Hero preview.

State lives mainly in `SummarizeSSESection`:

| state | Description |
| --- | --- |
| `activeTab` | `summary` / `transcript` / `mindmap` / `chat` |
| `transcript` | Subtitles from SSE or `/api/transcript` |
| `summary` | Final structured summary from `/api/summarize` |
| `streamingText` | Markdown accumulated from `summary_delta` |
| `stage` / `streaming` / `error` | Current streaming state |
| `mindmap` / `mindmapMarkdown` | Mind map JSON and markmap Markdown |
| `chatMessages` | Multi-turn Q&A including assistant citations |
| `highlightCueIndex` | Cue highlight + scroll when user clicks chat citation |

State flow:

```text
idle
  -> click Understand
  -> streaming(fetching_transcript)
  -> transcript ready
  -> streaming(summarizing or chunking/map/reducing)
  -> summary ready
  -> done/cache
  -> user opens mindmap/chat
```

Caching:

- `summarizeCache.js` uses `localStorage`, 24-hour TTL.
- Key format: `summarize_v2:{hashUrl(url)}:{preferLang}`.
- Cached: `transcript`, `summary`, `mindmap`, `mindmapMarkdown`, `chatMessages`.
- Re-analyze sends `force_refresh=true`, clears cache for current url/lang, resets mindmap/chat.

Explicit transcript load:

- If user has not clicked Understand but video has subtitles, Transcript tab shows a "Load subtitles" button.
- Click calls `fetchTranscript(url, preferLang)` — subtitles only, no LLM.

## 6. Configuration and environment variables

Core LLM config:

```env
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

Download / subtitle / analysis config:

```env
DOWNLOAD_DIR=downloads
MAX_SUBTITLE_CHARS=16000
CHUNK_MAX_CHARS=6000
MAX_ANALYSIS_DURATION_SEC=7200
```

Cookies config:

```env
# Preferred: exported Netscape cookies file
YTDLP_COOKIES=C:/Users/you/Downloads/bilibili-cookies.txt

# Fallback: read browser profile on backend machine
YTDLP_COOKIES_FROM_BROWSER=edge
YTDLP_COOKIES_FROM_BROWSER=chrome
```

Security:

- `LLM_API_KEY` belongs only in backend `.env`; never in frontend, real examples in docs, test fixtures, or git.
- Do not commit real cookie files.

## 7. Tests and verification

Backend focused tests:

```powershell
cd backend
py -m pytest tests/test_summarize_sse.py tests/test_mindmap_chat.py tests/test_transcript_utils.py tests/test_downloader.py
```

Frontend build:

```powershell
cd frontend
npm run build
```

Manual verification suggestions:

- YouTube: video with confirmed subtitles — parse does not auto-analyze; after "Understand with AI", transcript appears then streaming summary.
- Bilibili: `https://www.bilibili.com/video/BV1mAAmzqEfP` — public subtitle probe, language, transcript, summary, mind map, chat citations.
- No LLM key: `/api/health` `llm_ready=false`; frontend disables AI button or shows config hint.
- No subtitles / login-required subtitles: readable frontend errors; backend never treats danmaku as transcript.

Run the above commands when changing related code; scope by risk.

## 8. Known limitations and follow-up work

- ASR / faster-whisper not implemented; videos without real subtitles cannot use AI understanding yet.
- Analysis is subtitle-text only; no frame / multimodal understanding.
- `markmap` dependencies are large; `MindMapPanel` is lazy-loaded but Vite may still warn on chunk size — consider further splitting.
- Long browser automation acceptance not fully documented; rely on backend pytest, frontend build, and manual URL checks.
- YouTube subtitles may hit 429; retry/backoff exists but user may need to wait and retry.
- Bilibili public subtitle APIs may change; keep cookies fallback but do not require cookies by default.
- `UnderstandingSection.jsx` and `analysisCache.js` are legacy unmounted code; confirm no other entry points before removal.
- `/api/summary` remains as deprecated sync compatibility; frontend primary path is `/api/summarize`.

## 9. Development guardrails

- When external API/SDK/library behavior is uncertain, confirm via Context7 or official docs — do not rely on memory.
- Open/closed principle: add capabilities in new service/router/utils; minimize changes to download main path and legacy download APIs.
- Minimal change surface: AI understanding and download share a page but separate state machines — do not wire AI SSE into download job polling.
- Never expose keys, cookies, or real user data; `.env` examples use placeholders only.
- Bilibili: distinguish real subtitles from danmaku; never use danmaku as transcript.
- Frontend: reuse cached transcript/summary when available; request backend only on re-analyze, explicit subtitle load, or missing data.
- New SSE events: update backend service, frontend stream parser/consumer, i18n strings, and this document together.
