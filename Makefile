PYTHON ?= python3
EVAL_REPORT ?= reports/evaluation_report.md
CI_EVAL_REPORT ?= /tmp/ai_ops_evaluation_report.md

.PHONY: install data demo test eval lint format ci api docker-build

install:
	$(PYTHON) -m pip install -e ".[dev]"

data:
	$(PYTHON) -m data.generate_synthetic --output data/synthetic

demo:
	LLM_PROVIDER=mock $(PYTHON) -m app.cli --question "Why did checkout-api latency and errors spike in eu-central-1 on April 4?"

test:
	$(PYTHON) -m pytest

eval:
	LLM_PROVIDER=mock $(PYTHON) -m evaluation.run_evaluation --output $(EVAL_REPORT) --min-score 0.75

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

ci:
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pytest
	LLM_PROVIDER=mock $(PYTHON) -m evaluation.run_evaluation --output $(CI_EVAL_REPORT) --min-score 0.75

api:
	$(PYTHON) -m app.api

docker-build:
	docker build -t ai-decision-support-system .

