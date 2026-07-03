"""yt-dlp wrapper: parse, download, and fetch subtitles.

Design principle: build on yt-dlp; only wrap parameters, never patch its source.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled, DownloadError

from . import bilibili_subtitles
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
    netloc = parts.netloc
    if parts.scheme in ("http", "https") and netloc.lower() == "bilibili.com":
        netloc = "www.bilibili.com"
    if not parts.query:
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not (k.lower().startswith(_TRACKING_PARAM_PREFIXES) or k.lower() in _TRACKING_PARAM_KEYS)
    ]
    return urlunsplit((parts.scheme, netloc, parts.path, urlencode(kept), parts.fragment))

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


_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _ytdlp_common_opts() -> dict:
    """Shared yt-dlp options to reduce YouTube 403 / format errors."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        # Pace subtitle/metadata requests to reduce YouTube 429 rate limits.
        "sleep_interval": 1,
        "max_sleep_interval": 5,
        "sleep_interval_requests": 1,
        "sleep_interval_subtitles": 2,
        "http_headers": {"User-Agent": _BROWSER_UA},
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

_DANMAKU_LANG = "danmaku"
_BILIBILI_BVID_RE = re.compile(r"(BV[0-9A-Za-z]+)")
_BILIBILI_EXTRACTORS = frozenset({
    "BiliBili",
    "Bilibili",
    "BiliBiliBangumi",
    "BiliBiliBangumiMedia",
    "BiliBiliBangumiSeason",
    "BiliBiliAudio",
    "BiliBiliPlayer",
})


def _is_bilibili_url(url: str) -> bool:
    try:
        host = urlsplit(normalize_url(url)).netloc.lower()
    except ValueError:
        return False
    return host.endswith("bilibili.com") or host.endswith("b23.tv")


def _is_bilibili_info(info: dict) -> bool:
    extractor = (info.get("extractor_key") or info.get("extractor") or "").strip()
    if extractor in _BILIBILI_EXTRACTORS:
        return True
    webpage = info.get("webpage_url") or info.get("original_url") or ""
    return bool(webpage) and _is_bilibili_url(str(webpage))


def _is_danmaku_lang(lang: str) -> bool:
    return (lang or "").lower() == _DANMAKU_LANG


def _has_ytdlp_auth_config() -> bool:
    return bool(settings.ytdlp_cookies or settings.ytdlp_cookies_from_browser)


def _collect_subtitle_langs(subtitles: dict, auto_caps: dict) -> list[str]:
    langs = set(subtitles.keys()) | set(auto_caps.keys())
    return sorted(lang for lang in langs if not _is_danmaku_lang(lang))


def _subtitle_metadata_empty(info: dict) -> bool:
    subtitles = info.get("subtitles") or {}
    auto_caps = info.get("automatic_captions") or {}
    return not _collect_subtitle_langs(subtitles, auto_caps)


def ensure_subtitle_metadata(url: str, info: dict) -> dict:
    """Populate subtitle tracks when yt-dlp skips them during plain extract_info.

    Bilibili (and some other sites) only fill ``info['subtitles']`` when
    ``listsubtitles`` or ``writesubtitles`` is enabled. Without this probe,
    parse() always reports ``has_subtitles=false`` even when CC subs exist.
    """
    if not _is_bilibili_info(info) and not _subtitle_metadata_empty(info):
        return info
    if not _is_bilibili_info(info) and _subtitle_metadata_empty(info):
        return info

    url = normalize_url(url)
    opts = {**_base_opts(), "listsubtitles": True}
    with YoutubeDL(opts) as ydl:
        probed = ydl.extract_info(url, download=False)

    if probed.get("_type") == "playlist" and probed.get("entries"):
        entries = [e for e in probed["entries"] if e]
        if entries:
            probed = entries[0]

    probed_subs = probed.get("subtitles") or {}
    if probed_subs:
        info = {**info, "subtitles": probed_subs}
    probed_auto = probed.get("automatic_captions")
    if probed_auto:
        info = {**info, "automatic_captions": probed_auto}
    return info


def extract_info(url: str, *, probe_subtitles: bool = False) -> dict:
    """Run yt-dlp metadata extraction once (shared by parse / subtitle fetch)."""
    url = normalize_url(url)
    with YoutubeDL(_base_opts()) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get("_type") == "playlist" and info.get("entries"):
        entries = [e for e in info["entries"] if e]
        if entries:
            info = entries[0]
    if probe_subtitles or _is_bilibili_info(info):
        info = ensure_subtitle_metadata(url, info)
    return info


