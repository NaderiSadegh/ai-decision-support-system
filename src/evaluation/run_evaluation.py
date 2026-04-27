from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from agents.pipeline import OperationsAnalystPipeline
from evaluation.questions import EVAL_CASES
from utils.config import get_settings


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    score: float
    passed: bool
    details: list[str]


def evaluate_case(pipeline: OperationsAnalystPipeline, case: dict) -> CaseResult:
    result = pipeline.answer(case["question"])
    answer_text = result.reasoning.answer.lower()
    details = []
    checks = []

    intent_ok = result.route.intent == case["expected_intent"]
    checks.append(intent_ok)
    details.append(f"intent={'pass' if intent_ok else 'fail'} ({result.route.intent})")

    confidence_ok = result.reasoning.confidence >= case["min_confidence"]
    checks.append(confidence_ok)
    details.append(f"confidence={'pass' if confidence_ok else 'fail'} ({result.reasoning.confidence:.2f})")

    term_results = []
    for term in case["required_terms"]:
        ok = term.lower() in answer_text or term.lower() in result.reasoning.likely_cause.lower()
        term_results.append(ok)
        checks.append(ok)
    details.append(
        "terms="
        + ", ".join(
            f"{term}:{'pass' if ok else 'fail'}" for term, ok in zip(case["required_terms"], term_results, strict=True)
        )
    )

    score = sum(1 for check in checks if check) / len(checks)
    return CaseResult(case_id=case["id"], score=round(score, 3), passed=score >= 0.8, details=details)


def run_evaluation(output: Path, min_score: float) -> tuple[float, list[CaseResult]]:
    os.environ.setdefault("LLM_PROVIDER", "mock")
    settings = get_settings()
    pipeline = OperationsAnalystPipeline(settings)
    results = [evaluate_case(pipeline, case) for case in EVAL_CASES]
    average = round(sum(item.score for item in results) / len(results), 3)
    write_report(output, average, results, min_score)
    return average, results


def write_report(output: Path, average: float, results: list[CaseResult], min_score: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Evaluation Report",
        "",
        "Provider: `mock`",
        f"Average score: `{average:.3f}`",
        f"Required average score: `{min_score:.3f}`",
        "",
        "| Case | Score | Pass | Details |",
        "| --- | ---: | --- | --- |",
    ]
    for result in results:
        lines.append(
            f"| `{result.case_id}` | {result.score:.3f} | {'yes' if result.passed else 'no'} | "
            f"{'; '.join(result.details)} |"
        )
    lines.extend(
        [
            "",
            "The evaluation checks deterministic behavior against synthetic incidents only.",
            "CI writes its report to a temporary path and validates thresholds without committing generated output.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the AI Operations Analyst.")
    parser.add_argument("--output", type=Path, default=Path("reports/evaluation_report.md"))
    parser.add_argument("--min-score", type=float, default=0.75)
    args = parser.parse_args()
    average, _ = run_evaluation(args.output, args.min_score)
    print(f"Evaluation average score: {average:.3f}")
    if average < args.min_score:
        raise SystemExit(f"Evaluation score {average:.3f} is below threshold {args.min_score:.3f}")


if __name__ == "__main__":
    main()
