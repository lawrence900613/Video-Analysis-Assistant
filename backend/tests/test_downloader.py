"""Offline unit tests: pure functions only, no network or downloads.

Run:
    cd backend
    pip install -r requirements.txt pytest
    pytest -q
"""
from urllib.error import HTTPError

from app import downloader as dl


# ---------------------------------------------------------------------------
# Duration / size formatting
# ---------------------------------------------------------------------------

def test_format_duration():
    assert dl._format_duration(None) is None
    assert dl._format_duration(0) is None
    assert dl._format_duration(65) == "1:05"
    assert dl._format_duration(3725) == "1:02:05"


def test_human_size():
    assert dl._human_size(None) is None
    assert dl._human_size(0) is None
    assert dl._human_size(512) == "512.0B"
    assert dl._human_size(1536) == "1.5KB"
    assert dl._human_size(5 * 1024 * 1024) == "5.0MB"


# ---------------------------------------------------------------------------
# VTT parsing + SRT export
# ---------------------------------------------------------------------------

VTT_SAMPLE = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.500
<c>Second</c> line

00:00:04.500 --> 00:00:06.000
Hello world
"""

VTT_ROLLING = """WEBVTT

00:00:19.000 --> 00:00:22.000
it sucks when...

00:00:19.000 --> 00:00:22.000
it sucks when... real visualization, right? You hear the

00:00:22.000 --> 00:00:24.000
real visualization, right? You hear the

00:00:22.000 --> 00:00:28.000
real visualization, right? You hear the next part here
"""

VTT_ENTITIES = """WEBVTT

