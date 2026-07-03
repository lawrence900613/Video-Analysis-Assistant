# Requirements Analysis · Video Analysis Assistant (Universal Video Downloader)

> Version: v1.0 | Last updated: on completion of Phase 3
> This document describes the business background, users and scenarios, functional and non-functional requirements, scope boundaries, and risks. It serves as context for AI/developers in future iterations.

## 1. Background

Many users need to save videos locally, but face these pain points:

- Some platforms do not support direct downloads;
- Even when supported, it is often inconvenient (no batch download, limited resolution, various restrictions, requires a client, etc.);
- There is no unified, cross-platform entry point usable anytime, anywhere (including on mobile).

Therefore we build a "universal video downloader" website that lets users **paste a link and quickly download** videos from any platform, and beyond downloading, offers **understanding and translation** value-added capabilities.

Project positioning: **for learning purposes**, exploring a new development model of "standing on the shoulders of open-source giants + AI value-add". Please respect copyright, be mindful of account risks, and use for personal learning only.

## 2. Target Users and Typical Scenarios

| User | Scenario |
| --- | --- |
| Students / self-learners | Save online courses and tutorials for offline viewing; read an AI summary of long videos before deciding to watch in detail |
| Content creators | Collect material, reference competitor videos; download watermark-free clips |
| Language learners | Download foreign-language videos and translate subtitles to study while watching |
| General users | Casually save favorite short videos on mobile |

Core needs keywords: **fast, all-platform, anytime/anywhere, mobile-friendly, selectable quality**.

## 3. Functional Requirements

### 3.1 Core Features (Implemented)

- **F1 Link parsing**: Enter a video link and parse the title, cover, author, duration, source platform, available qualities/formats, and whether subtitles exist.
- **F2 Video download**: Download locally after selecting a quality/format.
  - Supports "Best quality (auto merge)", "individual resolution tiers", and "Audio only MP3".
  - Video-only streams are automatically merged with the best audio track (requires ffmpeg).
- **F3 AI video summary**: Auto-extract subtitles → LLM generates key points, TL;DR, and an outline.
- **F4 Subtitle translation**: Extract subtitles → LLM translates → export a standard SRT file.

### 3.2 Interaction & Experience Requirements (Implemented)

- **F5 Distinctive, conversion-oriented UI**: AI video workbench landing (light mesh + brand tokens, hero + result workbench + AI tabs), highlighting paid value (PRO badges, value-focused copy, upgrade CTA). Current UI: [05-frontend-ui-implementation.md](./05-frontend-ui-implementation.md).
- **F6 Responsive / mobile-friendly**: Adapts to phone, tablet, and desktop.
- **F7 Chinese/English switch**: One-click switch of the whole site's language, with the choice persisted locally.

### 3.3 Extended Features (Planned, not yet implemented)

- Batch download (paste multiple links and queue downloads).
- Real payment/membership (Alipay / Stripe) and user accounts.
- Speech-to-text for videos without subtitles (integrate Whisper, then summarize/translate).
- Real-time download progress (SSE / WebSocket).
- History and cloud storage (introduce a database).

## 4. Non-Functional Requirements

- **Lightweight**: No database, minimal dependencies, runs on a single machine.
- **Python-first tech stack**: Core download capability built on the Python ecosystem.
- **Reliable download capability**: Reuse a mature open-source project instead of building parsing logic in-house to reduce risk.
- **Extensible**: Clear layering and module boundaries for easy future additions.
- **Portable**: Runs on Windows / macOS / Linux.
- **Compliance reminders**: The page clearly states copyright and learning-use notices.

## 5. Scope

**In scope this cycle (Phases 1-3):**
- Core download (F1, F2)
- AI video summary (F3) + subtitle translation (F4), with **real** LLM integration
- Complete frontend UI (F5, F6) and Chinese/English switch (F7)

**Out of scope this cycle:**
- Batch download, real payment, user accounts/database, speech-to-text, download progress bar.
  (The UI reserves mind-share via "coming soon / PRO" markers; features to be delivered in later iterations.)

## 6. Key Decisions and Rationale

| Decision point | Conclusion | Rationale |
| --- | --- | --- |
| Build download in-house? | No, reuse yt-dlp | Supports 1000+ platforms, 100k+ stars, mature and stable, avoids risk |
| Need a backend? | Yes | Server-side download/merge, call the LLM, hide secrets |
| Need a database? | Not this cycle | Keep it lightweight; no persistence needed |
| Frontend form | React (Vite) SPA | Component-based, fast builds, good UX, easy to extend |
| AI integration | OpenAI-compatible protocol | One codebase can switch between OpenAI/DeepSeek/Moonshot/Qwen, etc. |

## 7. Risks and Compliance

- **Copyright risk**: For personal learning only; the page includes copyright and learning-use notices; distribution is discouraged.
- **Account risk**: Frequent downloads may trigger platform anti-abuse controls; this is the user's responsibility.
- **Platform-change risk**: Platform revamps may break parsing → mitigated by upgrading yt-dlp.
- **Merge dependency**: HD merging depends on ffmpeg; when missing, it degrades to single-file formats.
- **Secret security**: The LLM key is stored in the backend `.env` and never sent to the frontend.

## 8. Acceptance Criteria

1. Pasting a mainstream-platform link successfully parses info and a quality list.
2. Selecting any quality / audio-only downloads successfully to local disk.
3. After configuring the LLM, videos with subtitles can generate a summary and export a translated SRT.
4. The page displays correctly on mobile and desktop, and Chinese/English can be toggled with one click.
5. Edge cases (no subtitles / no ffmpeg, etc.) show clear, friendly messages.
