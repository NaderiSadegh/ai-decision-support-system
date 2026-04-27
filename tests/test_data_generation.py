from __future__ import annotations

from data.generate_synthetic import generate_synthetic_data
from retrieval.loaders import read_csv, read_jsonl


def test_generate_synthetic_data(tmp_path):
    generate_synthetic_data(tmp_path)

    metrics = read_csv(tmp_path / "metrics.csv")
    logs = read_jsonl(tmp_path / "logs.jsonl")

    assert len(metrics) == 3024
    assert any(row["anomaly_label"] == "cache_misconfiguration_after_deploy" for row in metrics)
    assert any("cache_miss_ratio" in row["message"] for row in logs)
