from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from data.generate_synthetic import generate_synthetic_data
from retrieval.loaders import read_csv

REQUIRED_FILES = [
    "metrics.csv",
    "events.csv",
    "anomaly_labels.csv",
    "logs.jsonl",
    "incidents.jsonl",
    "runbooks.jsonl",
]


class OperationsStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._lock = RLock()
        ensure_synthetic_data(data_dir)
        self.db_path = data_dir / "operations.sqlite"
        self._connect_and_prepare()

    def _connect_and_prepare(self) -> None:
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()
        self._load_if_empty()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp TEXT NOT NULL,
                service TEXT NOT NULL,
                region TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                error_rate REAL NOT NULL,
                throughput_rpm REAL NOT NULL,
                cpu_pct REAL NOT NULL,
                memory_pct REAL NOT NULL,
                queue_depth REAL NOT NULL,
                saturation_score REAL NOT NULL,
                anomaly_label TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                timestamp TEXT NOT NULL,
                service TEXT NOT NULL,
                region TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                actor TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS anomaly_labels (
                anomaly_id TEXT NOT NULL,
                service TEXT NOT NULL,
                region TEXT NOT NULL,
                start TEXT NOT NULL,
                end TEXT NOT NULL,
                label TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                severity TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def _load_if_empty(self) -> None:
        count = self.connection.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
        if count:
            return
        metrics = read_csv(self.data_dir / "metrics.csv")
        events = read_csv(self.data_dir / "events.csv")
        labels = read_csv(self.data_dir / "anomaly_labels.csv")
        self.connection.executemany(
            """
            INSERT INTO metrics VALUES (
                :timestamp, :service, :region, :latency_ms, :error_rate, :throughput_rpm,
                :cpu_pct, :memory_pct, :queue_depth, :saturation_score, :anomaly_label
            )
            """,
            metrics,
        )
        self.connection.executemany(
            """
            INSERT INTO events VALUES (
                :timestamp, :service, :region, :event_type, :severity, :actor, :description
            )
            """,
            events,
        )
        self.connection.executemany(
            """
            INSERT INTO anomaly_labels VALUES (
                :anomaly_id, :service, :region, :start, :end, :label, :root_cause, :severity
            )
            """,
            labels,
        )
        self.connection.commit()

    def metric_summary(self, start: str, end: str, service: str | None, region: str | None) -> list[dict[str, Any]]:
        conditions = ["timestamp BETWEEN :start AND :end"]
        params: dict[str, Any] = {"start": start, "end": end}
        if service:
            conditions.append("service = :service")
            params["service"] = service
        if region:
            conditions.append("region = :region")
            params["region"] = region
        sql = f"""
            SELECT
                service,
                region,
                AVG(latency_ms) AS avg_latency_ms,
                AVG(error_rate) AS avg_error_rate,
                AVG(throughput_rpm) AS avg_throughput_rpm,
                AVG(cpu_pct) AS avg_cpu_pct,
                AVG(queue_depth) AS avg_queue_depth,
                MAX(saturation_score) AS max_saturation_score,
                COUNT(*) AS samples
            FROM metrics
            WHERE {" AND ".join(conditions)}
            GROUP BY service, region
            ORDER BY max_saturation_score DESC, avg_error_rate DESC, avg_latency_ms DESC
            LIMIT 10
        """
        with self._lock:
            return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def baseline_summary(self, start: str, end: str, service: str, region: str) -> dict[str, Any] | None:
        sql = """
            SELECT
                AVG(latency_ms) AS avg_latency_ms,
                AVG(error_rate) AS avg_error_rate,
                AVG(throughput_rpm) AS avg_throughput_rpm,
                AVG(cpu_pct) AS avg_cpu_pct,
                AVG(queue_depth) AS avg_queue_depth,
                MAX(saturation_score) AS max_saturation_score,
                COUNT(*) AS samples
            FROM metrics
            WHERE timestamp BETWEEN :start AND :end
              AND service = :service
              AND region = :region
              AND anomaly_label = 'normal'
        """
        with self._lock:
            row = self.connection.execute(
                sql,
                {"start": start, "end": end, "service": service, "region": region},
            ).fetchone()
        return dict(row) if row and row["samples"] else None

    def events_between(self, start: str, end: str, service: str | None, region: str | None) -> list[dict[str, Any]]:
        conditions = ["timestamp BETWEEN :start AND :end"]
        params: dict[str, Any] = {"start": start, "end": end}
        if service:
            conditions.append("service = :service")
            params["service"] = service
        if region:
            conditions.append("region = :region")
            params["region"] = region
        sql = f"""
            SELECT timestamp, service, region, event_type, severity, actor, description
            FROM events
            WHERE {" AND ".join(conditions)}
            ORDER BY timestamp ASC
            LIMIT 20
        """
        with self._lock:
            return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def anomaly_labels(self, start: str, end: str, service: str | None, region: str | None) -> list[dict[str, Any]]:
        conditions = ["start <= :end", "end >= :start"]
        params: dict[str, Any] = {"start": start, "end": end}
        if service:
            conditions.append("service = :service")
            params["service"] = service
        if region:
            conditions.append("region = :region")
            params["region"] = region
        sql = f"""
            SELECT anomaly_id, service, region, start, end, label, root_cause, severity
            FROM anomaly_labels
            WHERE {" AND ".join(conditions)}
            ORDER BY severity DESC, start ASC
        """
        with self._lock:
            return [dict(row) for row in self.connection.execute(sql, params).fetchall()]


def ensure_synthetic_data(data_dir: Path) -> None:
    if all((data_dir / filename).exists() for filename in REQUIRED_FILES):
        return
    generate_synthetic_data(data_dir)
