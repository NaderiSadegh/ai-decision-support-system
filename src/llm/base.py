from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str


class LLMProvider(Protocol):
    provider_name: str

    def generate(self, prompt: str) -> LLMResponse:
        """Generate text for a prompt."""
