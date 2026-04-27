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
        prompt = self._build_prompt(answer_seed)
        final_text = self.llm.generate(prompt).text
        final_text = self._ensure_exact_format(final_text, fallback=answer_seed)
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

    def _build_prompt(self, answer_seed: str) -> str:
        if getattr(self.llm, "provider_name", "") != "ollama":
            return (
                "Rewrite the following into a concise operations analyst incident brief. "
                "Keep these exact headings: Root Cause, Key Signals, Recommended Actions, Confidence.\n\n"
                f"FINAL_ANSWER:\n{answer_seed}"
            )

        return (
            "You are formatting an IncidentLens incident brief.\n\n"
            "Return plain text only. Do not use Markdown emphasis, star characters, numbered lists, "
            "code blocks, Markdown heading markers, or nested bullets. Use only simple hyphen bullets "
            "for Key Signals and Recommended Actions.\n\n"
            "Return exactly this format, replacing placeholders with content from the source brief:\n\n"
            "Root Cause\n"
            "<one concise sentence>\n\n"
            "Key Signals\n"
            "- <signal 1>\n"
            "- <signal 2>\n"
            "- <signal 3>\n\n"
            "Recommended Actions\n"
            "- <action 1>\n"
            "- <action 2>\n"
            "- <action 3>\n\n"
            "Confidence\n"
            "<0.00-1.00>\n\n"
            "Rules:\n"
            "- Root Cause must be one concise sentence.\n"
            "- Include exactly three Key Signals.\n"
            "- Include exactly three Recommended Actions.\n"
            "- Confidence must be a decimal from 0.00 to 1.00.\n"
            "- Do not add any other text.\n\n"
            f"Source brief:\n{answer_seed}"
        )

    def _ensure_exact_format(self, text: str, fallback: str) -> str:
        cleaned = text.replace("**", "").replace("*", "").strip()
        sections = _parse_sections(cleaned)
        if set(sections) >= {"Root Cause", "Key Signals", "Recommended Actions", "Confidence"}:
            root_cause = _first_sentence(sections["Root Cause"]) or _section_text(fallback, "Root Cause")
            signals = _section_bullets(sections["Key Signals"])[:3]
            actions = _section_bullets(sections["Recommended Actions"])[:3]
            confidence = _section_text(cleaned, "Confidence").splitlines()[0].strip()
            if len(signals) == 3 and len(actions) == 3 and _looks_like_confidence(confidence):
                return _format_incident_brief(root_cause, signals, actions, confidence)
        return fallback

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
        summary_lines = []
        if primary:
            summary_lines.append(
                f"{service} in {region} averaged {primary.avg_latency_ms:.1f} ms latency, "
                f"{primary.avg_error_rate:.3f} error rate, and {primary.avg_queue_depth:.1f} queue depth."
            )
        if comparisons:
            deltas = ", ".join(
                f"{name} {comparison.delta_pct:+.1f}%"
                for name, comparison in comparisons.items()
                if abs(comparison.delta_pct) >= 25
            )
            if deltas:
                summary_lines.append(f"Material baseline deltas: {deltas}.")
        event_signals = [item for item in evidence if " event for " in item]
        other_signals = [item for item in evidence if item not in event_signals]
        ordered_signals = [*summary_lines, *event_signals, *other_signals]
        signals = _pad_to_three(ordered_signals, "No additional signal was retrieved.")
        actions = _pad_to_three(recommendations, "Continue monitoring until metrics return to baseline.")
        return _format_incident_brief(likely_cause, signals[:3], actions[:3], f"{confidence:.2f}")


def _delta(structured: StructuredEvidence, metric: str) -> float:
    for comparison in structured.baseline_comparisons:
        if comparison.metric == metric:
            return comparison.delta_pct
    return 0.0


def _format_incident_brief(root_cause: str, signals: list[str], actions: list[str], confidence: str) -> str:
    signal_block = "\n".join(f"- {signal.strip()}" for signal in signals[:3])
    action_block = "\n".join(f"- {action.strip()}" for action in actions[:3])
    return (
        f"Root Cause\n{root_cause.strip()}\n\n"
        f"Key Signals\n{signal_block}\n\n"
        f"Recommended Actions\n{action_block}\n\n"
        f"Confidence\n{confidence.strip()}"
    )


def _pad_to_three(items: list[str], filler: str) -> list[str]:
    cleaned = [item.strip() for item in items if item and item.strip()]
    while len(cleaned) < 3:
        cleaned.append(filler)
    return cleaned[:3]


def _parse_sections(text: str) -> dict[str, str]:
    headings = ["Root Cause", "Key Signals", "Recommended Actions", "Confidence"]
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in lines:
        line = raw_line.strip().strip("#").strip()
        if line in headings:
            current = line
            sections[current] = []
            continue
        if current:
            sections[current].append(raw_line)
    return {heading: "\n".join(content).strip() for heading, content in sections.items()}


def _section_bullets(text: str) -> list[str]:
    bullets = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif line:
            bullets.append(line.lstrip("- ").strip())
    return bullets


def _section_text(text: str, heading: str) -> str:
    return _parse_sections(text).get(heading, "").strip()


def _first_sentence(text: str) -> str:
    line = " ".join(part.strip().lstrip("- ").strip() for part in text.splitlines() if part.strip())
    if not line:
        return ""
    if "." in line:
        return line.split(".", 1)[0].strip() + "."
    return line.strip()


def _looks_like_confidence(value: str) -> bool:
    try:
        parsed = float(value)
    except ValueError:
        return False
    return 0.0 <= parsed <= 1.0
