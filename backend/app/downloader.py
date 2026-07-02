"""yt-dlp 封装层：解析、下载、字幕获取。

设计原则：站在 yt-dlp 巨人肩膀上，只做参数封装，不改其源码。
"""
from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path
from typing import Optional

from yt_dlp import YoutubeDL

from .config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# 环境检测
# ---------------------------------------------------------------------------

def has_ffmpeg() -> bool:
    """检测本机是否安装 ffmpeg（高清视频合流 / 音频转码需要）。"""
    return shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _human_size(num: Optional[float]) -> Optional[str]:
    if not num:
        return None
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"


def _base_opts() -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

def parse(url: str) -> dict:
    """解析视频信息，返回标题、封面、时长、可选清晰度等。"""
    with YoutubeDL(_base_opts()) as ydl:
        info = ydl.extract_info(url, download=False)

    # 播放列表：取第一个条目
    if info.get("_type") == "playlist" and info.get("entries"):
        entries = [e for e in info["entries"] if e]
        if entries:
            info = entries[0]

    options = _build_quality_options(info)

    subtitles = info.get("subtitles") or {}
    auto_caps = info.get("automatic_captions") or {}
    sub_langs = sorted(set(list(subtitles.keys()) + list(auto_caps.keys())))

    return {
        "id": info.get("id"),
        "title": info.get("title") or "未命名视频",
        "uploader": info.get("uploader") or info.get("channel") or info.get("uploader_id"),
        "thumbnail": info.get("thumbnail"),
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
    """根据 formats 构建给用户选择的清晰度/格式列表。

    - 若视频格式不含音频，则使用 `<id>+bestaudio` 选择器（需 ffmpeg 合流）
    - 追加 "最佳画质(自动)" 与 "仅音频 MP3"
    """
    formats = info.get("formats") or []
    ffmpeg = has_ffmpeg()

    # 按分辨率高度聚合，选出每个高度的最优格式
    best_by_height: dict[int, dict] = {}
    for f in formats:
        if f.get("vcodec") in (None, "none"):
            continue  # 跳过纯音频
        height = f.get("height")
        if not height:
            continue
        score = (f.get("tbr") or 0, f.get("filesize") or f.get("filesize_approx") or 0)
        cur = best_by_height.get(height)
        if cur is None or score > cur["_score"]:
            best_by_height[height] = {**f, "_score": score}

    options: list[dict] = []

    # 最佳画质（自动，需 ffmpeg 合流）
    if ffmpeg:
        options.append({
            "id": "bestvideo+bestaudio/best",
            "label": "最佳画质（自动）",
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
            # 无 ffmpeg 时无法合流，跳过纯视频轨
            continue
        fmt_id = f["format_id"]
        selector = fmt_id if has_audio else f"{fmt_id}+bestaudio/best"
        ext = "mp4" if needs_merge else (f.get("ext") or "mp4")
        options.append({
            "id": selector,
            "label": f"{height}P" + ("" if has_audio else " (合流)"),
            "ext": ext,
            "height": height,
            "filesize": _human_size(f.get("filesize") or f.get("filesize_approx")),
            "needs_merge": needs_merge,
            "recommended": False,
        })

    # 若没有任何带高度的格式（部分平台），退回 best
    if not options:
        options.append({
            "id": "best",
            "label": "默认画质",
            "ext": "mp4",
            "height": 0,
            "filesize": None,
            "needs_merge": False,
            "recommended": True,
        })

    # 仅音频
    options.append({
        "id": "audio-mp3" if ffmpeg else "bestaudio/best",
        "label": "仅音频 MP3" if ffmpeg else "仅音频",
        "ext": "mp3" if ffmpeg else "m4a",
        "height": -1,
        "filesize": None,
        "needs_merge": False,
        "recommended": False,
        "audio_only": True,
    })

    return options


# ---------------------------------------------------------------------------
# 下载
# ---------------------------------------------------------------------------

def download(url: str, format_id: str) -> Path:
    """下载到临时目录，返回文件路径。format_id 可为格式选择器。"""
    job_dir = settings.download_dir / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
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

    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)

    files = [p for p in job_dir.iterdir() if p.is_file()]
    if not files:
        raise RuntimeError("下载失败：未生成文件")
    # 取体积最大的文件（合流后主文件）
    return max(files, key=lambda p: p.stat().st_size)


# ---------------------------------------------------------------------------
# 字幕
# ---------------------------------------------------------------------------

_PREFERRED_LANGS = ["zh-Hans", "zh-CN", "zh", "en", "en-US"]


def fetch_subtitle(url: str, prefer_langs: Optional[list[str]] = None) -> dict:
    """获取字幕（优先人工字幕，其次自动字幕）。

    返回 {lang, cues:[{start,end,text}], plain_text}
    """
    prefer = (prefer_langs or []) + _PREFERRED_LANGS

    with YoutubeDL(_base_opts()) as ydl:
        info = ydl.extract_info(url, download=False)

        subtitles = info.get("subtitles") or {}
        auto_caps = info.get("automatic_captions") or {}

        chosen_lang, tracks, is_auto = _choose_track(subtitles, auto_caps, prefer)
        if not tracks:
            raise ValueError("该视频没有可用字幕（人工或自动均无），无法进行总结/翻译。")

        # 优先 vtt 格式
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
