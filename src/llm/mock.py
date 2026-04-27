from __future__ import annotations

from llm.base import LLMResponse


class MockLLM:
    provider_name = "mock"

    def generate(self, prompt: str) -> LLMResponse:
        # Deterministic by design: the reasoning layer already builds the grounded answer.
        marker = "FINAL_ANSWER:"
        if marker in prompt:
            text = prompt.split(marker, 1)[1].strip()
        else:
            text = "I used the retrieved operational evidence to produce a deterministic answer."
        return LLMResponse(text=text, provider=self.provider_name)