def format_parse_result(info: dict, url: str) -> dict:
    """Build API-facing parse payload from raw yt-dlp info."""
    options = _build_quality_options(info)

    subtitles = info.get("subtitles") or {}
    auto_caps = info.get("automatic_captions") or {}
    sub_langs = _collect_subtitle_langs(subtitles, auto_caps)
    is_bilibili = _is_bilibili_info(info)
    has_subtitles = bool(sub_langs)
    subtitle_uncertain = is_bilibili and not has_subtitles

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
        "has_subtitles": has_subtitles,
        "subtitle_uncertain": subtitle_uncertain,
        "subtitle_requires_cookies": subtitle_uncertain and not _has_ytdlp_auth_config(),
        "subtitle_langs": sub_langs,
        "ffmpeg": has_ffmpeg(),
    }


def parse(url: str) -> dict:
    """Parse video metadata: title, thumbnail, duration, quality options, etc."""
    url = normalize_url(url)
    info = extract_info(url, probe_subtitles=True)
    result = format_parse_result(info, url)
    if result.get("subtitle_uncertain"):
        bvid = _extract_bilibili_bvid(url, info)
        try:
            public_langs = bilibili_subtitles.public_subtitle_langs(bvid) if bvid else []
        except Exception:
            public_langs = []
        if public_langs:
            result["has_subtitles"] = True
            result["subtitle_uncertain"] = False
            result["subtitle_requires_cookies"] = False
            result["subtitle_langs"] = public_langs
    return result


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

_PREFERRED_LANGS = ["zh-Hans", "zh-CN", "zh", "zh-Hant", "en", "en-US", "en-GB"]
_SUBTITLE_FETCH_RETRIES = 5
_SUBTITLE_HTTP_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "text/vtt,text/plain,application/json,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
# Obscure ISO-639-1 codes YouTube lists but rarely has real captions for.
_LOW_PRIORITY_LANGS = frozenset({"aa", "ab", "ae", "ak", "an", "av", "ay", "ba", "bi", "bm", "br", "ch", "co", "cr", "cu", "cv", "cy", "ee", "eo", "ff", "fj", "fo", "fy", "ga", "gd", "gl", "gn", "gu", "gv", "ha", "ho", "ht", "hz", "ia", "ie", "ig", "ii", "ik", "io", "iu", "jv", "kg", "ki", "kj", "kl", "km", "kn", "kr", "ks", "ku", "kv", "kw", "la", "lb", "lg", "li", "ln", "lo", "lu", "mg", "mh", "mi", "mk", "mn", "mo", "mr", "ms", "mt", "my", "na", "nb", "nd", "ne", "ng", "nn", "no", "nr", "nv", "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "ps", "qu", "rm", "rn", "rw", "sa", "sc", "sd", "se", "sg", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sw", "ta", "te", "tg", "ti", "tk", "tl", "tn", "to", "ts", "tt", "tw", "ty", "ug", "ur", "uz", "ve", "vi", "vo", "wa", "wo", "xh", "yi", "yo", "za", "zu"})


class SubtitleRateLimitError(RuntimeError):
    """YouTube (or upstream) rejected subtitle requests with HTTP 429."""


def _lang_base(code: str) -> str:
    return (code or "").split("-", 1)[0].lower()


def _lang_matches(preferred: str, available: str) -> bool:
    if preferred == available:
        return True
    pref_base = _lang_base(preferred)
    avail_base = _lang_base(available)
    if pref_base == avail_base:
        return True
    # Treat zh variants as equivalent (zh-Hans, zh-CN, zh-TW, …).
    if pref_base == "zh" and avail_base == "zh":
        return True
    return False


def _find_lang(prefer: list[str], available: dict) -> Optional[str]:
    for lang in prefer:
        if lang in available:
            return lang
    for lang in prefer:
        for key in available:
            if _lang_matches(lang, key):
                return key
    return None


def _fallback_lang(available: dict, prefer: list[str]) -> Optional[str]:
    matched = _find_lang(prefer, available)
    if matched:
        return matched

    def _rank(code: str) -> tuple[int, str]:
        base = _lang_base(code)
        if code in _PREFERRED_LANGS:
            return (0, code)
        if base in {_lang_base(p) for p in _PREFERRED_LANGS}:
            return (1, code)
        if base in _LOW_PRIORITY_LANGS or len(base) == 2 and code in _LOW_PRIORITY_LANGS:
            return (4, code)
        if base in ("en", "zh", "ja", "ko", "fr", "de", "es", "pt", "ru"):
            return (2, code)
        return (3, code)

    return min(available.keys(), key=_rank, default=None)


