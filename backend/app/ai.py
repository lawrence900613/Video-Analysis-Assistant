"""LLM features: video summarization and subtitle translation (OpenAI-compatible API)."""
from __future__ import annotations

import json
import re
from typing import Iterator

from openai import OpenAI

from .config import get_settings
from .transcript_utils import ts_to_sec

settings = get_settings()

_MARKDOWN_FORMAT = (
    "Output Markdown with this structure:\n"
    "# TL;DR\n(one sentence overview)\n\n"
    "## Key Points\n- point 1\n- point 2\n(3-6 bullets)\n\n"
    "## [mm:ss] Chapter Title\n(1-2 sentence summary)\n"
    "(repeat for each chapter, ordered by time)\n"
)


def _client() -> OpenAI:
    if not settings.llm_ready:
        raise RuntimeError(
            "LLM API key not configured. Set LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL in backend/.env."
        )
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response with fallback extraction."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group())
        raise


def _chat_json(system: str, user: str, retries: int = 1) -> dict:
    client = _client()
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            kwargs: dict = {
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.3,
            }
            try:
                kwargs["response_format"] = {"type": "json_object"}
            except Exception:
                pass
            resp = client.chat.completions.create(**kwargs)
            return _parse_json_response(resp.choices[0].message.content or "")
        except Exception as e:
            last_err = e
            if attempt >= retries:
                break
    raise RuntimeError(f"LLM JSON parse failed: {last_err}") from last_err


def summarize_structured(
    title: str,
    transcript: str,
    output_lang: str = "English",
    cues: list[dict] | None = None,
) -> dict:
    """Generate structured VideoSummary JSON."""
    system = (
        "You are a rigorous video content summarization expert. "
        "Respond ONLY with valid JSON matching the schema. "
        "Stay faithful to the source; do not invent facts."
    )
    prompt = (
        f'Analyze the video "{title}" and write the summary in {output_lang}.\n\n'
        "Return JSON with this exact structure:\n"
        '{"tldr": "one sentence overview", '
        '"key_points": ["point 1", "point 2", ...3-6 items], '
        '"chapters": [{"title": "chapter name", "summary": "1-2 sentences", '
        '"start_label": "mm:ss or hh:mm:ss"}]}\n\n'
        "Requirements:\n"
        "- key_points: 3-6 concise bullet points\n"
        "- chapters: ordered by time, each with approximate start_label from transcript\n"
        "- Use only information from the subtitle text\n\n"
        f"Subtitle text:\n{transcript}"
    )
    data = _chat_json(system, prompt)
    return {
        "tldr": data.get("tldr", ""),
        "key_points": data.get("key_points") or [],
        "chapters": data.get("chapters") or [],
    }


def map_summarize_chunk(
    title: str,
    chunk_text: str,
    chunk_index: int,
    total: int,
    output_lang: str = "English",
) -> dict:
    """Map phase: partial summary for one transcript chunk."""
    system = "You are a video content analyst. Respond ONLY with valid JSON."
    prompt = (
        f'Video "{title}" — segment {chunk_index + 1}/{total}. '
        f"Summarize in {output_lang}. Return JSON:\n"
        '{"partial_tldr": "...", "partial_points": ["..."], '
        '"partial_chapters": [{"title": "...", "summary": "...", "start_label": "mm:ss"}]}\n\n'
        f"Segment text:\n{chunk_text}"
    )
    return _chat_json(system, prompt)


def _stream_chat_markdown(system: str, user: str) -> Iterator[str]:
    """Stream chat completion content deltas."""
    client = _client()
    stream = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


def summarize_stream_markdown(
    title: str,
    transcript: str,
    output_lang: str = "English",
) -> Iterator[str]:
    """Stream a Markdown summary from subtitle text."""
    system = (
        "You are a rigorous video content summarization expert. "
        "Stay faithful to the source; do not invent facts. "
        + _MARKDOWN_FORMAT
    )
    prompt = (
        f'Analyze the video "{title}" and write the summary in {output_lang}.\n\n'
        f"Subtitle text:\n{transcript}"
    )
    yield from _stream_chat_markdown(system, prompt)


def reduce_summaries_stream(
    title: str,
    partials: list[dict],
    output_lang: str = "English",
) -> Iterator[str]:
    """Stream reduce phase: merge partial summaries into Markdown."""
    system = (
        "You are a video content analyst. Deduplicate similar chapters. "
        + _MARKDOWN_FORMAT
    )
    partials_json = json.dumps(partials, ensure_ascii=False)
    prompt = (
        f'Merge these partial summaries of "{title}" into one coherent summary in {output_lang}.\n\n'
        f"Partials:\n{partials_json}"
    )
    yield from _stream_chat_markdown(system, prompt)


