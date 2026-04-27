from __future__ import annotations

import argparse
import json
import shutil
import textwrap

from agents.pipeline import OperationsAnalystPipeline
from utils.config import get_settings
from utils.logging import configure_logging

DEFAULT_QUESTION = "Why did checkout-api latency and errors spike in eu-central-1 on April 4?"
SCENARIOS = {
    "incident": DEFAULT_QUESTION,
    "anomaly": "Investigate the billing-worker retry queue anomaly in us-east-1 on April 5.",
    "debugging": "What caused search-api latency to increase in us-west-2 on April 6?",
}
SECTION_TITLES = {"Root Cause", "Key Signals", "Recommended Actions", "Confidence"}
MAX_WRAP_WIDTH = 88


def _print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def _wrap_width() -> int:
    terminal_width = shutil.get_terminal_size(fallback=(MAX_WRAP_WIDTH, 24)).columns
    return max(48, min(MAX_WRAP_WIDTH, terminal_width))


def _wrap_cli_text(text: str) -> str:
    width = _wrap_width()
    wrapped_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            wrapped_lines.append("")
        elif line in SECTION_TITLES:
            wrapped_lines.append(line)
        elif line.startswith("- "):
            wrapped_lines.append(
                textwrap.fill(
                    line[2:].strip(),
                    width=width,
                    initial_indent="- ",
                    subsequent_indent="  ",
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
        else:
            wrapped_lines.append(
                textwrap.fill(
                    line,
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
    return "\n".join(wrapped_lines)


def _format_bullet(text: str) -> str:
    return textwrap.fill(
        text,
        width=_wrap_width(),
        initial_indent="- ",
        subsequent_indent="  ",
        break_long_words=False,
        break_on_hyphens=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IncidentLens incident investigation scenarios.")
    parser.add_argument("--question", "-q", help="Custom operations question to investigate.")
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="incident",
        help="Built-in demo scenario to run when --question is not provided.",
    )
    parser.add_argument("--list-scenarios", action="store_true", help="Show built-in demo scenarios and exit.")
    parser.add_argument("--json", action="store_true", help="Print the full response as JSON.")
    parser.add_argument("--details", action="store_true", help="Print investigation plan and trace around the answer.")
    args = parser.parse_args()

    if args.list_scenarios:
        print("IncidentLens demo scenarios")
        for name, question in SCENARIOS.items():
            print(f"- {name}: {question}")
        return

    settings = get_settings()
    configure_logging(settings.log_level)
    question = args.question or SCENARIOS[args.scenario]
    result = OperationsAnalystPipeline(settings).answer(question)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    if not args.details:
        print(_wrap_cli_text(result.reasoning.answer))
        return

    print("\nIncidentLens")
    print("=" * 12)
    print(f"Question: {result.question}")
    print(f"Provider: {settings.llm_provider}")

    _print_section("Investigation Plan")
    print(_format_bullet(f"Intent: {result.route.intent}"))
    print(_format_bullet(f"Service: {result.plan.service or 'all'}"))
    print(_format_bullet(f"Region: {result.plan.region or 'all'}"))
    print(_format_bullet(f"Window: {result.plan.time_window.start} to {result.plan.time_window.end}"))
    print(_format_bullet(f"Metrics: {', '.join(result.plan.metrics)}"))

    _print_section("Answer")
    print(_wrap_cli_text(result.reasoning.answer))

    _print_section("Investigation Trace")
    for step in result.reasoning.intermediate_steps:
        print(_format_bullet(step))


if __name__ == "__main__":
    main()