def _is_rate_limit_error(exc: BaseException) -> bool:
    if isinstance(exc, HTTPError) and exc.code == 429:
        return True
    if isinstance(exc, SubtitleRateLimitError):
        return True
    msg = str(exc).lower()
    return "429" in msg or "too many requests" in msg


def _is_transient_http_error(exc: BaseException) -> bool:
    if isinstance(exc, HTTPError) and exc.code in (408, 429, 500, 502, 503, 504):
        return True
    if isinstance(exc, (URLError, TimeoutError, ConnectionError, OSError)):
        return True
    if isinstance(exc, DownloadError) and _is_rate_limit_error(exc):
        return True
    msg = str(exc).lower()
    return any(token in msg for token in ("429", "502", "503", "504", "timed out", "connection reset"))


def _backoff_seconds(attempt: int, *, rate_limited: bool = False) -> float:
    base = min(2 ** attempt + 1, 20)
    return base * (1.5 if rate_limited else 1.0)


def _subtitle_rate_limit_message() -> str:
    return (
        "YouTube subtitle service is temporarily rate-limited (HTTP 429). "
        "Please wait a minute and try again."
    )


def _raise_subtitle_fetch_error(exc: Exception) -> None:
    if _is_rate_limit_error(exc):
        raise SubtitleRateLimitError(_subtitle_rate_limit_message()) from exc
    raise exc


def _fetch_url_with_retry(ydl: YoutubeDL, url: str) -> bytes:
    """Fetch subtitle bytes; retry on transient HTTP errors (e.g. YouTube 429)."""
    last_err: Exception | None = None
    for attempt in range(_SUBTITLE_FETCH_RETRIES):
        try:
            return ydl.urlopen(Request(url, headers=_SUBTITLE_HTTP_HEADERS)).read()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if _is_transient_http_error(e) and attempt < _SUBTITLE_FETCH_RETRIES - 1:
                time.sleep(_backoff_seconds(attempt, rate_limited=_is_rate_limit_error(e)))
                continue
            break
    if last_err:
        raise last_err
    raise RuntimeError("Failed to fetch subtitle content")


def _read_subtitle_from_dir(tmpdir: str) -> Optional[str]:
    for path in Path(tmpdir).glob("*.vtt"):
        return path.read_text(encoding="utf-8", errors="ignore")
    for path in Path(tmpdir).glob("*"):
        if path.is_file() and path.suffix.lower() in (".vtt", ".srt", ".ass", ".json3", ".srv3", ".ttml", ""):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if text.strip():
                return text
    return None


def _download_subtitle_file(
    url: str,
    lang: str,
    is_auto: bool,
) -> str:
    """Fallback: let yt-dlp download subtitle to a temp file (with retries)."""
    last_err: Exception | None = None
    for attempt in range(_SUBTITLE_FETCH_RETRIES):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                opts = {
                    **_ytdlp_common_opts(),
                    "skip_download": True,
                    "outtmpl": os.path.join(tmpdir, "%(id)s"),
                    "writesubtitles": not is_auto,
                    "writeautomaticsub": is_auto,
                    "subtitleslangs": [lang],
                    "subtitlesformat": "vtt/best",
                    "quiet": True,
                    "no_warnings": True,
                }
                with YoutubeDL(opts) as ydl:
                    ydl.download([url])

                content = _read_subtitle_from_dir(tmpdir)
                if content:
                    return content
            last_err = RuntimeError("Subtitle download produced no file")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if _is_transient_http_error(e) and attempt < _SUBTITLE_FETCH_RETRIES - 1:
                time.sleep(_backoff_seconds(attempt, rate_limited=_is_rate_limit_error(e)))
                continue
            break
    if last_err and _is_rate_limit_error(last_err):
        raise SubtitleRateLimitError(_subtitle_rate_limit_message()) from last_err
    if last_err:
        raise last_err
    raise RuntimeError("Subtitle download produced no file")


