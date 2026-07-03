"""yt-dlp wrapper: parse, download, and fetch subtitles.

Design principle: build on yt-dlp; only wrap parameters, never patch its source.
"""
from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from .config import get_settings

settings = get_settings()

# Tracking / share-link query params that carry no extraction value. Instagram,
# YouTube, TikTok, etc. append these when a user taps "copy link". yt-dlp usually
# tolerates them, but stripping them keeps URLs clean and avoids extractor edge cases.
_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAM_KEYS = {
    "igsh", "igshid", "fbclid", "gclid", "si", "feature", "app",
    "share_id", "share_app_id", "_r", "_d", "source", "ref",
    "spm_id_from", "vd_source", "from", "seid",
}


def normalize_url(url: str) -> str:
    """Strip known tracking/share query params while preserving meaningful ones (e.g. YouTube ``v``)."""
    url = (url or "").strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not parts.query:
        return url
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not (k.lower().startswith(_TRACKING_PARAM_PREFIXES) or k.lower() in _TRACKING_PARAM_KEYS)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))

# ---------------------------------------------------------------------------
# Bilibili anti-bot patch (HTTP 412 on wbi/playurl)
# ---------------------------------------------------------------------------
# Bilibili's `x/player/wbi/playurl` gateway now rejects requests that lack the
# browser risk-control params (dm_img_list / dm_img_str / dm_cover_img_str /
# dm_img_inter / web_location) with HTTP 412 Precondition Failed. yt-dlp does
# not yet send them, so videos whose webpage does not inline playinfo fail to
# parse anonymously. We inject harmless dummy values (the same shape a browser
# sends) before yt-dlp signs the request. This wraps the extractor method; it
# does not modify yt-dlp's source. Only BilibiliBaseIE is touched, so other
# extractors (YouTube, Instagram, ...) are unaffected.

def _patch_bilibili_dm_img() -> None:
    try:
        from yt_dlp.extractor.bilibili import BilibiliBaseIE
    except Exception:  # noqa: BLE001 - yt-dlp internals may change
        return

    if getattr(BilibiliBaseIE, "_dm_img_patched", False):
        return

    _orig_download_playinfo = BilibiliBaseIE._download_playinfo

    # Dummy WebGL fingerprint values; content is irrelevant, presence is what
    # the gateway checks. Kept static and idempotent.
    _DM_IMG_DEFAULTS = {
        "dm_img_list": "[]",
        "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
        "dm_cover_img_str": (
            "QU5HTEUgKEludGVsLCBJbnRlbChSKSBVSEQgR3JhcGhpY3MgKDB4MDAwMDlCQzUp"
            "IERpcmVjdDNEMTEgdnNfNV8wIHBzXzVfMCwgRDNEMTEpR29vZ2xlIEluYy4gKEludGVsKQ"
        ),
        "dm_img_inter": '{"ds":[],"wh":[0,0,0],"of":[0,0,0]}',
        "web_location": "1315873",
    }

    def _patched_download_playinfo(self, bvid, cid, headers=None, query=None):
        merged = dict(query or {})
        for key, value in _DM_IMG_DEFAULTS.items():
            merged.setdefault(key, value)
        return _orig_download_playinfo(self, bvid, cid, headers=headers, query=merged)

    BilibiliBaseIE._download_playinfo = _patched_download_playinfo
    BilibiliBaseIE._dm_img_patched = True


_patch_bilibili_dm_img()

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------

def _effective_path() -> str:
    """Return a PATH that includes machine + user entries on Windows.

    Cursor/uvicorn child processes often inherit a trimmed PATH and miss
    WinGet/shim directories where ffmpeg is installed.
    """
    parts: list[str] = []
    seen: set[str] = set()
    for chunk in (
        os.environ.get("PATH", ""),
        os.environ.get("Path", ""),
    ):
        for entry in chunk.split(os.pathsep):
            entry = entry.strip()
            if entry and entry.lower() not in seen:
                seen.add(entry.lower())
                parts.append(entry)
    if os.name == "nt":
        for scope in ("Machine", "User"):
            try:
                import winreg

                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE if scope == "Machine" else winreg.HKEY_CURRENT_USER, "Environment") as key:
                    reg_path, _ = winreg.QueryValueEx(key, "Path")
            except OSError:
                reg_path = ""
            for entry in str(reg_path).split(os.pathsep):
                entry = entry.strip()
                if entry and entry.lower() not in seen:
                    seen.add(entry.lower())
                    parts.append(entry)
    return os.pathsep.join(parts)


