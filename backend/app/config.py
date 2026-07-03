"""Application settings loaded from environment variables / .env."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load backend/.env
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _normalize_llm_base_url(url: str) -> str:
    """Ensure OpenAI-compatible base URLs include the /v1 suffix."""
    url = (url or "https://api.deepseek.com/v1").strip().rstrip("/")
    if url.endswith("/v1"):
        return url
    for host in ("api.openai.com", "api.deepseek.com", "api.moonshot.cn", "dashscope.aliyuncs.com"):
        if host in url:
            return f"{url}/v1"
    return url


class Settings:
    def __init__(self) -> None:
        self.llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
        self.llm_base_url: str = _normalize_llm_base_url(os.getenv("LLM_BASE_URL", ""))
        self.llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat").strip()

        download_dir = os.getenv("DOWNLOAD_DIR", "downloads").strip()
        self.download_dir: Path = (BACKEND_DIR / download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.max_subtitle_chars: int = int(os.getenv("MAX_SUBTITLE_CHARS", "16000"))
        self.chunk_max_chars: int = int(os.getenv("CHUNK_MAX_CHARS", "6000"))
        self.max_analysis_duration_sec: int = int(os.getenv("MAX_ANALYSIS_DURATION_SEC", str(2 * 3600)))

        self.host: str = os.getenv("HOST", "0.0.0.0").strip()
        self.port: int = int(os.getenv("PORT", "8000"))

        # Optional: path to Netscape cookies.txt for sites that require login (e.g. YouTube)
        cookies = os.getenv("YTDLP_COOKIES", "").strip()
        self.ytdlp_cookies: Optional[Path] = None
        if cookies:
            path = Path(cookies)
            if not path.is_absolute():
                path = (BACKEND_DIR / path).resolve()
            if path.is_file():
                self.ytdlp_cookies = path

        # Optional: load cookies from browser, e.g. chrome, edge, firefox
        self.ytdlp_cookies_from_browser: Optional[str] = os.getenv(
            "YTDLP_COOKIES_FROM_BROWSER", ""
        ).strip() or None

    @property
    def llm_ready(self) -> bool:
        return bool(self.llm_api_key) and not self.llm_api_key.startswith("sk-your-")


@lru_cache
def get_settings() -> Settings:
    return Settings()