def parse_markdown_to_summary(md: str) -> dict:
    """Lightweight parse of streamed Markdown into VideoSummary fields."""
    md = (md or "").strip()
    if not md:
        raise ValueError("Could not parse Markdown summary")
    tldr = ""
    key_points: list[str] = []
    chapters: list[dict] = []

    tldr_match = re.search(
        r"(?:^|\n)#+\s*(?:TL;DR|tl;dr|一句话总结|总结)\s*\n+(.+?)(?=\n#|\n##|\Z)",
        md,
        re.DOTALL | re.IGNORECASE,
    )
    if tldr_match:
        tldr = tldr_match.group(1).strip().split("\n")[0].strip()
    else:
        for line in md.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-") and not line.startswith("*"):
                tldr = line
                break

    in_key_points = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^#+\s*(?:key points|核心要点|要点)", stripped, re.IGNORECASE):
            in_key_points = True
            continue
        if stripped.startswith("##") and not re.search(r"\[[\d:]+\]", stripped):
            in_key_points = False
        if in_key_points:
            m = re.match(r"^[-*]\s+(.+)$", stripped)
            if m:
                key_points.append(m.group(1).strip())

    if not key_points:
        for m in re.finditer(r"^[-*]\s+(.+)$", md, re.MULTILINE):
            pt = m.group(1).strip()
            if pt and not re.match(r"^\[[\d:]+\]", pt):
                key_points.append(pt)

    chapter_re = re.compile(
        r"^##+\s*(?:\[([^\]]+)\]\s*)?(.+?)\s*$",
        re.MULTILINE,
    )
    matches = list(chapter_re.finditer(md))
    for i, m in enumerate(matches):
        start_label = (m.group(1) or "").strip()
        title_text = m.group(2).strip()
        if re.match(r"^(?:key points|tldr|核心要点|要点|一句话总结|总结)$", title_text, re.IGNORECASE):
            continue
        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[start_pos:end_pos].strip()
        body_lines = [ln.strip() for ln in body.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        summary_text = " ".join(body_lines[:3]).strip()
        chapters.append({
            "title": title_text,
            "summary": summary_text,
            "start_label": start_label,
        })

    if not tldr and not key_points and not chapters:
        raise ValueError("Could not parse Markdown summary")

    return {
        "tldr": tldr,
        "key_points": key_points[:6],
        "chapters": chapters,
    }


def reduce_summaries(
    title: str,
    partials: list[dict],
    output_lang: str = "English",
) -> dict:
    """Reduce phase: merge partial summaries into one VideoSummary."""
    system = "You are a video content analyst. Respond ONLY with valid JSON."
    partials_json = json.dumps(partials, ensure_ascii=False)
    prompt = (
        f'Merge these partial summaries of "{title}" into one coherent summary in {output_lang}.\n'
        "Deduplicate similar chapters. Return JSON:\n"
        '{"tldr": "...", "key_points": ["..."], '
        '"chapters": [{"title": "...", "summary": "...", "start_label": "mm:ss"}]}\n\n'
        f"Partials:\n{partials_json}"
    )
    data = _chat_json(system, prompt)
    return {
        "tldr": data.get("tldr", ""),
        "key_points": data.get("key_points") or [],
        "chapters": data.get("chapters") or [],
    }


def structured_to_markdown(summary: dict) -> str:
    """Convert structured summary to legacy Markdown text."""
    lines = [summary.get("tldr", "")]
    lines.append("")
    for pt in summary.get("key_points") or []:
        lines.append(f"- {pt}")
    lines.append("")
    for ch in summary.get("chapters") or []:
        label = ch.get("start_label") or ""
        prefix = f"[{label}] " if label else ""
        lines.append(f"{prefix}{ch.get('title', '')}: {ch.get('summary', '')}")
    return "\n".join(lines).strip()


def summarize(title: str, transcript: str, output_lang: str = "English") -> str:
    """Generate a structured summary from subtitle text (legacy Markdown)."""
    structured = summarize_structured(title, transcript, output_lang)
    return structured_to_markdown(structured)


def generate_mindmap_llm(
    title: str,
    transcript: str,
    summary: dict | None,
    output_lang: str = "English",
) -> dict:
    """LLM-generated mind map tree from transcript + optional structured summary."""
    summary_hint = ""
    if summary:
        summary_hint = (
            "\n\nStructured summary for reference:\n"
            + json.dumps(
                {
                    "tldr": summary.get("tldr", ""),
                    "key_points": summary.get("key_points") or [],
                    "chapters": summary.get("chapters") or [],
                },
                ensure_ascii=False,
            )
        )

    system = (
        "You are a video content analyst. Build a hierarchical mind map from the source material. "
        "Respond ONLY with valid JSON. Stay faithful to the transcript; do not invent facts."
    )
    prompt = (
        f'Create a mind map for the video "{title}" in {output_lang}.\n'
        "Return JSON with this exact structure:\n"
        '{"root": {"id": "root", "label": "video title or main theme", "type": "root", '
        '"children": [{"id": "c1", "label": "...", "type": "chapter|point|detail", '
        '"start_sec": 0, "children": [...]}]}}\n\n'
        "Requirements:\n"
        "- 2-4 top-level branches (chapters or themes)\n"
        "- Each branch may have 2-5 sub-points\n"
        "- Use type: root | chapter | point | detail\n"
        "- Include start_sec (seconds) when a node maps to a transcript moment\n"
        "- Labels concise (under 80 chars)\n\n"
        f"Subtitle text:\n{transcript[:12000]}"
        f"{summary_hint}"
    )
    data = _chat_json(system, prompt)
    root = data.get("root") or data
    if "label" not in root and "children" not in root:
        raise RuntimeError("LLM mind map JSON missing root node")
    return {"root": root}


def mindmap_tree_to_markdown(root: dict, depth: int = 0) -> str:
    """Convert mind map JSON tree to Markdown for markmap rendering."""
    label = (root.get("label") or "Mind Map").strip()
    prefix = "#" * min(depth + 1, 6)
    lines = [f"{prefix} {label}"]
    for child in root.get("children") or []:
        lines.append(mindmap_tree_to_markdown(child, depth + 1))
    return "\n".join(lines)


def _build_qa_system_prompt(title: str, context: str, output_lang: str) -> str:
    return (
        f'You answer questions about the video "{title}" using ONLY the provided transcript context. '
        f"Respond in {output_lang}. If the answer is not in the context, say you cannot find it. "
        "Include [mm:ss] or [hh:mm:ss] timestamp citations inline when referencing specific moments. "
        "Do not invent facts."
        f"\n\nTranscript context:\n{context}"
    )


def answer_question_stream(
    title: str,
    context: str,
    messages: list[dict],
    output_lang: str = "English",
) -> Iterator[str]:
    """Stream a Q&A answer grounded in transcript context."""
    client = _client()
    system = _build_qa_system_prompt(title, context, output_lang)
    chat_messages = [{"role": "system", "content": system}]
    for msg in messages:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            chat_messages.append({"role": role, "content": content})

    stream = client.chat.completions.create(
        model=settings.llm_model,
        messages=chat_messages,
        temperature=0.3,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


_TS_CITATION_RE = re.compile(
    r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]"
)


def extract_citations_from_answer(answer: str, cues: list[dict]) -> list[dict]:
    """Parse [mm:ss] markers in an answer into cue-aligned citations."""
    if not answer or not cues:
        return []

    cue_starts = [c.get("start_sec", ts_to_sec(c["start"])) for c in cues]
    citations: list[dict] = []
    seen: set[int] = set()

    for m in _TS_CITATION_RE.finditer(answer):
        label = m.group(1)
        parts = label.split(":")
        try:
            if len(parts) == 2:
                target_sec = int(parts[0]) * 60 + int(parts[1])
            else:
                target_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            continue

        best_idx = min(range(len(cue_starts)), key=lambda i: abs(cue_starts[i] - target_sec))
        if best_idx in seen:
            continue
        seen.add(best_idx)
        cue = cues[best_idx]
        citations.append({
            "start_sec": cue.get("start_sec", target_sec),
            "end_sec": cue.get("end_sec", target_sec + 5),
            "quote": cue.get("text", "")[:200],
            "cue_index": cue.get("index", best_idx),
        })

    return citations


def translate_cues(cues: list[dict], target_lang: str) -> list[dict]:
    """Translate subtitle cues line by line while preserving timestamps."""
    client = _client()
    if not cues:
        return cues

    # Wrap lines with indices so translations can be realigned
    numbered = "\n".join(f"[{i}] {c['text']}" for i, c in enumerate(cues))
    prompt = (
        f"Translate the numbered subtitles below into {target_lang}. Requirements:\n"
        "- Translate line by line, keeping the [index] prefix on each line\n"
        "- Output only the translation, no extra explanation\n"
        "- Keep natural, concise spoken language\n\n"
        f"{numbered}"
    )
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": "You are a professional subtitle translator. Output must preserve [index] prefixes.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    text = resp.choices[0].message.content or ""

    # Parse [i] text back into cue mapping
    import re
    mapping: dict[int, str] = {}
    for m in re.finditer(r"\[(\d+)\]\s*(.*)", text):
        mapping[int(m.group(1))] = m.group(2).strip()

    result = []
    for i, c in enumerate(cues):
        result.append({
            "start": c["start"],
            "end": c["end"],
            "text": mapping.get(i, c["text"]),
        })
    return result
