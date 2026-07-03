"""Transcript utilities: cue enrichment, chunking, and chapter time alignment."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_TS_RE = re.compile(
    r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})(?:[.,](\d{1,3}))?$"
)


def ts_to_sec(ts: str) -> float:
    """Convert SRT/VTT timestamp to seconds."""
    ts = ts.strip().replace(".", ",")
    m = _TS_RE.match(ts)
    if not m:
        return 0.0
    h = int(m.group(1) or 0)
    mi = int(m.group(2))
    s = int(m.group(3))
    ms = int((m.group(4) or "0").ljust(3, "0")[:3])
    return h * 3600 + mi * 60 + s + ms / 1000.0


def sec_to_label(sec: float) -> str:
    """Format seconds as mm:ss or hh:mm:ss."""
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def enrich_cues(cues: list[dict]) -> list[dict]:
    """Add index, start_sec, end_sec to each cue."""
    out = []
    for i, c in enumerate(cues):
        start_sec = ts_to_sec(c["start"])
        end_sec = ts_to_sec(c["end"])
        out.append({
            "index": i,
            "start": c["start"],
            "end": c["end"],
            "start_sec": start_sec,
            "end_sec": end_sec if end_sec > start_sec else start_sec + 0.5,
            "text": c["text"],
        })
    return out


def format_cues_with_timestamps(cues: list[dict]) -> str:
    """Render transcript cues with labels so LLM citations can map to real times."""
    lines: list[str] = []
    for cue in cues:
        start_sec = cue.get("start_sec", ts_to_sec(cue["start"]))
        text = (cue.get("text") or "").strip()
        if text:
            lines.append(f"[{sec_to_label(start_sec)}] {text}")
    return "\n".join(lines)


def build_transcript(
    *,
    title: str,
    url: str,
    lang: str,
    is_auto: bool,
    cues: list[dict],
    plain_text: str,
    duration_sec: Optional[float] = None,
    source: str = "subtitle",
    max_chars: Optional[int] = None,
) -> dict:
    """Build a Transcript dict with enriched cues."""
    enriched = enrich_cues(cues)
    truncated = False
    if max_chars and len(plain_text) > max_chars:
        plain_text = plain_text[:max_chars]
        truncated = True
    return {
        "title": title,
        "url": url,
        "lang": lang,
        "is_auto": is_auto,
        "duration_sec": duration_sec,
        "source": source,
        "cues": enriched,
        "plain_text": plain_text,
        "char_count": len(plain_text),
        "truncated": truncated,
    }


@dataclass
class TranscriptChunk:
    chunk_index: int
    start_sec: float
    end_sec: float
    text: str
    cue_range: tuple[int, int]


def chunk_transcript(
    cues: list[dict],
    max_chars: int = 6000,
    overlap_cues: int = 2,
    include_timestamps: bool = False,
) -> list[TranscriptChunk]:
    """Split cues into overlapping chunks by character budget."""
    if not cues:
        return []

    chunks: list[TranscriptChunk] = []
    start_idx = 0
    chunk_index = 0

    while start_idx < len(cues):
        end_idx = start_idx
        char_count = 0
        while end_idx < len(cues):
            if include_timestamps:
                line = f"[{sec_to_label(cues[end_idx].get('start_sec', ts_to_sec(cues[end_idx]['start'])))}] {cues[end_idx]['text']}"
            else:
                line = cues[end_idx]["text"]
            line_len = len(line) + 1
            if char_count + line_len > max_chars and end_idx > start_idx:
                break
            char_count += line_len
            end_idx += 1

        if end_idx == start_idx:
            end_idx = start_idx + 1

        text = format_cues_with_timestamps(cues[start_idx:end_idx]) if include_timestamps else "\n".join(
            c["text"] for c in cues[start_idx:end_idx]
        )
        chunks.append(TranscriptChunk(
            chunk_index=chunk_index,
            start_sec=cues[start_idx].get("start_sec", ts_to_sec(cues[start_idx]["start"])),
            end_sec=cues[end_idx - 1].get("end_sec", ts_to_sec(cues[end_idx - 1]["end"])),
            text=text,
            cue_range=(start_idx, end_idx - 1),
        ))
        chunk_index += 1

        if end_idx >= len(cues):
            break
        start_idx = max(start_idx + 1, end_idx - overlap_cues)

    return chunks


def _parse_time_label(label: str) -> Optional[float]:
    """Parse mm:ss or hh:mm:ss label to seconds."""
    if not label:
        return None
    label = label.strip()
    parts = label.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
    return None


_TITLE_TS_RE = re.compile(
    r"(?:^|\s)(?:(\d{1,2}):(\d{2})(?::(\d{2}))?)\s*(?:[-–—]|$|\s)",
)


def _extract_time_from_title(title: str) -> Optional[str]:
    """Pull an embedded timestamp from a chapter title, e.g. '3:24 - Intro'."""
    m = _TITLE_TS_RE.search(title or "")
    if not m:
        return None
    if m.group(3) is not None:
        return f"{int(m.group(1))}:{m.group(2)}:{m.group(3)}"
    return f"{int(m.group(1))}:{m.group(2)}"


def _chapter_label(ch: dict) -> str:
    label = (ch.get("start_label") or ch.get("start_time") or "").strip()
    if label:
        return label
    return _extract_time_from_title(ch.get("title", "")) or ""


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\w+", text or "") if len(w) > 2}


def _text_match_score(query: str, cue_text: str) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    c_tokens = _tokenize(cue_text)
    if not c_tokens:
        return 0.0
    return len(q_tokens & c_tokens) / len(q_tokens)


def _snap_to_cue(cue_starts: list[float], target: float, min_sec: float = 0.0) -> float:
    """Snap target to the nearest cue at or after min_sec."""
    if not cue_starts:
        return max(target, min_sec)
    candidates = [s for s in cue_starts if s >= min_sec - 0.5]
    if not candidates:
        candidates = cue_starts
    return min(candidates, key=lambda s: abs(s - target))


def _even_cue_indices(num_chapters: int, num_cues: int) -> list[int]:
    """Pick evenly spaced cue indices spanning the full transcript."""
    if num_chapters <= 0 or num_cues <= 0:
        return []
    if num_chapters == 1:
        return [0]
    last = num_cues - 1
    return [
        min(round(i * last / (num_chapters - 1)), last)
        for i in range(num_chapters)
    ]


def _labels_are_distinct(chapters: list[dict]) -> bool:
    """True when parsed LLM labels look usable (present, unique, non-decreasing)."""
    parsed: list[float] = []
    for ch in chapters:
        label = _chapter_label(ch)
        sec = _parse_time_label(label) if label else None
        if sec is None:
            return False
        parsed.append(sec)
    if len(set(parsed)) < len(parsed):
        return False
    return all(parsed[i] <= parsed[i + 1] for i in range(len(parsed) - 1))


def _find_cue_by_text(
    cues: list[dict],
    chapter: dict,
    search_from: int = 0,
) -> Optional[int]:
    """Fuzzy-match chapter title/summary to transcript cue text."""
    query = f"{chapter.get('title', '')} {chapter.get('summary', '')}".strip()
    if not query:
        return None

    best_idx: Optional[int] = None
    best_score = 0.0
    for i in range(search_from, len(cues)):
        score = _text_match_score(query, cues[i].get("text", ""))
        if score > best_score:
            best_score = score
            best_idx = i
    if best_idx is not None and best_score >= 0.15:
        return best_idx
    return None


def align_chapter_times(
    cues: list[dict],
    chapters: list[dict],
    duration_sec: Optional[float] = None,
) -> list[dict]:
    """Map chapter titles/labels to distinct cue timestamps."""
    if not chapters:
        return []

    cue_starts = [
        c.get("start_sec", ts_to_sec(c["start"])) for c in cues
    ] if cues else []

    n = len(chapters)
    use_llm_labels = bool(cue_starts) and _labels_are_distinct(chapters)
    spread_indices = _even_cue_indices(n, len(cue_starts)) if cue_starts else []
    resolved_starts: list[float] = []
    min_sec = 0.0
    search_from = 0

    for i, ch in enumerate(chapters):
        start_sec: Optional[float] = None

        if use_llm_labels:
            label = _chapter_label(ch)
            parsed = _parse_time_label(label)
            if parsed is not None:
                start_sec = _snap_to_cue(cue_starts, parsed, min_sec)

        if start_sec is None and cues:
            matched = _find_cue_by_text(cues, ch, search_from)
            if matched is not None:
                start_sec = cue_starts[matched]
                search_from = matched + 1

        if start_sec is None and spread_indices:
            start_sec = cue_starts[spread_indices[i]]

        if start_sec is None:
            if duration_sec and n > 1:
                start_sec = (duration_sec * i) / (n - 1)
            else:
                start_sec = float(i * 60)

        if resolved_starts and start_sec <= resolved_starts[-1]:
            if spread_indices:
                start_sec = max(start_sec, cue_starts[spread_indices[i]])
            if start_sec <= resolved_starts[-1]:
                start_sec = resolved_starts[-1] + 30.0

        if cue_starts:
            start_sec = _snap_to_cue(cue_starts, start_sec, min_sec)

        resolved_starts.append(start_sec)
        min_sec = start_sec + 1.0

    aligned = []
    for i, ch in enumerate(chapters):
        start_sec = resolved_starts[i]
        if i + 1 < n:
            end_sec = resolved_starts[i + 1]
        elif duration_sec is not None:
            end_sec = duration_sec
        elif cue_starts:
            end_sec = cue_starts[-1]
        else:
            end_sec = start_sec + 60

        if end_sec <= start_sec:
            end_sec = start_sec + 30

        aligned.append({
            "title": ch.get("title", f"Chapter {i + 1}"),
            "summary": ch.get("summary", ""),
            "start_sec": start_sec,
            "end_sec": end_sec,
            "start_label": sec_to_label(start_sec),
            "end_label": sec_to_label(end_sec),
        })

    return aligned


def retrieve_chunks(
    cues: list[dict],
    query: str,
    *,
    top_k: int = 5,
    chunk_max_chars: int = 6000,
) -> list[TranscriptChunk]:
    """Keyword overlap retrieval over transcript chunks for Q&A context."""
    if not cues or not (query or "").strip():
        return []

    chunks = chunk_transcript(cues, max_chars=chunk_max_chars)
    if not chunks:
        return []

    q_tokens = _tokenize(query)
    if not q_tokens:
        return chunks[:top_k]

    scored: list[tuple[float, TranscriptChunk]] = []
    for chunk in chunks:
        score = _text_match_score(query, chunk.text)
        if score > 0:
            scored.append((score, chunk))

    if not scored:
        return chunks[:top_k]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def select_relevant_cues(cues: list[dict], query: str, *, top_k: int = 3) -> list[dict]:
    """Pick individual cues that best match a question/answer text."""
    if not cues or not (query or "").strip():
        return []

    scored: list[tuple[float, int, dict]] = []
    for i, cue in enumerate(cues):
        score = _text_match_score(query, cue.get("text", ""))
        if score > 0:
            scored.append((score, i, cue))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [cue for _, _, cue in scored[:top_k]]
