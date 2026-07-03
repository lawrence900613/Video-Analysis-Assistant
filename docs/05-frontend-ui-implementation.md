# Frontend UI Implementation (Current Authoritative Reference)

> Status: Consolidated from current code and the July 2026 UI redesign. For AI behavior, see [04-ai-video-understanding-implementation.md](./04-ai-video-understanding-implementation.md). For download flow, see [VIDEO_DOWNLOAD.md](./VIDEO_DOWNLOAD.md).

## 1. Page structure

```text
App.jsx
├── Navbar.jsx              Top nav + language toggle + Upgrade Pro
├── Hero.jsx                Hero: headline, URL input, trust stats, AI preview card
├── ResultCard.jsx          Parse result (conditional)
│   └── SummarizeSSESection.jsx   AI understanding (summary / transcript / mind map / Q&A)
├── PlatformGallery.jsx     Platform cards (external links)
├── FeatureSection.jsx      Feature highlights
├── PricingSection.jsx      Pricing comparison
├── FaqSection.jsx          FAQ
└── Footer.jsx
```

**Removed**: `HistoryPanel.jsx` and localStorage parse history; the navbar no longer has a History entry.

**Legacy (unmounted)**: `UnderstandingSection.jsx` (old AI UI), `analysisCache.js` (old cache). Production path uses only `SummarizeSSESection` + `summarizeCache.js`.

## 2. Visual system

Design direction: **AI video knowledge workbench** — light mesh background + ink / electric blue / hot pink / soft cyan brand tokens, inspired by high-conversion tool pages (BibiGPT / NoteGPT style).

### 2.1 Tokens and global styles

| File | Role |
| --- | --- |
| [frontend/tailwind.config.js](../frontend/tailwind.config.js) | `brand` / `accent` / `neon` / `ink` palettes; `shadow-soft` / `shadow-glow`; animations |
| [frontend/src/index.css](../frontend/src/index.css) | Global background glow, reusable utility classes |

Common reusable classes:

| Class | Purpose |
| --- | --- |
| `brand-gradient` / `brand-text` | Primary buttons, emphasized headings |
| `card` | White glass-style card |
| `premium-panel` / `dark-panel` | Hero preview, dark info sidebar in result area |
| `search-box` | Hero URL input container |
| `premium-button` / `soft-button` | Primary / secondary CTAs |
| `section-badge` | Section label pill |
| `mobile-dock` | Mobile fixed bottom download bar |

### 2.2 Copy and i18n

- Dictionary: [frontend/src/i18n.jsx](../frontend/src/i18n.jsx)
- Language persistence: `localStorage.lang`; synced to `<html lang>`
- Hero headline: localized via i18n (`hero.title` — e.g. zh: download/summarize/understand video; en: equivalent conversion copy)
- Platform, feature, and pricing sections emphasize **AI summary / transcript / mind map / Q&A** value

## 3. Hero

[frontend/src/components/Hero.jsx](../frontend/src/components/Hero.jsx)

- Left column: badge, headline, subcopy, URL form, three `trust_items` metrics
- Right column: `HeroPreview` dark card — Summary / Transcript / Chat capability bars (**no** 4-step download flow; flow moved to result area)
- Bottom: platform name pills (display only; clickable cards are in PlatformGallery below)

Flow steps are still driven by `computeFlowStep` for Hero input logic, but are no longer shown at the bottom of the preview card.

## 4. Result workbench (ResultCard)

[frontend/src/components/ResultCard.jsx](../frontend/src/components/ResultCard.jsx)

Layout:

- **Left `dark-panel`**: cover, duration, title, author, view count
- **Right white card**: platform/subtitle badges → **`ResultFlow` workflow** → subtitle language → quality → download/subtitle/translate buttons → progress bar

### 4.1 Workflow bar (ResultFlow)

Visible when the user scrolls to the result area; replaces the small steps that used to sit under the Hero preview card:

| Step | i18n label (concept) | Default highlight |
| --- | --- | --- |
| 1 | Paste link | Completed |
| 2 | Parse info | Completed |
| 3 | Choose format | **Current** (after parse succeeds) |
| 4 | Start download | Highlighted while downloading |

i18n key: `result.workflow` (en: "Current workflow"; zh: localized equivalent).

### 4.2 View count formatting

[frontend/src/utils/history.js](../frontend/src/utils/history.js) now exports only `formatViews()` (localStorage history logic removed).

## 5. AI understanding area (SummarizeSSESection)

See [04](./04-ai-video-understanding-implementation.md) §5. UI highlights:

- Dark gradient header + white “Understand with AI / Re-analyze” button
- Tabs: Summary / Transcript / Mind map / Q&A (latter two gated)
- [StreamingProgress.jsx](../frontend/src/components/StreamingProgress.jsx): three stages (fetch subtitles → generate summary → done) + bottom percent bar; **step connectors aligned to icon centers** (grid + absolutely positioned progress line, avoiding negative-margin misalignment)

During streaming: `documentElement` gets `page-scroll-anchor-disabled` to prevent abnormal page scroll.

## 6. Platform cards (PlatformGallery)

[frontend/src/components/PlatformGallery.jsx](../frontend/src/components/PlatformGallery.jsx)

Each card is `<a target="_blank" rel="noopener noreferrer">`:

| Platform | Link |
| --- | --- |
| YouTube | https://www.youtube.com/ |
| Bilibili | https://www.bilibili.com/ |
| Douyin / TikTok | zh UI → douyin.com; en UI → tiktok.com |
| Twitch | https://www.twitch.tv/ |
| X / Twitter | https://x.com/ |
| Xiaohongshu | https://www.xiaohongshu.com/ |
| 1000+ sites | yt-dlp supported sites list |

## 7. Verification commands

```powershell
cd frontend
npm run build
```

AI-related backend tests (on Windows, prefer `py`):

```powershell
cd backend
py -m pytest tests/test_summarize_sse.py tests/test_mindmap_chat.py tests/test_transcript_utils.py tests/test_downloader.py
```

## 8. Known limitations

- After lazy-loading `MindMapPanel`, Vite may still warn about chunks > 500KB.
- Pricing Pro features are display-only; payments are not integrated.
- No parse history; users must keep URLs themselves or rely on browser history.

## 9. Development guardrails

- Prefer Tailwind classes and [index.css](../frontend/src/index.css) utilities for UI changes; avoid heavy UI libraries.
- Do not restore `HistoryPanel` unless product explicitly requires it and defines a storage strategy.
- When changing AI tabs or SSE UI, update the relevant sections in [04](./04-ai-video-understanding-implementation.md) and this document.
