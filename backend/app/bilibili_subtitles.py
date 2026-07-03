"""Cookie-free Bilibili subtitle probes.

This module only uses public webpage/player APIs plus anonymous device cookies
issued by Bilibili itself. Authenticated cookie fallback stays in the yt-dlp
wrapper so subtitle detection can remain cookie-free whenever Bilibili exposes
real subtitle tracks publicly.
"""
from __future__ import annotations

import http.cookiejar
import json
import re
from urllib.parse import quote, unquote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_SUBTITLE_API = "https://api.bilibili.com/x/v2/subtitle/web/view"
_SUBTITLE_DECODE_KEYS = (
    (
        'nP](wOFRvU.+<fjS{jn-!$D|Dz&",zT`',
        "=CFxYRn{.y|uVyO$uh&sikph?N.ilF/`",
    ),
    (
        'Bn"q~|albg@]Go~ACgyDvKnd+)_D}^&J?',
        "Cu~L!xs~f^&r@'vh=q]q{eeng*sEg^kp#J",
    ),
)
_LANG_RE = re.compile(r"^(?:[a-z]{2,3})(?:-[A-Za-z]{2,4})?$")


def _headers(referer: str, accept: str = "application/json, text/plain, */*") -> dict:
    return {
        "Referer": referer,
        "Origin": "https://www.bilibili.com",
        "User-Agent": _BROWSER_UA,
        "Accept": accept,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def _anonymous_opener(referer: str):
    """Return an opener seeded with Bilibili's anonymous buvid cookies."""
    cookie_jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    for url in (
        "https://www.bilibili.com",
        referer,
        "https://api.bilibili.com/x/frontend/finger/spi",
    ):
        try:
            request = Request(url, headers=_headers(referer, "*/*"))
            opener.open(request, timeout=20).read()
        except Exception:
            # Best-effort only; subtitle APIs often work without every seed hit.
            pass
    return opener


def _fetch_bytes(api_url: str, referer: str, opener=None, accept: str = "*/*") -> bytes:
    request = Request(api_url, headers=_headers(referer, accept))
    if opener is None:
        with urlopen(request, timeout=20) as response:
            return response.read()
    with opener.open(request, timeout=20) as response:
        return response.read()


def _fetch_json(api_url: str, referer: str) -> dict:
    raw = _fetch_bytes(api_url, referer, accept="application/json, text/plain, */*")
    return json.loads(raw.decode("utf-8", errors="ignore"))


def _subtitle_tracks_from_player(aid: int | str, cid: int | str, referer: str) -> list[dict]:
    query = urlencode({"aid": aid, "cid": cid})
    tracks: list[dict] = []
    for endpoint in (
        f"https://api.bilibili.com/x/player/v2?{query}",
        f"https://api.bilibili.com/x/player/wbi/v2?{query}",
    ):
        player = _fetch_json(endpoint, referer)
        subtitle_data = ((player.get("data") or {}).get("subtitle") or {})
        tracks = subtitle_data.get("subtitles") or []
        if tracks:
            break
    return tracks


def _read_varint(buf: bytes, index: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while index < len(buf):
        byte = buf[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, index
        shift += 7
    raise ValueError("incomplete protobuf varint")


def _protobuf_strings(buf: bytes, *, depth: int = 0) -> list[str]:
    """Extract UTF-8 length-delimited fields from Bilibili's protobuf response."""
    strings: list[str] = []
    index = 0
    while index < len(buf):
        try:
            key, index = _read_varint(buf, index)
        except ValueError:
            break
        if not key:
            break

        wire_type = key & 7
        if wire_type == 0:
            try:
                _, index = _read_varint(buf, index)
            except ValueError:
                break
        elif wire_type == 1:
            index += 8
        elif wire_type == 5:
            index += 4
        elif wire_type == 2:
            try:
                length, index = _read_varint(buf, index)
            except ValueError:
                break
            chunk = buf[index:index + length]
            index += length
            try:
                strings.append(chunk.decode("utf-8"))
            except UnicodeDecodeError:
                pass
            if depth < 5 and chunk:
                strings.extend(_protobuf_strings(chunk, depth=depth + 1))
        else:
            break
    return strings


def _xor_chars(value: str, key: str) -> str:
    return "".join(chr(ord(ch) ^ ord(key[index % len(key)])) for index, ch in enumerate(value))


def _decode_subtitle_url(url: str) -> str:
    """Decode Bilibili's encrypted subtitle.bilibili.com URL."""
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url

    parts = urlsplit(url)
    encrypted_path = parts.path.lstrip("/")
    for prefix, key_part in _SUBTITLE_DECODE_KEYS:
        decoded = _xor_chars(unquote(encrypted_path), key_part + "bilibili")
        if decoded.startswith(prefix):
            path = decoded[len(prefix):]
            return urlunsplit((
                "https",
                "aisubtitle.hdslb.com",
                quote(path, safe="/%"),
                parts.query,
                "",
            ))
    return url


def _subtitle_tracks_from_web_view(
    aid: int | str,
    cid: int | str,
    referer: str,
    opener,
) -> list[dict]:
    query = urlencode({
        "oid": cid,
        "pid": aid,
        "context_ext": json.dumps({"video_type": 1}, separators=(",", ":")),
        "type": 1,
        "cur_production_type": 0,
    })
    raw = _fetch_bytes(f"{_SUBTITLE_API}?{query}", referer, opener)
    strings = _protobuf_strings(raw)

    tracks: list[dict] = []
    for index, value in enumerate(strings):
        if not value.startswith("//subtitle.bilibili.com/"):
            continue
        previous = [item for item in strings[max(0, index - 4):index] if len(item) <= 16]
        lang = next((item for item in reversed(previous) if _LANG_RE.match(item)), "zh")
        label = next((item for item in reversed(previous) if item != lang and not item.isdigit()), lang)
        tracks.append({
            "lan": lang,
            "lan_doc": label,
            "subtitle_url": _decode_subtitle_url(value),
            "ai_type": lang.startswith("ai-"),
        })
    return tracks


def _video_ids(bvid: str) -> tuple[int | str | None, int | str | None, str]:
    referer = f"https://www.bilibili.com/video/{bvid}/"
    view = _fetch_json(
        f"https://api.bilibili.com/x/web-interface/view?{urlencode({'bvid': bvid})}",
        referer,
    )
    video = view.get("data") or {}
    aid = video.get("aid")
    cid = video.get("cid") or ((video.get("pages") or [{}])[0].get("cid"))
    return aid, cid, referer


def _public_tracks(bvid: str) -> tuple[list[dict], str, object | None]:
    if not bvid:
        return [], "", None

    aid, cid, referer = _video_ids(bvid)
    if not aid or not cid:
        return [], referer, None

    opener = _anonymous_opener(referer)
    tracks = _subtitle_tracks_from_web_view(aid, cid, referer, opener)
    if not tracks:
        tracks = _subtitle_tracks_from_player(aid, cid, referer)
    return tracks, referer, opener


def _lang_base(code: str) -> str:
    return (code or "").split("-", 1)[0].lower()


def _lang_matches(preferred: str, available: str) -> bool:
    if preferred == available:
        return True
    pref_base = _lang_base(preferred)
    avail_base = _lang_base(available)
    if pref_base == avail_base:
        return True
    if pref_base == "zh" and (avail_base == "zh" or available == "ai-zh"):
        return True
    return False


def _choose_track(tracks: list[dict], prefer: list[str]) -> dict | None:
    if not tracks:
        return None
    by_lang = {str(t.get("lan") or t.get("lang") or t.get("id")): t for t in tracks}
    for lang in prefer:
        for available, track in by_lang.items():
            if _lang_matches(lang, available):
                return track
    for available, track in by_lang.items():
        if available in {"zh", "zh-CN", "zh-Hans", "ai-zh"}:
            return track
    return tracks[0]


def public_subtitle_langs(bvid: str) -> list[str]:
    """Return publicly exposed real subtitle languages for a Bilibili BV id.

    Danmaku is intentionally ignored; only entries with subtitle_url count as
    transcript-grade subtitle tracks.
    """
    langs: set[str] = set()
    tracks, _referer, _opener = _public_tracks(bvid)
    for track in tracks:
        lang = track.get("lan") or track.get("lang") or track.get("id")
        subtitle_url = track.get("subtitle_url") or track.get("url")
        if lang and subtitle_url:
            langs.add(str(lang))
    return sorted(langs)


def public_subtitle(bvid: str, prefer_langs: list[str] | None = None) -> dict | None:
    """Return public Bilibili subtitle content for a BV id, or None if absent."""
    tracks, referer, opener = _public_tracks(bvid)
    track = _choose_track(tracks, prefer_langs or [])
    if not track:
        return None

    subtitle_url = track.get("subtitle_url") or track.get("url")
    if not subtitle_url:
        return None
    if subtitle_url.startswith("//subtitle.bilibili.com/"):
        subtitle_url = _decode_subtitle_url(subtitle_url)
    elif subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url

    content = _fetch_bytes(str(subtitle_url), referer, opener).decode("utf-8", errors="ignore")
    lang = str(track.get("lan") or track.get("lang") or track.get("id") or "")
    return {
        "lang": lang,
        "is_auto": bool(track.get("ai_type") or lang.startswith("ai-")),
        "content": content,
    }