def has_ffmpeg() -> bool:
    """Return whether ffmpeg is installed (needed for HD merge / audio transcoding)."""
    path = _effective_path()
    return shutil.which("ffmpeg", path=path) is not None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _human_size(num: Optional[float]) -> Optional[str]:
    if not num:
        return None
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"


def _ytdlp_common_opts() -> dict:
    """Shared yt-dlp options to reduce YouTube 403 / format errors."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        # android_vr exposes the full DASH ladder (up to 4K) without login,
        # which the default web/android clients no longer return anonymously.
        # web is kept as a fallback for robustness.
        "extractor_args": {"youtube": {"player_client": ["android_vr", "web"]}},
    }
    if settings.ytdlp_cookies:
        opts["cookiefile"] = str(settings.ytdlp_cookies)
    elif settings.ytdlp_cookies_from_browser:
        opts["cookiesfrombrowser"] = (settings.ytdlp_cookies_from_browser,)
    return opts


def _base_opts() -> dict:
    return {
        **_ytdlp_common_opts(),
        "skip_download": True,
    }


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def parse(url: str) -> dict:
    """Parse video metadata: title, thumbnail, duration, quality options, etc."""
    url = normalize_url(url)
    with YoutubeDL(_base_opts()) as ydl:
        info = ydl.extract_info(url, download=False)

    # Playlists: use the first entry
    if info.get("_type") == "playlist" and info.get("entries"):
        entries = [e for e in info["entries"] if e]
        if entries:
            info = entries[0]

    options = _build_quality_options(info)

    subtitles = info.get("subtitles") or {}
    auto_caps = info.get("automatic_captions") or {}
    sub_langs = sorted(set(list(subtitles.keys()) + list(auto_caps.keys())))

    thumbnail = info.get("thumbnail")
    if isinstance(thumbnail, str) and thumbnail.startswith("http://"):
        thumbnail = "https://" + thumbnail[len("http://") :]

    return {
        "id": info.get("id"),
        "title": info.get("title") or "Untitled video",
        "uploader": info.get("uploader") or info.get("channel") or info.get("uploader_id"),
        "thumbnail": thumbnail,
        "duration": info.get("duration"),
        "duration_string": _format_duration(info.get("duration")),
        "webpage_url": info.get("webpage_url") or url,
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "view_count": info.get("view_count"),
        "options": options,
        "has_subtitles": bool(sub_langs),
        "subtitle_langs": sub_langs,
        "ffmpeg": has_ffmpeg(),
    }


def _format_duration(seconds: Optional[float]) -> Optional[str]:
    if not seconds:
        return None
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _build_quality_options(info: dict) -> list[dict]:
    """Build selectable quality/format options from yt-dlp formats.

    - Video-only formats use `<id>+bestaudio` selectors (requires ffmpeg merge)
    - Appends "best quality (auto)" and "audio only MP3" options
    """
    formats = info.get("formats") or []
    ffmpeg = has_ffmpeg()

    # Group by resolution height and pick the best format per height
    best_by_height: dict[int, dict] = {}
    for f in formats:
        if f.get("vcodec") in (None, "none"):
            continue  # skip audio-only tracks
        height = f.get("height")
        if not height:
            continue
        score = (f.get("tbr") or 0, f.get("filesize") or f.get("filesize_approx") or 0)
        cur = best_by_height.get(height)
        if cur is None or score > cur["_score"]:
            best_by_height[height] = {**f, "_score": score}

    options: list[dict] = []

    # Best quality (auto merge; requires ffmpeg)
    if ffmpeg:
        options.append({
            "id": "bestvideo+bestaudio/best",
            "label": "Best quality (auto)",
            "ext": "mp4",
            "height": 99999,
            "filesize": None,
            "needs_merge": True,
            "recommended": True,
        })

    for height in sorted(best_by_height.keys(), reverse=True):
        f = best_by_height[height]
        has_audio = f.get("acodec") not in (None, "none")
        needs_merge = not has_audio
        if needs_merge and not ffmpeg:
            # Cannot merge without ffmpeg; skip video-only tracks
            continue
        fmt_id = f["format_id"]
        selector = fmt_id if has_audio else f"{fmt_id}+bestaudio/best"
        ext = "mp4" if needs_merge else (f.get("ext") or "mp4")
        options.append({
            "id": selector,
            "label": f"{height}P",
            "ext": ext,
            "height": height,
            "filesize": _human_size(f.get("filesize") or f.get("filesize_approx")),
            "needs_merge": needs_merge,
            "recommended": False,
        })

    # Fallback when no height-based formats exist (some platforms)
    if not options:
        options.append({
            "id": "best[acodec!=none][vcodec!=none]/best",
            "label": "Default quality",
            "ext": "mp4",
            "height": 0,
            "filesize": None,
            "needs_merge": False,
            "recommended": True,
        })

    # Without ffmpeg, prefer a progressive format that does not need merge
    if not ffmpeg and options:
        progressive = [
            o for o in options
            if not o.get("needs_merge") and not o.get("audio_only") and o.get("height", 0) > 0
        ]
        if progressive:
            for o in options:
                o["recommended"] = False
            progressive[0]["recommended"] = True

    # Audio only
    options.append({
        "id": "audio-mp3" if ffmpeg else "bestaudio/best",
        "label": "Audio only MP3" if ffmpeg else "Audio only",
        "ext": "mp3" if ffmpeg else "m4a",
        "height": -1,
        "filesize": None,
        "needs_merge": False,
        "recommended": False,
        "audio_only": True,
    })

    return options


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[str, Optional[int], Optional[float], Optional[int]], None]
ShouldCancel = Callable[[], bool]
JobDirCallback = Callable[[Path], None]


def download(
    url: str,
    format_id: str,
    on_progress: Optional[ProgressCallback] = None,
    should_cancel: Optional[ShouldCancel] = None,
    on_job_dir: Optional[JobDirCallback] = None,
) -> Path:
    """Download to a temp directory and return the file path. format_id may be a selector."""
    url = normalize_url(url)
    job_dir = settings.download_dir / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    if on_job_dir:
        on_job_dir(job_dir)

    opts = {
        **_ytdlp_common_opts(),
        "outtmpl": str(job_dir / "%(title).80B.%(ext)s"),
        "restrictfilenames": False,
        "windowsfilenames": True,
    }

    if format_id == "audio-mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["format"] = format_id
        if "+" in format_id or format_id in ("bestvideo+bestaudio/best", "best"):
            opts["merge_output_format"] = "mp4"

    if on_progress or should_cancel:
        opts["progress_hooks"] = [_make_progress_hook(on_progress, should_cancel)]
        opts["postprocessor_hooks"] = [_make_postprocessor_hook(on_progress, should_cancel)]
        if on_progress:
            on_progress("downloading", 0, None, None)

    try:
        _check_cancel(should_cancel)
        with YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        _check_cancel(should_cancel)

        files = [p for p in job_dir.iterdir() if p.is_file()]
        if not files:
            raise RuntimeError("Download failed: no file was produced")
        # Pick the largest file (merged output after muxing)
        return max(files, key=lambda p: p.stat().st_size)
    except DownloadCancelled:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise


def _check_cancel(should_cancel: Optional[ShouldCancel]) -> None:
    if should_cancel and should_cancel():
        raise DownloadCancelled("Download cancelled by user")


def _make_progress_hook(
    on_progress: Optional[ProgressCallback],
    should_cancel: Optional[ShouldCancel] = None,
):
    def hook(d: dict) -> None:
        _check_cancel(should_cancel)
        if d.get("status") != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes") or 0
        percent: Optional[int] = None
        if total and total > 0:
            percent = min(99, int(downloaded * 100 / total))
        speed = d.get("speed")
        speed_bps = float(speed) if speed and speed > 0 else None
        eta = d.get("eta")
        eta_seconds = int(eta) if eta is not None and eta >= 0 else None
        if on_progress:
            on_progress("downloading", percent, speed_bps, eta_seconds)

    return hook


def _make_postprocessor_hook(
    on_progress: Optional[ProgressCallback],
    should_cancel: Optional[ShouldCancel] = None,
):
    def hook(d: dict) -> None:
        _check_cancel(should_cancel)
        if d.get("status") in ("started", "processing") and on_progress:
            on_progress("processing", None, None, None)

    return hook


# ---------------------------------------------------------------------------
# Subtitles
# ---------------------------------------------------------------------------

_PREFERRED_LANGS = ["zh-Hans", "zh-CN", "zh", "en", "en-US"]


def fetch_subtitle(url: str, prefer_langs: Optional[list[str]] = None) -> dict:
    """Fetch subtitles (manual first, then auto-generated).

    Returns {lang, cues:[{start,end,text}], plain_text}
    """
    prefer = (prefer_langs or []) + _PREFERRED_LANGS
    url = normalize_url(url)

    with YoutubeDL(_base_opts()) as ydl:
        info = ydl.extract_info(url, download=False)

        subtitles = info.get("subtitles") or {}
        auto_caps = info.get("automatic_captions") or {}

        chosen_lang, tracks, is_auto = _choose_track(subtitles, auto_caps, prefer)
        if not tracks:
            raise ValueError(
                "No subtitles available for this video (manual or auto). Summary/translation is not possible."
            )

        # Prefer VTT format
        track = _pick_format(tracks, ["vtt", "srv3", "srv1", "ttml", "json3"])
        content = ydl.urlopen(track["url"]).read().decode("utf-8", errors="ignore")

    cues = _parse_vtt(content) if track.get("ext") == "vtt" or "-->" in content else _parse_json3(content)
    plain = "\n".join(c["text"] for c in cues)

    max_chars = settings.max_subtitle_chars
    if max_chars and len(plain) > max_chars:
        plain = plain[:max_chars]

    return {"lang": chosen_lang, "is_auto": is_auto, "cues": cues, "plain_text": plain}


def _choose_track(subtitles: dict, auto_caps: dict, prefer: list[str]):
    for lang in prefer:
        if lang in subtitles:
            return lang, subtitles[lang], False
    if subtitles:
        lang = next(iter(subtitles))
        return lang, subtitles[lang], False
    for lang in prefer:
        if lang in auto_caps:
            return lang, auto_caps[lang], True
    if auto_caps:
        lang = next(iter(auto_caps))
        return lang, auto_caps[lang], True
    return None, [], False


def _pick_format(tracks: list[dict], pref_exts: list[str]) -> dict:
    for ext in pref_exts:
        for t in tracks:
            if t.get("ext") == ext:
                return t
    return tracks[0]


_VTT_TS = re.compile(
    r"(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})"
)


def _parse_vtt(content: str) -> list[dict]:
    cues: list[dict] = []
    blocks = re.split(r"\n\s*\n", content)
    seen = set()
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        m = None
        text_lines: list[str] = []
        for line in lines:
            hit = _VTT_TS.search(line)
            if hit and m is None:
                m = hit
            elif m is not None:
                text_lines.append(line)
        if not m:
            continue
        text = re.sub(r"<[^>]+>", "", " ".join(text_lines)).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cues.append({
            "start": _norm_ts(m.group(1)),
            "end": _norm_ts(m.group(2)),
            "text": text,
        })
    return cues


def _parse_json3(content: str) -> list[dict]:
    import json
    try:
        data = json.loads(content)
    except Exception:
        return []
    cues: list[dict] = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text:
            continue
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 0)
        cues.append({
            "start": _ms_to_ts(start_ms),
            "end": _ms_to_ts(start_ms + dur_ms),
            "text": text,
        })
    return cues


def _norm_ts(ts: str) -> str:
    ts = ts.replace(",", ".")
    if ts.count(":") == 1:  # MM:SS.mmm -> 00:MM:SS.mmm
        ts = "00:" + ts
    return ts.replace(".", ",")


def _ms_to_ts(ms: int) -> str:
    s, msec = divmod(int(ms), 1000)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d},{msec:03d}"


def cues_to_srt(cues: list[dict]) -> str:
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{c['start']} --> {c['end']}")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)
