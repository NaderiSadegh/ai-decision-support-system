from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SERVICES = [
    "checkout-api",
    "billing-worker",
    "auth-service",
    "search-api",
    "notification-service",
    "analytics-pipeline",
]
REGIONS = ["us-east-1", "us-west-2", "eu-central-1"]
START = datetime(2026, 4, 1, 0, 0)
HOURS = 7 * 24


ANOMALIES = [
    {
        "anomaly_id": "ANOM-001",
        "service": "checkout-api",
        "region": "eu-central-1",
        "start": "2026-04-04T09:00:00",
        "end": "2026-04-04T16:00:00",
        "label": "cache_misconfiguration_after_deploy",
        "root_cause": "A deployment changed cache TTL behavior, increasing cache misses and downstream queue pressure.",
        "severity": "high",
    },
    {
        "anomaly_id": "ANOM-002",
        "service": "billing-worker",
        "region": "us-east-1",
        "start": "2026-04-05T01:00:00",
        "end": "2026-04-05T08:00:00",
        "label": "payment_provider_timeout",
        "root_cause": "An external payment provider timeout caused retry storms and queue growth.",
        "severity": "medium",
    },
    {
        "anomaly_id": "ANOM-003",
        "service": "search-api",
        "region": "us-west-2",
        "start": "2026-04-06T12:00:00",
        "end": "2026-04-06T19:00:00",
        "label": "index_rebuild_resource_contention",
        "root_cause": "A scheduled index rebuild competed with live search traffic for CPU.",
        "severity": "medium",
    },
]


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _active_anomaly(service: str, region: str, timestamp: datetime) -> dict[str, Any] | None:
    for anomaly in ANOMALIES:
        if anomaly["service"] != service or anomaly["region"] != region:
            continue
        if _parse_dt(anomaly["start"]) <= timestamp <= _parse_dt(anomaly["end"]):
            return anomaly
    return None


def _metric_row(rng: random.Random, timestamp: datetime, service: str, region: str) -> dict[str, Any]:
    base_latency = {
        "checkout-api": 105,
        "billing-worker": 145,
        "auth-service": 75,
        "search-api": 95,
        "notification-service": 85,
        "analytics-pipeline": 180,
    }[service]
    base_throughput = {
        "checkout-api": 950,
        "billing-worker": 420,
        "auth-service": 1250,
        "search-api": 780,
        "notification-service": 360,
        "analytics-pipeline": 190,
    }[service]
    hour = timestamp.hour
    business_cycle = 1.0 + (0.22 if 8 <= hour <= 18 else -0.08)
    latency = rng.gauss(base_latency, base_latency * 0.08)
    error_rate = max(0.001, rng.gauss(0.009, 0.004))
    throughput = rng.gauss(base_throughput * business_cycle, base_throughput * 0.06)
    cpu = rng.gauss(42, 8)
    memory = rng.gauss(58, 7)
    queue_depth = max(0, rng.gauss(18, 8))
    anomaly = _active_anomaly(service, region, timestamp)

    label = "normal"
    if anomaly:
        label = anomaly["label"]
        if anomaly["anomaly_id"] == "ANOM-001":
            latency *= 3.7
            error_rate *= 8.5
            throughput *= 0.72
            cpu *= 1.35
            queue_depth *= 4.4
        elif anomaly["anomaly_id"] == "ANOM-002":
            latency *= 2.2
            error_rate *= 5.2
            throughput *= 0.61
            cpu *= 1.15
            queue_depth *= 5.6
        elif anomaly["anomaly_id"] == "ANOM-003":
            latency *= 2.8
            error_rate *= 3.2
            throughput *= 0.78
            cpu *= 1.9
            queue_depth *= 2.1

    saturation = min(1.0, (cpu / 100 * 0.35) + (queue_depth / 220 * 0.45) + (error_rate * 1.8))
    return {
        "timestamp": timestamp.isoformat(),
        "service": service,
        "region": region,
        "latency_ms": round(max(20, latency), 2),
        "error_rate": round(min(0.99, error_rate), 4),
        "throughput_rpm": round(max(1, throughput), 2),
        "cpu_pct": round(min(99, max(1, cpu)), 2),
        "memory_pct": round(min(99, max(1, memory)), 2),
        "queue_depth": round(max(0, queue_depth), 2),
        "saturation_score": round(saturation, 4),
        "anomaly_label": label,
    }


def _events() -> list[dict[str, str]]:
    return [
        {
            "timestamp": "2026-04-04T08:35:00",
            "service": "checkout-api",
            "region": "eu-central-1",
            "event_type": "deployment",
            "severity": "info",
            "actor": "release-bot",
            "description": "Deployed checkout-api v2.14.0 with cache TTL normalization and cart pricing changes.",
        },
        {
            "timestamp": "2026-04-04T09:20:00",
            "service": "checkout-api",
            "region": "eu-central-1",
            "event_type": "alert",
            "severity": "high",
            "actor": "monitoring",
            "description": "Checkout p95 latency and error budget burn exceeded the critical threshold.",
        },
        {
            "timestamp": "2026-04-04T16:10:00",
            "service": "checkout-api",
            "region": "eu-central-1",
            "event_type": "rollback",
            "severity": "info",
            "actor": "release-bot",
            "description": "Rolled back cache TTL normalization flag after elevated cache misses.",
        },
        {
            "timestamp": "2026-04-05T01:10:00",
            "service": "billing-worker",
            "region": "us-east-1",
            "event_type": "external_dependency",
            "severity": "medium",
            "actor": "status-sync",
            "description": "Payment provider reported intermittent timeout responses.",
        },
        {
            "timestamp": "2026-04-05T02:00:00",
            "service": "billing-worker",
            "region": "us-east-1",
            "event_type": "alert",
            "severity": "medium",
            "actor": "monitoring",
            "description": "Billing retry queue crossed 5x its normal overnight depth.",
        },
        {
            "timestamp": "2026-04-06T12:00:00",
            "service": "search-api",
            "region": "us-west-2",
            "event_type": "maintenance",
            "severity": "info",
            "actor": "scheduler",
            "description": "Started product index rebuild on shared search nodes.",
        },
        {
            "timestamp": "2026-04-06T13:05:00",
            "service": "search-api",
            "region": "us-west-2",
            "event_type": "alert",
            "severity": "medium",
            "actor": "monitoring",
            "description": "Search CPU saturation and p95 latency exceeded warning thresholds.",
        },
    ]


