from __future__ import annotations

from llm.base import LLMResponse
from reasoning.analyzer import RootCauseReasoner


class CapturingOllama:
    provider_name = "ollama"

    def generate(self, prompt: str) -> LLMResponse:
        return LLMResponse(text=prompt, provider=self.provider_name)


def test_ollama_prompt_enforces_plain_text_incident_format():
    prompt = RootCauseReasoner(CapturingOllama())._build_prompt(
        "Root Cause\nA cache change caused checkout latency.\n\nConfidence\n0.95"
    )

    assert "Return plain text only" in prompt
    assert "Do not use Markdown emphasis" in prompt
    assert "star characters" in prompt
    assert "Root Cause\n<one concise sentence>" in prompt
    assert "Key Signals\n- <signal 1>\n- <signal 2>\n- <signal 3>" in prompt
    assert "Recommended Actions\n- <action 1>\n- <action 2>\n- <action 3>" in prompt
    assert "Confidence\n<0.00-1.00>" in prompt
    assert "Include exactly three Key Signals" in prompt
    assert "Include exactly three Recommended Actions" in prompt
