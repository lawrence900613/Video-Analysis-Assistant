"""LLM features: video summarization and subtitle translation (OpenAI-compatible API)."""
from __future__ import annotations

from openai import OpenAI

from .config import get_settings

settings = get_settings()


def _client() -> OpenAI:
    if not settings.llm_ready:
        raise RuntimeError(
            "LLM API key not configured. Set LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL in backend/.env."
        )
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def summarize(title: str, transcript: str, output_lang: str = "English") -> str:
    """Generate a structured summary from subtitle text."""
    client = _client()
    prompt = (
        f'You are a professional video content analyst. Below is the subtitle text for the video "{title}". '
        f"Write the summary in {output_lang}:\n"
        "1. One-sentence overview (TL;DR)\n"
        "2. 3-6 key takeaways (bullet points)\n"
        "3. Content outline (in narrative order, brief)\n\n"
        "Requirements: stay faithful to the source, be clear and structured, do not invent facts.\n\n"
        f"Subtitle text:\n{transcript}"
    )
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": "You are a rigorous video content summarization expert. Always respond in the requested language.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


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
