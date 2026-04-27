from __future__ import annotations

import re
from datetime import datetime, timedelta

from data.generate_synthetic import REGIONS, SERVICES
from reasoning.models import InvestigationPlan, RouteDecision, TimeWindow

DATE_RE = re.compile(r"(2026-04-\d{2}|april\s+\d{1,2})", re.IGNORECASE)


class Planner:
    def create_plan(self, question: str, route: RouteDecision) -> InvestigationPlan:
        lower = question.lower()
        service = next((candidate for candidate in SERVICES if candidate in lower), None)
        region = next((candidate for candidate in REGIONS if candidate in lower), None)
        metrics = self._extract_metrics(lower)
        time_window = self._extract_time_window(lower, service)
        steps = [
            "Route the question by operational intent.",
            "Extract service, region, metrics, and time window.",
            "Retrieve structured metrics, related events, and anomaly labels.",
            "Retrieve matching logs, incidents, and runbooks.",
            "Compare current behavior with baseline and synthesize a supported answer.",
        ]
        return InvestigationPlan(
            question=question,
            intent=route.intent,
            service=service,
            region=region,
            metrics=metrics,
            time_window=time_window,
            steps=steps,
        )

    def _extract_metrics(self, lower: str) -> list[str]:
        mapping = {
            "latency": ["latency", "slow", "p95"],
            "error_rate": ["error", "fail", "5xx"],
            "queue_depth": ["queue", "backpressure", "retry"],
            "cpu_pct": ["cpu", "saturation"],
            "throughput_rpm": ["throughput", "traffic", "requests"],
        }
        metrics = [metric for metric, terms in mapping.items() if any(term in lower for term in terms)]
        return metrics or ["latency", "error_rate", "queue_depth", "cpu_pct"]

    def _extract_time_window(self, lower: str, service: str | None) -> TimeWindow:
        match = DATE_RE.search(lower)
        if match:
            raw = match.group(1).lower()
            day = int(raw[-2:]) if raw.startswith("2026-04-") else int(raw.split()[-1])
            start = datetime(2026, 4, day, 0, 0)
            end = datetime(2026, 4, day, 23, 59)
            return _narrow_to_known_incident(service, start, end)

        defaults = {
            "checkout-api": TimeWindow("2026-04-04T08:00:00", "2026-04-04T17:00:00"),
            "billing-worker": TimeWindow("2026-04-05T00:00:00", "2026-04-05T09:00:00"),
            "search-api": TimeWindow("2026-04-06T11:00:00", "2026-04-06T20:00:00"),
        }
        if service in defaults:
            return defaults[service]
        return TimeWindow("2026-04-04T00:00:00", "2026-04-06T23:59:00")


def _narrow_to_known_incident(service: str | None, start: datetime, end: datetime) -> TimeWindow:
    if service == "checkout-api" and start.date().isoformat() == "2026-04-04":
        return TimeWindow("2026-04-04T08:00:00", "2026-04-04T17:00:00")
    if service == "billing-worker" and start.date().isoformat() == "2026-04-05":
        return TimeWindow("2026-04-05T00:00:00", "2026-04-05T09:00:00")
    if service == "search-api" and start.date().isoformat() == "2026-04-06":
        return TimeWindow("2026-04-06T11:00:00", "2026-04-06T20:00:00")
    # Include a small buffer around the full day so neighboring events still show up.
    return TimeWindow((start - timedelta(hours=1)).isoformat(), (end + timedelta(minutes=1)).isoformat())