def _read_track_content(
    track: dict,
    ydl: YoutubeDL,
    url: str,
    lang: str,
    is_auto: bool,
) -> tuple[str | None, Exception | None]:
    if track.get("data"):
        return str(track["data"]), None

    fetch_err: Exception | None = None
    if track.get("url"):
        try:
            raw = _fetch_url_with_retry(ydl, track["url"])
            return raw.decode("utf-8", errors="ignore"), None
        except Exception as e:  # noqa: BLE001
            fetch_err = e
            if _is_rate_limit_error(e):
                return None, e

    try:
        content = _download_subtitle_file(url, lang, is_auto)
        return content, None
    except Exception as e:  # noqa: BLE001
        return None, e if fetch_err is None else fetch_err


def _extract_bilibili_bvid(url: str, info: Optional[dict] = None) -> Optional[str]:
    for value in (
        (info or {}).get("bvid"),
        (info or {}).get("id"),
        (info or {}).get("webpage_url"),
        (info or {}).get("original_url"),
        url,
    ):
        if not value:
            continue
        match = _BILIBILI_BVID_RE.search(str(value))
        if match:
            return match.group(1)
    return None


def _bilibili_login_required_message() -> str:
    return (
        "Bilibili did not expose real subtitles through public metadata, page JSON, or "
        "player subtitle APIs for this video. If the page only shows captions after you "
        "log in, configure backend/.env with YTDLP_COOKIES=/path/to/cookies.txt or "
        "YTDLP_COOKIES_FROM_BROWSER=edge/chrome, then restart the backend. Danmaku is "
        "not used as transcript."
    )


def _bilibili_fetch_json(ydl: YoutubeDL, api_url: str, referer: str) -> dict:
    request = Request(api_url, headers={"Referer": referer, "User-Agent": _BROWSER_UA})
    raw = ydl.urlopen(request).read().decode("utf-8", errors="ignore")
    return json.loads(raw)


def _bilibili_subtitle_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return url


def _seconds_to_ts(seconds: float) -> str:
    return _ms_to_ts(round(float(seconds) * 1000))


