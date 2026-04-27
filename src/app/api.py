from __future__ import annotations

from typing import Annotated

import uvicorn
from fastapi import Body, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from agents.pipeline import OperationsAnalystPipeline
from utils.config import get_settings
from utils.logging import configure_logging


class AskRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "Why did checkout-api latency spike in eu-central-1 on April 4?",
                }
            ]
        }
    )

    question: str = Field(
        ...,
        min_length=3,
        description="Natural-language operations question to investigate.",
        examples=["Why did checkout-api latency spike in eu-central-1 on April 4?"],
    )


class RouteResponse(BaseModel):
    intent: str
    use_structured_retrieval: bool
    use_text_retrieval: bool
    rationale: str


class TimeWindowResponse(BaseModel):
    start: str
    end: str


class PlanResponse(BaseModel):
    question: str
    intent: str
    service: str | None
    region: str | None
    metrics: list[str]
    time_window: TimeWindowResponse
    steps: list[str]


class MetricSummaryResponse(BaseModel):
    service: str
    region: str
    avg_latency_ms: float
    avg_error_rate: float
    avg_throughput_rpm: float
    avg_cpu_pct: float
    avg_queue_depth: float
    max_saturation_score: float
    samples: int


class BaselineComparisonResponse(BaseModel):
    metric: str
    current: float
    baseline: float
    delta_pct: float


class EventEvidenceResponse(BaseModel):
    timestamp: str
    service: str
    region: str
    event_type: str
    severity: str
    description: str
    actor: str


class StructuredEvidenceResponse(BaseModel):
    metric_summaries: list[MetricSummaryResponse]
    baseline_comparisons: list[BaselineComparisonResponse]
    related_events: list[EventEvidenceResponse]
    anomaly_labels: list[dict[str, str]]
    sql_queries: list[str]


class TextEvidenceResponse(BaseModel):
    source_type: str
    source_id: str
    title: str
    content: str
    score: float


class ReasoningResponse(BaseModel):
    answer: str
    likely_cause: str
    confidence: float
    evidence: list[str]
    recommendations: list[str]
    intermediate_steps: list[str]


class AnalysisResponse(BaseModel):
    question: str
    route: RouteResponse
    plan: PlanResponse
    structured_evidence: StructuredEvidenceResponse
    text_evidence: list[TextEvidenceResponse]
    reasoning: ReasoningResponse


class AskResponse(BaseModel):
    result: AnalysisResponse


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    pipeline = OperationsAnalystPipeline(settings)

    app = FastAPI(
        title="IncidentLens",
        version="0.1.0",
        description="AI incident investigation for synthetic SaaS operations.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "llm_provider": settings.llm_provider}

    @app.post("/ask", response_model=AskResponse)
    def ask(
        request: Annotated[
            AskRequest,
            Body(
                openapi_examples={
                    "checkout_latency": {
                        "summary": "Checkout latency incident",
                        "description": "Investigate a synthetic checkout-api degradation.",
                        "value": {
                            "question": "Why did checkout-api latency spike in eu-central-1 on April 4?",
                        },
                    }
                }
            ),
        ],
    ) -> AskResponse:
        return AskResponse(result=pipeline.answer(request.question).to_dict())

    return app


def main() -> None:
    uvicorn.run("app.api:create_app", factory=True, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
