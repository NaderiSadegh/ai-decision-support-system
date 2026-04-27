from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TimeWindow:
    start: str
    end: str


@dataclass(frozen=True)
class RouteDecision:
    intent: str
    use_structured_retrieval: bool
    use_text_retrieval: bool
    rationale: str


@dataclass(frozen=True)
class InvestigationPlan:
    question: str
    intent: str
    service: str | None
    region: str | None
    metrics: list[str]
    time_window: TimeWindow
    steps: list[str]


@dataclass(frozen=True)
class MetricSummary:
    service: str
    region: str
    avg_latency_ms: float
    avg_error_rate: float
    avg_throughput_rpm: float
    avg_cpu_pct: float
    avg_queue_depth: float
    max_saturation_score: float
    samples: int


@dataclass(frozen=True)
class BaselineComparison:
    metric: str
    current: float
    baseline: float
    delta_pct: float


@dataclass(frozen=True)
class EventEvidence:
    timestamp: str
    service: str
    region: str
    event_type: str
    severity: str
    description: str
    actor: str


@dataclass(frozen=True)
class TextEvidence:
    source_type: str
    source_id: str
    title: str
    content: str
    score: float


@dataclass(frozen=True)
class StructuredEvidence:
    metric_summaries: list[MetricSummary] = field(default_factory=list)
    baseline_comparisons: list[BaselineComparison] = field(default_factory=list)
    related_events: list[EventEvidence] = field(default_factory=list)
    anomaly_labels: list[dict[str, Any]] = field(default_factory=list)
    sql_queries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReasoningResult:
    answer: str
    likely_cause: str
    confidence: float
    evidence: list[str]
    recommendations: list[str]
    intermediate_steps: list[str]


@dataclass(frozen=True)
class AnalysisResult:
    question: str
    route: RouteDecision
    plan: InvestigationPlan
    structured_evidence: StructuredEvidence
    text_evidence: list[TextEvidence]
    reasoning: ReasoningResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "route": self.route.__dict__,
            "plan": {
                **self.plan.__dict__,
                "time_window": self.plan.time_window.__dict__,
            },
            "structured_evidence": {
                "metric_summaries": [item.__dict__ for item in self.structured_evidence.metric_summaries],
                "baseline_comparisons": [item.__dict__ for item in self.structured_evidence.baseline_comparisons],
                "related_events": [item.__dict__ for item in self.structured_evidence.related_events],
                "anomaly_labels": self.structured_evidence.anomaly_labels,
                "sql_queries": self.structured_evidence.sql_queries,
            },
            "text_evidence": [item.__dict__ for item in self.text_evidence],
            "reasoning": self.reasoning.__dict__,
        }