00:00:00.000 --> 00:00:02.000
&gt;&gt; Hello &amp; welcome
"""


def test_parse_vtt():
    cues = dl._parse_vtt(VTT_SAMPLE)
    assert len(cues) == 3
    assert cues[0]["start"] == "00:00:00,000"
    assert cues[0]["end"] == "00:00:02,000"
    assert cues[0]["text"] == "Hello world"
    assert cues[1]["text"] == "Second line"
    assert cues[2]["text"] == "Hello world"


def test_parse_vtt_rolling_overlap_deduped():
    cues = dl._parse_vtt(VTT_ROLLING)
    assert len(cues) == 2
    assert cues[0]["text"] == "it sucks when... real visualization, right? You hear the"
    assert cues[0]["start"] == "00:00:19,000"
    assert cues[1]["text"] == "real visualization, right? You hear the next part here"
    assert cues[1]["start"] == "00:00:22,000"


def test_parse_vtt_decodes_html_entities():
    cues = dl._parse_vtt(VTT_ENTITIES)
    assert len(cues) == 1
    assert cues[0]["text"] == ">> Hello & welcome"


def test_dedupe_overlapping_cues():
    cues = [
        {"start": "00:00:19,000", "end": "00:00:22,000", "text": "alpha beta"},
        {"start": "00:00:22,000", "end": "00:00:24,000", "text": "beta"},
        {"start": "00:00:24,000", "end": "00:00:26,000", "text": "gamma"},
    ]
    deduped = dl._dedupe_overlapping_cues(cues)
    assert len(deduped) == 2
    assert deduped[0]["text"] == "alpha beta"
    assert deduped[1]["text"] == "gamma"


def test_norm_ts_short_form():
    # MM:SS.mmm should be normalized to HH:MM:SS,mmm
    assert dl._norm_ts("01:02.500") == "00:01:02,500"
    assert dl._norm_ts("00:00:01.000") == "00:00:01,000"


def test_cues_to_srt():
    cues = [
        {"start": "00:00:00,000", "end": "00:00:02,000", "text": "A"},
        {"start": "00:00:02,000", "end": "00:00:04,000", "text": "B"},
    ]
    srt = dl.cues_to_srt(cues)
    lines = srt.splitlines()
    assert lines[0] == "1"
    assert lines[1] == "00:00:00,000 --> 00:00:02,000"
    assert lines[2] == "A"
    assert "2" in lines
    assert "B" in lines


def test_parse_json3():
    content = (
        '{"events":[{"tStartMs":0,"dDurationMs":1500,"segs":[{"utf8":"Hi "},{"utf8":"there"}]},'
        '{"tStartMs":1500,"dDurationMs":1000,"segs":[{"utf8":"\\n"}]}]}'
    )
    cues = dl._parse_json3(content)
    assert len(cues) == 1  # second event is newline-only and filtered out
    assert cues[0]["text"] == "Hi there"
    assert cues[0]["start"] == "00:00:00,000"
    assert cues[0]["end"] == "00:00:01,500"


def test_parse_json3_rolling_overlap_deduped():
    content = (
        '{"events":['
        '{"tStartMs":19000,"dDurationMs":3000,"segs":[{"utf8":"short "}]},'
        '{"tStartMs":19000,"dDurationMs":3000,"segs":[{"utf8":"short extended text"}]},'
        '{"tStartMs":22000,"dDurationMs":2000,"segs":[{"utf8":"extended text"}]},'
        '{"tStartMs":22000,"dDurationMs":6000,"segs":[{"utf8":"extended text and more"}]}'
        "]}"
    )
    cues = dl._parse_json3(content)
    assert len(cues) == 2
    assert cues[0]["text"] == "short extended text"
    assert cues[1]["text"] == "extended text and more"


def test_parse_bilibili_subtitle_json():
    content = (
        '{"body":['
        '{"from":0.12,"to":2.5,"content":"你好 &amp; welcome"},'
        '{"from":2.5,"to":4,"content":"第二句"}'
        "]}"
    )
    cues = dl._parse_bilibili_subtitle_json(content)
    assert len(cues) == 2
    assert cues[0]["start"] == "00:00:00,120"
    assert cues[0]["end"] == "00:00:02,500"
    assert cues[0]["text"] == "你好 & welcome"
    assert cues[1]["text"] == "第二句"


# ---------------------------------------------------------------------------
# Subtitle track selection (manual first, then auto; language priority)
# ---------------------------------------------------------------------------

def test_choose_track_prefers_manual():
    subs = {"en": [{"url": "u1", "ext": "vtt"}]}
    auto = {"zh-Hans": [{"url": "u2", "ext": "vtt"}]}
    lang, tracks, is_auto = dl._choose_track(subs, auto, ["zh-Hans", "en"])
    assert lang == "en"
    assert is_auto is False


def test_choose_track_language_priority():
    subs = {"en": [{"url": "u1"}], "zh-Hans": [{"url": "u2"}]}
    lang, _tracks, is_auto = dl._choose_track(subs, {}, ["zh-Hans", "en"])
    assert lang == "zh-Hans"
    assert is_auto is False


def test_choose_track_falls_back_to_auto():
    auto = {"fr": [{"url": "u3"}]}
    lang, tracks, is_auto = dl._choose_track({}, auto, ["zh-Hans", "en"])
    assert lang == "fr"
    assert is_auto is True
    assert tracks


def test_choose_track_none():
    lang, tracks, is_auto = dl._choose_track({}, {}, ["en"])
    assert lang is None
    assert tracks == []


def test_choose_track_skips_danmaku():
    subs = {
        "danmaku": [{"url": "u-dm", "ext": "xml"}],
        "zh-CN": [{"url": "u-zh", "ext": "srt", "data": "1\n00:00:00,000 --> 00:00:02,000\n你好"}],
    }
    lang, tracks, is_auto = dl._choose_track(subs, {}, ["zh-Hans"])
    assert lang == "zh-CN"
    assert is_auto is False


def test_collect_subtitle_langs_excludes_danmaku():
    subs = {"danmaku": [{}], "zh-CN": [{}], "en": [{}]}
    langs = dl._collect_subtitle_langs(subs, {})
    assert langs == ["en", "zh-CN"]


def test_format_parse_result_bilibili_uncertain():
    info = {
        "id": "BVtest",
        "title": "Test",
        "extractor_key": "BiliBili",
        "subtitles": {"danmaku": [{"ext": "xml", "url": "https://example.com/dm.xml"}]},
        "formats": [],
    }
    result = dl.format_parse_result(info, "https://www.bilibili.com/video/BVtest/")
    assert result["has_subtitles"] is False
    assert result["subtitle_uncertain"] is True
    assert result["subtitle_requires_cookies"] is True
    assert result["subtitle_langs"] == []


def test_format_parse_result_bilibili_with_cc():
    info = {
        "id": "BVtest",
        "title": "Test",
        "extractor_key": "BiliBili",
        "subtitles": {
            "danmaku": [{"ext": "xml", "url": "https://example.com/dm.xml"}],
            "zh-CN": [{"ext": "srt", "data": "1\n00:00:00,000 --> 00:00:02,000\n你好"}],
        },
        "formats": [],
    }
    result = dl.format_parse_result(info, "https://www.bilibili.com/video/BVtest/")
    assert result["has_subtitles"] is True
    assert result["subtitle_uncertain"] is False
    assert result["subtitle_langs"] == ["zh-CN"]


def test_parse_bilibili_uses_public_subtitle_probe(monkeypatch):
    raw_info = {
        "id": "BVtest",
        "title": "Test",
        "extractor_key": "BiliBili",
        "subtitles": {"danmaku": [{"ext": "xml", "url": "https://example.com/dm.xml"}]},
        "formats": [],
    }
    monkeypatch.setattr(dl, "extract_info", lambda url, probe_subtitles=False: raw_info)
    monkeypatch.setattr(dl.bilibili_subtitles, "public_subtitle_langs", lambda bvid: ["zh-CN"])

    result = dl.parse("https://www.bilibili.com/video/BVtest/")

    assert result["has_subtitles"] is True
    assert result["subtitle_uncertain"] is False
    assert result["subtitle_requires_cookies"] is False
    assert result["subtitle_langs"] == ["zh-CN"]


def test_parse_srt():
    content = "1\n00:00:00,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,000 --> 00:00:04,000\nWorld"
    cues = dl._parse_srt(content)
    assert len(cues) == 2
    assert cues[0]["text"] == "Hello"
    assert cues[1]["text"] == "World"


def test_read_track_content_inline_data():
    track = {"data": "1\n00:00:00,000 --> 00:00:02,000\nInline"}
    content, err = dl._read_track_content(track, None, "https://example.com", "zh-CN", False)
    assert err is None
    assert "Inline" in content


def test_is_bilibili_url():
    assert dl._is_bilibili_url("https://www.bilibili.com/video/BV1xx/")
    assert not dl._is_bilibili_url("https://www.youtube.com/watch?v=abc")


def test_normalize_bilibili_adds_www():
    assert (
        dl.normalize_url("https://bilibili.com/video/BV1xx/?spm_id_from=333.788")
        == "https://www.bilibili.com/video/BV1xx/"
    )


def test_decode_bilibili_subtitle_url():
    prefix, key_part = dl.bilibili_subtitles._SUBTITLE_DECODE_KEYS[0]
    decoded_path = "/bfs/ai_subtitle/test.json"
    encrypted = dl.bilibili_subtitles._xor_chars(
        prefix + decoded_path,
        key_part + "bilibili",
    )
    url = (
        "//subtitle.bilibili.com/"
        + dl.bilibili_subtitles.quote(encrypted, safe="")
        + "?auth_key=abc"
    )

    assert dl.bilibili_subtitles._decode_subtitle_url(url) == (
        "https://aisubtitle.hdslb.com/bfs/ai_subtitle/test.json?auth_key=abc"
    )


def test_choose_track_prefers_en_over_aa():
    auto = {
        "aa": [{"url": "u-aa", "ext": "vtt"}],
        "en": [{"url": "u-en", "ext": "vtt"}],
    }
    lang, tracks, is_auto = dl._choose_track({}, auto, ["zh-Hans", "en"])
    assert lang == "en"
    assert is_auto is True
    assert tracks[0]["url"] == "u-en"


def test_choose_track_matches_en_gb():
    auto = {"en-GB": [{"url": "u-gb", "ext": "vtt"}]}
    lang, tracks, is_auto = dl._choose_track({}, auto, ["en"])
    assert lang == "en-GB"
    assert is_auto is True


def test_is_rate_limit_error():
    assert dl._is_rate_limit_error(HTTPError("url", 429, "Too Many Requests", {}, None))
    assert dl._is_rate_limit_error(dl.SubtitleRateLimitError("429"))
    assert not dl._is_rate_limit_error(ValueError("nope"))


def test_track_candidates_try_compatible_chinese_before_english():
    auto = {
        "en": [{"url": "u-en", "ext": "json3"}],
        "zh-CN": [{"url": "u-zh-cn", "ext": "json3"}],
        "zh-Hans": [{"url": "u-zh-hans", "ext": "json3"}],
    }

    candidates = dl._track_candidates({}, auto, ["zh-Hans", "zh-CN", "zh", "zh-Hant", "en"])

    assert [(lang, is_auto) for lang, _tracks, is_auto in candidates[:3]] == [
        ("zh-Hans", True),
        ("zh-CN", True),
        ("en", True),
    ]


def test_fetch_subtitle_falls_back_after_youtube_zh_hans_429(monkeypatch):
    class _Response:
        def __init__(self, text: str):
            self._text = text

        def read(self):
            return self._text.encode("utf-8")

    class _FakeYDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return False

        def urlopen(self, request):
            url = getattr(request, "full_url", str(request))
            if url == "https://youtube.test/zh-Hans":
                raise HTTPError(url, 429, "Too Many Requests", {}, None)
            return _Response(
                '{"events":[{"tStartMs":0,"dDurationMs":1000,"segs":[{"utf8":"你好"}]}]}'
            )

    info = {
        "id": "yt-test",
        "title": "YT Test",
        "extractor_key": "Youtube",
        "subtitles": {},
        "automatic_captions": {
            "zh-Hans": [{"url": "https://youtube.test/zh-Hans", "ext": "json3"}],
            "zh-CN": [{"url": "https://youtube.test/zh-CN", "ext": "json3"}],
        },
    }

    monkeypatch.setattr(dl, "YoutubeDL", _FakeYDL)
    monkeypatch.setattr(dl.time, "sleep", lambda _seconds: None)

    sub = dl.fetch_subtitle("https://www.youtube.com/watch?v=test", ["zh-Hans"], info=info)

    assert sub["lang"] == "zh-CN"
    assert sub["plain_text"] == "你好"


# ---------------------------------------------------------------------------
# Quality option building (with / without ffmpeg)
# ---------------------------------------------------------------------------

INFO = {
    "formats": [
        {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "ext": "mp4", "tbr": 500, "filesize": 1000},
        {"format_id": "137", "vcodec": "avc1", "acodec": "none", "height": 1080, "ext": "mp4", "tbr": 2000, "filesize": 5000},
        {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "ext": "m4a", "tbr": 128},
    ]
}


def test_build_quality_options_with_ffmpeg(monkeypatch):
    monkeypatch.setattr(dl, "has_ffmpeg", lambda: True)
    opts = dl._build_quality_options(INFO)
    ids = [o["id"] for o in opts]

    assert "bestvideo+bestaudio/best" in ids           # best quality auto merge
    assert "137+bestaudio/best" in ids                 # 1080p video-only needs merge
    assert "18" in ids                                 # 360p progressive direct download
    assert any(o.get("audio_only") for o in opts)      # audio-only option

    o1080 = next(o for o in opts if o["height"] == 1080)
    assert o1080["needs_merge"] is True
    o360 = next(o for o in opts if o["height"] == 360)
    assert o360["needs_merge"] is False

    audio = next(o for o in opts if o.get("audio_only"))
    assert audio["id"] == "audio-mp3"
    assert audio["ext"] == "mp3"


def test_build_quality_options_without_ffmpeg(monkeypatch):
    monkeypatch.setattr(dl, "has_ffmpeg", lambda: False)
    opts = dl._build_quality_options(INFO)
    ids = [o["id"] for o in opts]

    assert "bestvideo+bestaudio/best" not in ids       # no auto merge without ffmpeg
    assert "137+bestaudio/best" not in ids             # video-only tracks skipped
    assert "18" in ids                                 # progressive still available

    audio = next(o for o in opts if o.get("audio_only"))
    assert audio["id"] == "bestaudio/best"             # falls back to native audio
    assert audio["ext"] == "m4a"