def _parse_bilibili_subtitle_json(content: str) -> list[dict]:
    """Parse Bilibili subtitle JSON from subtitle_url into SRT-like cues."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    cues: list[dict] = []
    for item in data.get("body") or []:
        text = _clean_cue_text(str(item.get("content") or ""))
        if not text:
            continue
        start = item.get("from")
        end = item.get("to")
        if start is None or end is None:
            continue
        cues.append({
            "start": _seconds_to_ts(float(start)),
            "end": _seconds_to_ts(float(end)),
            "text": text,
        })
    return _dedupe_overlapping_cues(cues)


def _fetch_bilibili_subtitle(
    url: str,
    prefer: list[str],
    info: Optional[dict] = None,
) -> Optional[dict]:
    """Fetch real Bilibili CC/AI subtitles from player APIs.

    yt-dlp often exposes only danmaku as ``subtitles['danmaku']``. Bilibili's
    player endpoint can list real subtitle_url entries, usually requiring the
    same cookies a browser session uses.
    """
    bvid = _extract_bilibili_bvid(url, info)
    if not bvid:
        return None

    public_sub = bilibili_subtitles.public_subtitle(bvid, prefer)
    if public_sub:
        cues = _parse_bilibili_subtitle_json(public_sub["content"])
        if not cues:
            raise ValueError("subtitle_empty:Bilibili subtitle track was empty or unreadable.")
        plain = "\n".join(c["text"] for c in cues)
        max_chars = settings.max_subtitle_chars
        if max_chars and len(plain) > max_chars:
            plain = plain[:max_chars]
        return {
            "lang": public_sub["lang"],
            "is_auto": public_sub["is_auto"],
            "cues": cues,
            "plain_text": plain,
        }

    referer = f"https://www.bilibili.com/video/{bvid}/"
    with YoutubeDL(_base_opts()) as ydl:
        view = _bilibili_fetch_json(
            ydl,
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            referer,
        )
        video = view.get("data") or {}
        aid = video.get("aid")
        cid = video.get("cid") or ((video.get("pages") or [{}])[0].get("cid"))
        if not aid or not cid:
            return None

        subtitle_data: dict | None = None
        for endpoint in (
            f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}",
            f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}",
        ):
            player = _bilibili_fetch_json(ydl, endpoint, referer)
            data = player.get("data") or {}
            subtitle_data = data.get("subtitle") or {}
            if subtitle_data.get("subtitles"):
                break

        tracks = (subtitle_data or {}).get("subtitles") or []
        if not tracks:
            if _has_ytdlp_auth_config():
                raise ValueError(
                    "no_subtitles:Bilibili did not return any real subtitle tracks for this account/video. "
                    "Danmaku is not used as transcript."
                )
            raise ValueError(f"bilibili_login_required:{_bilibili_login_required_message()}")

        by_lang: dict[str, list[dict]] = {}
        for track in tracks:
            lang = track.get("lan") or track.get("lang") or track.get("id")
            subtitle_url = track.get("subtitle_url") or track.get("url")
            if not lang or not subtitle_url:
                continue
            by_lang.setdefault(str(lang), []).append(track)

        lang = _fallback_lang(by_lang, prefer)
        if not lang:
            return None

        track = by_lang[lang][0]
        subtitle_url = _bilibili_subtitle_url(track.get("subtitle_url") or track.get("url") or "")
        if not subtitle_url:
            return None

        content = _fetch_url_with_retry(ydl, subtitle_url).decode("utf-8", errors="ignore")
        cues = _parse_bilibili_subtitle_json(content)
        if not cues:
            raise ValueError("subtitle_empty:Bilibili subtitle track was empty or unreadable.")
        plain = "\n".join(c["text"] for c in cues)
        max_chars = settings.max_subtitle_chars
        if max_chars and len(plain) > max_chars:
            plain = plain[:max_chars]
        return {
            "lang": lang,
            "is_auto": bool(track.get("ai_type") or track.get("type") == "ai"),
            "cues": cues,
            "plain_text": plain,
        }


def _parse_subtitle_content(content: str, track: dict) -> list[dict]:
    ext = (track.get("ext") or "").lower()
    if ext == "srt" or re.search(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->", content):
        return _parse_srt(content)
    if ext == "vtt" or "-->" in content:
        return _parse_vtt(content)
    return _parse_json3(content)


def fetch_subtitle(
    url: str,
    prefer_langs: Optional[list[str]] = None,
    info: Optional[dict] = None,
) -> dict:
    """Fetch subtitles (manual first, then auto-generated).

    Returns {lang, cues:[{start,end,text}], plain_text}

    Pass ``info`` from a prior ``parse()`` / ``extract_info`` call to avoid a
    duplicate metadata request (helps reduce YouTube 429 rate limits).
    """
    prefer = (prefer_langs or []) + _PREFERRED_LANGS
    url = normalize_url(url)

    try:
        if info is None:
            info = extract_info(url, probe_subtitles=True)
        elif _subtitle_metadata_empty(info) and _is_bilibili_info(info):
            info = ensure_subtitle_metadata(url, info)

        subtitles = info.get("subtitles") or {}
        auto_caps = info.get("automatic_captions") or {}

        candidates = _track_candidates(subtitles, auto_caps, prefer)
        if not candidates:
            if _is_bilibili_info(info):
                bilibili_sub = _fetch_bilibili_subtitle(url, prefer, info)
                if bilibili_sub:
                    return bilibili_sub
            raise ValueError(
                "No subtitles available for this video (manual or auto). Summary/translation is not possible."
            )

        last_err: Exception | None = None
        with YoutubeDL(_base_opts()) as ydl:
            for chosen_lang, tracks, is_auto in candidates:
                track = _pick_format(tracks, ["vtt", "srt", "srv3", "srv1", "ttml", "json3"])
                content, fetch_err = _read_track_content(track, ydl, url, chosen_lang, is_auto)
                if fetch_err:
                    last_err = fetch_err
                    continue
                if not content or not content.strip():
                    last_err = ValueError("Subtitle content is empty")
                    continue

                cues = _parse_subtitle_content(content, track)
                if not cues:
                    last_err = ValueError("Subtitle content is empty")
                    continue
                plain = "\n".join(c["text"] for c in cues)

                max_chars = settings.max_subtitle_chars
                if max_chars and len(plain) > max_chars:
                    plain = plain[:max_chars]

                return {"lang": chosen_lang, "is_auto": is_auto, "cues": cues, "plain_text": plain}

        if last_err:
            _raise_subtitle_fetch_error(last_err)
        raise ValueError(
            "No subtitles available for this video (manual or auto). Summary/translation is not possible."
        )
    except SubtitleRateLimitError:
        raise
    except ValueError:
        raise
    except Exception as e:  # noqa: BLE001
        _raise_subtitle_fetch_error(e)


def _without_danmaku(tracks: dict) -> dict:
    return {lang: entries for lang, entries in tracks.items() if not _is_danmaku_lang(lang)}


def _choose_track(subtitles: dict, auto_caps: dict, prefer: list[str]):
    subtitles = _without_danmaku(subtitles)
    lang = _find_lang(prefer, subtitles)
    if lang:
        return lang, subtitles[lang], False
    if subtitles:
        lang = _fallback_lang(subtitles, prefer)
        if lang:
            return lang, subtitles[lang], False
    lang = _find_lang(prefer, auto_caps)
    if lang:
        return lang, auto_caps[lang], True
    if auto_caps:
        lang = _fallback_lang(auto_caps, prefer)
        if lang:
            return lang, auto_caps[lang], True
    return None, [], False


def _track_candidates(subtitles: dict, auto_caps: dict, prefer: list[str]) -> list[tuple[str, list[dict], bool]]:
    preferred_bases = {_lang_base(p) for p in _PREFERRED_LANGS}

    def _rank_lang(code: str) -> tuple[int, str]:
        base = _lang_base(code)
        if code in _PREFERRED_LANGS:
            return (0, code)
        if base in preferred_bases:
            return (1, code)
        if base in _LOW_PRIORITY_LANGS or len(base) == 2 and code in _LOW_PRIORITY_LANGS:
            return (4, code)
        if base in ("en", "zh", "ja", "ko", "fr", "de", "es", "pt", "ru"):
            return (2, code)
        return (3, code)

    def _ordered_langs(available: dict) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()

        def _append(lang: str | None) -> None:
            if lang and lang not in seen and available.get(lang):
                seen.add(lang)
                ordered.append(lang)

        for lang in prefer:
            _append(lang if lang in available else None)
        for lang in prefer:
            for key in available:
                if _lang_matches(lang, key):
                    _append(key)
        for key in sorted(available.keys(), key=_rank_lang):
            _append(key)
        return ordered

    candidates: list[tuple[str, list[dict], bool]] = []
    for is_auto, source in ((False, _without_danmaku(subtitles)), (True, auto_caps)):
        for lang in _ordered_langs(source):
            candidates.append((lang, source[lang], is_auto))
    return candidates


def _pick_format(tracks: list[dict], pref_exts: list[str]) -> dict:
    for ext in pref_exts:
        for t in tracks:
            if t.get("ext") == ext:
                return t
    return tracks[0]


_VTT_TS = re.compile(
    r"(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})"
)


def _clean_cue_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _dedupe_overlapping_cues(cues: list[dict]) -> list[dict]:
    """Drop rolling auto-caption partials (same-start updates and suffix-only repeats)."""
    if not cues:
        return []

    collapsed: list[dict] = []
    for cue in cues:
        if collapsed and cue["start"] == collapsed[-1]["start"]:
            if len(cue["text"]) > len(collapsed[-1]["text"]):
                collapsed[-1] = cue
        else:
            collapsed.append(cue)

    result: list[dict] = []
    for cue in collapsed:
        text = cue["text"]
        if not text:
            continue
        if not result:
            result.append(cue)
            continue

        prev_text = result[-1]["text"]
        if text == prev_text or text in prev_text or prev_text.endswith(text):
            continue

        result.append(cue)

    return result


_SRT_TS = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})"
)


def _parse_srt(content: str) -> list[dict]:
    cues: list[dict] = []
    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        idx = 1 if lines[0].isdigit() else 0
        if idx >= len(lines):
            continue
        match = _SRT_TS.search(lines[idx])
        if not match:
            continue
        text = _clean_cue_text(" ".join(lines[idx + 1 :]))
        if not text:
            continue
        cues.append({
            "start": match.group(1),
            "end": match.group(2),
            "text": text,
        })
    return _dedupe_overlapping_cues(cues)


def _parse_vtt(content: str) -> list[dict]:
    cues: list[dict] = []
    blocks = re.split(r"\n\s*\n", content)
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
        text = _clean_cue_text(" ".join(text_lines))
        if not text:
            continue
        cues.append({
            "start": _norm_ts(m.group(1)),
            "end": _norm_ts(m.group(2)),
            "text": text,
        })
    return _dedupe_overlapping_cues(cues)


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
        text = _clean_cue_text("".join(s.get("utf8", "") for s in segs))
        if not text:
            continue
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 0)
        cues.append({
            "start": _ms_to_ts(start_ms),
            "end": _ms_to_ts(start_ms + dur_ms),
            "text": text,
        })
    return _dedupe_overlapping_cues(cues)


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
