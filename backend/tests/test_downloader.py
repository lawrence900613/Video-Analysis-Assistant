"""Offline unit tests: pure functions only, no network or downloads.

Run:
    cd backend
    pip install -r requirements.txt pytest
    pytest -q
"""
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


def test_parse_vtt():
    cues = dl._parse_vtt(VTT_SAMPLE)
    # Third cue duplicates the first and is deduplicated
    assert len(cues) == 2
    assert cues[0]["start"] == "00:00:00,000"
    assert cues[0]["end"] == "00:00:02,000"
    assert cues[0]["text"] == "Hello world"
    # HTML tags are stripped
    assert cues[1]["text"] == "Second line"


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
