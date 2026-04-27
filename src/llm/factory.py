from __future__ import annotations

from llm.base import LLMProvider
from llm.mock import MockLLM
from llm.ollama import OllamaLLM
from utils.config import Settings


def build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockLLM()
    if settings.llm_provider == "ollama":
        return OllamaLLM(base_url=settings.ollama_base_url, model=settings.ollama_model)
    raise ValueError("Unsupported LLM_PROVIDER. Use 'mock' or 'ollama'.")
