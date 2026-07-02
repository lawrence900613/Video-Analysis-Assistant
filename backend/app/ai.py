"""大模型能力：视频总结、字幕翻译（OpenAI 兼容协议）。"""
from __future__ import annotations

from openai import OpenAI

from .config import get_settings

settings = get_settings()


def _client() -> OpenAI:
    if not settings.llm_ready:
        raise RuntimeError(
            "未配置大模型 API Key。请在 backend/.env 中填写 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL。"
        )
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def summarize(title: str, transcript: str) -> str:
    """根据字幕文本生成中文总结（要点 + 结构化概览）。"""
    client = _client()
    prompt = (
        f"你是专业的视频内容分析助手。以下是视频《{title}》的字幕文本，请用简体中文输出：\n"
        "1. 一句话概述（TL;DR）\n"
        "2. 3-6 个核心要点（分点列出）\n"
        "3. 内容大纲（按讲述顺序，简短）\n\n"
        "要求：忠于原文、条理清晰、不编造内容。\n\n"
        f"字幕文本：\n{transcript}"
    )
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "你是严谨的中文视频内容总结专家。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def translate_cues(cues: list[dict], target_lang: str) -> list[dict]:
    """逐条翻译字幕，保持时间轴不变。"""
    client = _client()
    if not cues:
        return cues

    # 用编号包裹，便于对齐还原
    numbered = "\n".join(f"[{i}] {c['text']}" for i, c in enumerate(cues))
    prompt = (
        f"请把下面带编号的字幕翻译成{target_lang}。要求：\n"
        "- 逐行翻译，保留每行的 [编号] 前缀\n"
        "- 只输出翻译结果，不要额外解释\n"
        "- 保持口语自然、简洁\n\n"
        f"{numbered}"
    )
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "你是专业的字幕翻译，输出必须保留 [编号] 前缀。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    text = resp.choices[0].message.content or ""

    # 还原：解析 [i] 文本
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
