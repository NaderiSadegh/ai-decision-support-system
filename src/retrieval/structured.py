from __future__ import annotations

from datetime import datetime, timedelta

from reasoning.models import (
    BaselineComparison,
    EventEvidence,
    InvestigationPlan,
    MetricSummary,
    StructuredEvidence,
)
from retrieval.sqlite_store import OperationsStore


class StructuredRetriever:
    def __init__(self, store: OperationsStore) -> None:
        self.store = store

    def retrieve(self, plan: InvestigationPlan) -> StructuredEvidence:
        summaries = [
            MetricSummary(
                service=row["service"],
                region=row["region"],
                avg_latency_ms=round(row["avg_latency_ms"], 2),
                avg_error_rate=round(row["avg_error_rate"], 4),
                avg_throughput_rpm=round(row["avg_throughput_rpm"], 2),
                avg_cpu_pct=round(row["avg_cpu_pct"], 2),
                avg_queue_depth=round(row["avg_queue_depth"], 2),
                max_saturation_score=round(row["max_saturation_score"], 4),
                samples=int(row["samples"]),
            )
            for row in self.store.metric_summary(
                plan.time_window.start,
                plan.time_window.end,
                plan.service,
                plan.region,
            )
        ]
        primary = summaries[0] if summaries else None
        comparisons: list[BaselineComparison] = []
        if primary:
            baseline_start, baseline_end = _baseline_window(plan.time_window.start, plan.time_window.end)
            baseline = self.store.baseline_summary(
                baseline_start,
                baseline_end,
                primary.service,
                primary.region,
            )
            if baseline:
                metric_pairs = {
                    "latency_ms": (primary.avg_latency_ms, baseline["avg_latency_ms"]),
                    "error_rate": (primary.avg_error_rate, baseline["avg_error_rate"]),
                    "throughput_rpm": (primary.avg_throughput_rpm, baseline["avg_throughput_rpm"]),
                    "cpu_pct": (primary.avg_cpu_pct, baseline["avg_cpu_pct"]),
                    "queue_depth": (primary.avg_queue_depth, baseline["avg_queue_depth"]),
                }
                comparisons = [
                    BaselineComparison(
                        metric=metric,
                        current=round(current, 4),
                        baseline=round(base, 4),
                        delta_pct=round(((current - base) / base) * 100, 2) if base else 0.0,
                    )
                    for metric, (current, base) in metric_pairs.items()
                ]

        events = [
            EventEvidence(
                timestamp=row["timestamp"],
                service=row["service"],
                region=row["region"],
                event_type=row["event_type"],
                severity=row["severity"],
                actor=row["actor"],
                description=row["description"],
            )
            for row in self.store.events_between(
                plan.time_window.start,
                plan.time_window.end,
                plan.service,
                plan.region,
            )
        ]
        labels = self.store.anomaly_labels(
            plan.time_window.start,
            plan.time_window.end,
            plan.service,
            plan.region,
        )
        sql_queries = [
            "SELECT service, region, AVG(latency_ms), AVG(error_rate), AVG(queue_depth) "
            "FROM metrics WHERE timestamp BETWEEN :start AND :end GROUP BY service, region",
            "SELECT * FROM events WHERE timestamp BETWEEN :start AND :end",
        ]
        return StructuredEvidence(
            metric_summaries=summaries,
            baseline_comparisons=comparisons,
            related_events=events,
            anomaly_labels=labels,
            sql_queries=sql_queries,
        )


def _baseline_window(start: str, end: str) -> tuple[str, str]:
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    duration = end_dt - start_dt
    baseline_end = start_dt - timedelta(hours=1)
    baseline_start = baseline_end - max(duration, timedelta(hours=6))
    return baseline_start.isoformat(), baseline_end.isoformat()
