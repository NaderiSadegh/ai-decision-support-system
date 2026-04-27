from __future__ import annotations

import argparse
import json

from agents.pipeline import OperationsAnalystPipeline
from utils.config import get_settings
from utils.logging import configure_logging

DEFAULT_QUESTION = "Why did checkout-api latency and errors spike in eu-central-1 on April 4?"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Operations Analyst pipeline.")
    parser.add_argument("--question", "-q", default=DEFAULT_QUESTION)
    parser.add_argument("--json", action="store_true", help="Print the full response as JSON.")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    result = OperationsAnalystPipeline(settings).answer(args.question)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print("\nAI Operations Analyst")
    print("=" * 22)
    print(f"Question: {result.question}\n")
    print("Route")
    print(f"- Intent: {result.route.intent}")
    print(f"- Rationale: {result.route.rationale}\n")
    print("Plan")
    print(f"- Service: {result.plan.service or 'all'}")
    print(f"- Region: {result.plan.region or 'all'}")
    print(f"- Window: {result.plan.time_window.start} to {result.plan.time_window.end}")
    print(f"- Metrics: {', '.join(result.plan.metrics)}\n")
    print("Answer")
    print(result.reasoning.answer)
    print("\nIntermediate Steps")
    for step in result.reasoning.intermediate_steps:
        print(f"- {step}")


if __name__ == "__main__":
    main()
