from __future__ import annotations

from agents.pipeline import OperationsAnalystPipeline
from data.generate_synthetic import generate_synthetic_data
from utils.config import Settings


def _settings(tmp_path):
    generate_synthetic_data(tmp_path)
    return Settings(
        data_dir=tmp_path,
        llm_provider="mock",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
        retrieval_top_k=5,
        log_level="INFO",
    )


def test_pipeline_identifies_checkout_cache_issue(tmp_path):
    pipeline = OperationsAnalystPipeline(_settings(tmp_path))

    result = pipeline.answer("Why did checkout-api latency and errors spike in eu-central-1 on April 4?")

    assert result.route.intent == "incident_investigation"
    assert result.plan.service == "checkout-api"
    assert result.plan.region == "eu-central-1"
    assert "cache" in result.reasoning.likely_cause.lower()
    assert result.reasoning.confidence >= 0.8
    assert "deployment" in result.reasoning.answer.lower()
    assert _matches_incident_brief_format(result.reasoning.answer)


def test_pipeline_returns_intermediate_steps(tmp_path):
    pipeline = OperationsAnalystPipeline(_settings(tmp_path))

    result = pipeline.answer("What caused search-api latency to increase in us-west-2 on April 6?")

    assert len(result.reasoning.intermediate_steps) >= 4
    assert result.structured_evidence.metric_summaries
    assert result.text_evidence


def _matches_incident_brief_format(answer: str) -> bool:
    sections = answer.splitlines()
    expected_headings = ["Root Cause", "Key Signals", "Recommended Actions", "Confidence"]
    heading_positions = [idx for idx, line in enumerate(sections) if line in expected_headings]
    if [sections[idx] for idx in heading_positions] != expected_headings:
        return False

    key_start = sections.index("Key Signals")
    actions_start = sections.index("Recommended Actions")
    confidence_start = sections.index("Confidence")
    key_signals = [line for line in sections[key_start + 1 : actions_start] if line.strip()]
    actions = [line for line in sections[actions_start + 1 : confidence_start] if line.strip()]

    return (
        len(key_signals) == 3
        and all(line.startswith("- ") for line in key_signals)
        and len(actions) == 3
        and all(line.startswith("- ") for line in actions)
        and float(sections[confidence_start + 1]) >= 0.0
        and "**" not in answer
        and "*" not in answer
    )
