# Documentation Index

This folder is organized into **current authoritative references** and **historical design background**.

## Current authoritative references (read these first)

| Document | Scope |
| --- | --- |
| [04-ai-video-understanding-implementation.md](./04-ai-video-understanding-implementation.md) | AI understanding: SSE summary, transcript, mind map, chat, APIs, subtitle strategy, caching, tests |
| [05-frontend-ui-implementation.md](./05-frontend-ui-implementation.md) | Frontend UI: landing page, result workbench, visual system, i18n, platform links, removed features |
| [VIDEO_DOWNLOAD.md](./VIDEO_DOWNLOAD.md) | Video download: yt-dlp pipeline, progress bar, cancel, ffmpeg, cookies |

## Historical / background documents (do not treat as current implementation)

| Document | Notes |
| --- | --- |
| [01-requirements-analysis.md](./01-requirements-analysis.md) | Early requirements and scope boundaries |
| [02-design-document.md](./02-design-document.md) | Early full-stack design (some UI/API details are outdated) |
| [02-ai-video-understanding-design.md](./02-ai-video-understanding-design.md) | AI understanding v1 design (polling job model is obsolete) |
| [03-ai-video-understanding-v2-design.md](./03-ai-video-understanding-v2-design.md) | AI understanding v2 design (SSE direction is correct; details superseded by 04) |

## Quick reference: current frontend main flow

```text
App
  -> Navbar / Hero (paste URL)
  -> ResultCard (download + ResultFlow step bar)
       -> SummarizeSSESection (AI understanding tabs)
  -> PlatformGallery / FeatureSection / PricingSection / FaqSection / Footer
```

AI entry point: `ResultCard` → `SummarizeSSESection` (not `UnderstandingSection.jsx`).
