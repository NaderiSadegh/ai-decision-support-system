from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    retrieval_top_k: int
    log_level: str


def get_settings() -> Settings:
    data_dir = Path(os.getenv("OPS_ANALYST_DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser()
    return Settings(
        data_dir=data_dir,
        llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
