from __future__ import annotations

from evaluation.run_evaluation import run_evaluation


def test_evaluation_passes_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_ANALYST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    average, results = run_evaluation(tmp_path / "report.md", min_score=0.75)

    assert average >= 0.75
    assert all(result.passed for result in results)
    assert (tmp_path / "report.md").exists()
