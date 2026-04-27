from __future__ import annotations

from agents.planner import Planner
from agents.router import QueryRouter
from data.generate_synthetic import generate_synthetic_data
from retrieval.sqlite_store import OperationsStore
from retrieval.structured import StructuredRetriever
from retrieval.text import TextRetriever


def test_structured_retrieval_finds_related_events(tmp_path):
    generate_synthetic_data(tmp_path)
    route = QueryRouter().route("Why did checkout-api spike in eu-central-1 on April 4?")
    plan = Planner().create_plan("Why did checkout-api spike in eu-central-1 on April 4?", route)

    evidence = StructuredRetriever(OperationsStore(tmp_path)).retrieve(plan)

    assert evidence.metric_summaries[0].service == "checkout-api"
    assert any(event.event_type == "deployment" for event in evidence.related_events)
    assert evidence.baseline_comparisons


def test_text_retrieval_finds_runbook_and_logs(tmp_path):
    generate_synthetic_data(tmp_path)
    route = QueryRouter().route("How should we mitigate checkout-api cache latency?")
    plan = Planner().create_plan("How should we mitigate checkout-api cache latency?", route)

    evidence = TextRetriever(tmp_path).retrieve("How should we mitigate checkout-api cache latency?", plan)

    assert evidence
    assert any(item.source_type in {"runbook", "log", "incident"} for item in evidence)
