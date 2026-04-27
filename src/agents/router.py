from __future__ import annotations

from reasoning.models import RouteDecision


class QueryRouter:
    def route(self, question: str) -> RouteDecision:
        text = question.lower()
        if any(
            term in text for term in ["why", "root cause", "spike", "incident", "anomaly", "slow", "latency", "error"]
        ):
            return RouteDecision(
                intent="incident_investigation",
                use_structured_retrieval=True,
                use_text_retrieval=True,
                rationale="Question asks for causal analysis or degraded service behavior.",
            )
        if any(term in text for term in ["fix", "mitigate", "runbook", "next step", "remediate"]):
            return RouteDecision(
                intent="remediation_guidance",
                use_structured_retrieval=True,
                use_text_retrieval=True,
                rationale="Question asks for operational recommendations.",
            )
        if any(term in text for term in ["health", "status", "performance", "summary", "overview"]):
            return RouteDecision(
                intent="performance_summary",
                use_structured_retrieval=True,
                use_text_retrieval=False,
                rationale="Question asks for a metrics-oriented status summary.",
            )
        return RouteDecision(
            intent="general_ops_question",
            use_structured_retrieval=True,
            use_text_retrieval=True,
            rationale="Default route uses both structured and text evidence for grounding.",
        )
