from __future__ import annotations

from llm.base import LLMProvider
from reasoning.models import InvestigationPlan, ReasoningResult, RouteDecision, StructuredEvidence, TextEvidence


class RootCauseReasoner:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    def synthesize(
        self,
        route: RouteDecision,
        plan: InvestigationPlan,
        structured: StructuredEvidence,
        text_evidence: list[TextEvidence],
    ) -> ReasoningResult:
        primary = structured.metric_summaries[0] if structured.metric_summaries else None
        comparisons = {item.metric: item for item in structured.baseline_comparisons}
        labels = structured.anomaly_labels
        events = structured.related_events
        likely_cause = labels[0]["root_cause"] if labels else self._infer_cause(structured, text_evidence)
        evidence = self._build_evidence(structured, text_evidence)
        confidence = self._confidence(structured, text_evidence)
        recommendations = self._recommendations(likely_cause, plan, text_evidence)
        answer_seed = self._answer_seed(
            plan, route, primary, comparisons, likely_cause, confidence, evidence, recommendations
        )
        prompt = f"Rewrite the following into a concise operations analyst answer.\n\nFINAL_ANSWER:\n{answer_seed}"
        final_text = self.llm.generate(prompt).text
        intermediate_steps = [
            f"Route: {route.intent} ({route.rationale})",
            (
                f"Plan: service={plan.service or 'all'}, region={plan.region or 'all'}, "
                f"window={plan.time_window.start} to {plan.time_window.end}"
            ),
            (
                f"Structured retrieval: {len(structured.metric_summaries)} metric summaries, "
                f"{len(events)} related events, {len(labels)} anomaly labels"
            ),
            f"Text retrieval: {len(text_evidence)} matching logs/incidents/runbooks",
            f"Synthesis: likely cause selected with confidence {confidence:.2f}",
        ]
        return ReasoningResult(
            answer=final_text,
            likely_cause=likely_cause,
            confidence=confidence,
            evidence=evidence,
            recommendations=recommendations,
            intermediate_steps=intermediate_steps,
        )

    def _infer_cause(self, structured: StructuredEvidence, text_evidence: list[TextEvidence]) -> str:
        event_types = {event.event_type for event in structured.related_events}
        text = " ".join(item.content.lower() + " " + item.title.lower() for item in text_evidence)
        queue_delta = _delta(structured, "queue_depth")
        latency_delta = _delta(structured, "latency_ms")
        cpu_delta = _delta(structured, "cpu_pct")
        if "deployment" in event_types and ("cache" in text or queue_delta > 100):
            return "A recent deployment likely changed cache behavior, increasing latency and queue pressure."
        if "external_dependency" in event_types or "provider timeout" in text:
            return "An external dependency timeout likely caused retries and queue buildup."
        if cpu_delta > 70 and "index" in text:
            return "Background index maintenance likely competed with live traffic for CPU."
        if latency_delta > 100 and queue_delta > 100:
            return "The service appears constrained by queue backpressure during the requested window."
        return "The evidence shows degraded service behavior, but no single root cause is fully confirmed."

    def _build_evidence(self, structured: StructuredEvidence, text_evidence: list[TextEvidence]) -> list[str]:
        evidence: list[str] = []
        for comparison in structured.baseline_comparisons:
            if abs(comparison.delta_pct) >= 25:
                direction = "higher" if comparison.delta_pct > 0 else "lower"
                evidence.append(
                    f"{comparison.metric} was {abs(comparison.delta_pct):.1f}% {direction} than the clean baseline "
                    f"({comparison.current} vs {comparison.baseline})."
                )
        for event in structured.related_events[:3]:
            evidence.append(
                f"{event.timestamp}: {event.event_type} event for {event.service}/{event.region}: {event.description}"
            )
        for item in text_evidence[:3]:
            evidence.append(f"{item.source_type} {item.source_id}: {item.title}")
        return evidence[:8]

    def _confidence(self, structured: StructuredEvidence, text_evidence: list[TextEvidence]) -> float:
        score = 0.35
        if structured.baseline_comparisons:
            score += 0.2
        if structured.related_events:
            score += 0.15
        if structured.anomaly_labels:
            score += 0.2
        if text_evidence:
            score += 0.1
        return min(0.95, round(score, 2))

    def _recommendations(
        self, likely_cause: str, plan: InvestigationPlan, text_evidence: list[TextEvidence]
    ) -> list[str]:
        cause = likely_cause.lower()
        recommendations = []
        if "cache" in cause:
            recommendations.extend(
                [
                    "Rollback or disable the cache TTL change and verify cache miss ratio returns to baseline.",
                    "Warm critical checkout caches before re-enabling the release.",
                    (
                        "Add a deployment guardrail that halts rollout when miss ratio, "
                        "latency, or queue depth rises together."
                    ),
                ]
            )
        elif "payment" in cause or "dependency" in cause:
            recommendations.extend(
                [
                    "Enable the provider circuit breaker and cap retry concurrency.",
                    "Drain queued jobs gradually once dependency health recovers.",
                    "Track idempotency errors while replaying delayed billing work.",
                ]
            )
        elif "index" in cause or "cpu" in cause:
            recommendations.extend(
                [
                    "Throttle or isolate the rebuild workload from live query nodes.",
                    "Watch CPU saturation and p95 latency for two consecutive windows.",
                    "Move future rebuilds to a lower-traffic window or dedicated capacity.",
                ]
            )
        else:
            recommendations.extend(
                [
                    "Inspect the highest-delta metrics first, then correlate with deploys and dependency logs.",
                    "Keep the incident window open until latency and error rate return to baseline.",
                ]
            )
        for item in text_evidence:
            if item.source_type == "runbook" and item.title not in " ".join(recommendations):
                recommendations.append(f"Use runbook guidance: {item.title}.")
                break
        if plan.intent == "performance_summary":
            recommendations.append(
                "Review lower-confidence services separately if they lack corroborating text evidence."
            )
        return recommendations[:4]

    def _answer_seed(
        self,
        plan: InvestigationPlan,
        route: RouteDecision,
        primary: object,
        comparisons: dict[str, object],
        likely_cause: str,
        confidence: float,
        evidence: list[str],
        recommendations: list[str],
    ) -> str:
        service = plan.service or getattr(primary, "service", "the selected services")
        region = plan.region or getattr(primary, "region", "all regions")
        headline = f"The most likely cause for {service} in {region} is: {likely_cause} Confidence: {confidence:.2f}."
        if primary:
            headline += (
                f" During the window, average latency was {primary.avg_latency_ms:.1f} ms, "
                f"error rate was {primary.avg_error_rate:.3f}, and queue depth averaged {primary.avg_queue_depth:.1f}."
            )
        if comparisons:
            deltas = ", ".join(
                f"{name} {comparison.delta_pct:+.1f}%"
                for name, comparison in comparisons.items()
                if abs(comparison.delta_pct) >= 25
            )
            if deltas:
                headline += f" Material baseline deltas: {deltas}."
        evidence_block = "\n".join(f"- {item}" for item in evidence)
        recommendation_block = "\n".join(f"- {item}" for item in recommendations)
        return (
            f"{headline}\n\n"
            f"Intent: {route.intent}.\n\n"
            f"Evidence:\n{evidence_block}\n\n"
            f"Recommended next actions:\n{recommendation_block}"
        )


def _delta(structured: StructuredEvidence, metric: str) -> float:
    for comparison in structured.baseline_comparisons:
        if comparison.metric == metric:
            return comparison.delta_pct
    return 0.0