def _logs() -> list[dict[str, str]]:
    return [
        {
            "timestamp": "2026-04-04T09:05:00",
            "service": "checkout-api",
            "region": "eu-central-1",
            "level": "WARN",
            "message": "cache_miss_ratio=0.71 for cart-pricing cache after release v2.14.0",
        },
        {
            "timestamp": "2026-04-04T09:18:00",
            "service": "checkout-api",
            "region": "eu-central-1",
            "level": "ERROR",
            "message": "cart pricing request timed out while waiting on inventory dependency",
        },
        {
            "timestamp": "2026-04-04T10:02:00",
            "service": "checkout-api",
            "region": "eu-central-1",
            "level": "WARN",
            "message": "worker queue depth above threshold; backpressure enabled for checkout requests",
        },
        {
            "timestamp": "2026-04-05T01:25:00",
            "service": "billing-worker",
            "region": "us-east-1",
            "level": "ERROR",
            "message": "payment provider timeout; retry scheduled with exponential backoff",
        },
        {
            "timestamp": "2026-04-05T02:15:00",
            "service": "billing-worker",
            "region": "us-east-1",
            "level": "WARN",
            "message": "retry queue depth elevated; idempotency guard active",
        },
        {
            "timestamp": "2026-04-06T12:40:00",
            "service": "search-api",
            "region": "us-west-2",
            "level": "WARN",
            "message": "index rebuild consuming high CPU on shard group blue",
        },
        {
            "timestamp": "2026-04-06T13:30:00",
            "service": "search-api",
            "region": "us-west-2",
            "level": "ERROR",
            "message": "search request exceeded latency budget during index merge",
        },
    ]


def _incidents() -> list[dict[str, str]]:
    return [
        {
            "incident_id": "INC-101",
            "title": "Checkout latency after cache configuration release",
            "service": "checkout-api",
            "summary": (
                "A cache TTL change increased miss ratio, amplified dependency calls, and caused checkout backpressure."
            ),
            "resolution": (
                "Rollback the cache flag, warm the cart-pricing cache, and add a release guardrail on miss ratio."
            ),
        },
        {
            "incident_id": "INC-102",
            "title": "Billing retry growth during provider timeout",
            "service": "billing-worker",
            "summary": "External payment timeout responses caused retry amplification and elevated queue depth.",
            "resolution": (
                "Enable provider circuit breaker, cap retries, and drain queued jobs after provider recovery."
            ),
        },
        {
            "incident_id": "INC-103",
            "title": "Search latency during index rebuild",
            "service": "search-api",
            "summary": "A rebuild job shared CPU with production search traffic and increased p95 latency.",
            "resolution": "Move rebuild work to isolated nodes or throttle indexing during peak traffic.",
        },
    ]


def _runbooks() -> list[dict[str, str]]:
    return [
        {
            "runbook_id": "RB-001",
            "title": "Investigate latency and error spikes",
            "service_scope": "all",
            "content": (
                "Compare current metrics with a previous clean baseline, inspect recent deploys, "
                "check queue depth, and correlate logs with dependency errors."
            ),
        },
        {
            "runbook_id": "RB-002",
            "title": "Checkout cache rollback procedure",
            "service_scope": "checkout-api",
            "content": (
                "Disable the cache TTL feature flag, warm critical caches, watch miss ratio, "
                "and verify checkout p95 latency recovers for two consecutive windows."
            ),
        },
        {
            "runbook_id": "RB-003",
            "title": "Billing retry storm containment",
            "service_scope": "billing-worker",
            "content": (
                "Enable circuit breaker, cap retry concurrency, preserve idempotency keys, "
                "and drain delayed jobs gradually."
            ),
        },
        {
            "runbook_id": "RB-004",
            "title": "Search index rebuild isolation",
            "service_scope": "search-api",
            "content": (
                "Throttle index rebuild tasks, move rebuilds away from live query nodes, "
                "and watch CPU saturation and p95 latency."
            ),
        },
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def generate_synthetic_data(output_dir: Path, seed: int = 7) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    metrics = []
    for offset in range(HOURS):
        timestamp = START + timedelta(hours=offset)
        for service in SERVICES:
            for region in REGIONS:
                metrics.append(_metric_row(rng, timestamp, service, region))

    _write_csv(output_dir / "metrics.csv", metrics)
    _write_csv(output_dir / "events.csv", _events())
    _write_csv(output_dir / "anomaly_labels.csv", ANOMALIES)
    _write_jsonl(output_dir / "logs.jsonl", _logs())
    _write_jsonl(output_dir / "incidents.jsonl", _incidents())
    _write_jsonl(output_dir / "runbooks.jsonl", _runbooks())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic SaaS operations data.")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    generate_synthetic_data(args.output, seed=args.seed)
    print(f"Synthetic data written to {args.output}")


if __name__ == "__main__":
    main()
