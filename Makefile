PYTHON ?= python3
EVAL_REPORT ?= reports/evaluation_report.md
CI_EVAL_REPORT ?= /tmp/ai_ops_evaluation_report.md
LLM_PROVIDER ?= mock
OLLAMA_MODEL ?= llama3.1:8b
OLLAMA_BASE_URL ?= http://localhost:11434
DEMO_QUESTION ?= Why did checkout-api latency and errors spike in eu-central-1 on April 4?

.PHONY: install data demo demo-scenarios test eval lint format ci api docker-build

install:
	$(PYTHON) -m pip install -e ".[dev]"

data:
	$(PYTHON) -m data.generate_synthetic --output data/synthetic

demo:
	@LLM_PROVIDER=$(LLM_PROVIDER) OLLAMA_MODEL=$(OLLAMA_MODEL) OLLAMA_BASE_URL=$(OLLAMA_BASE_URL) $(PYTHON) -m app.cli --question "$(DEMO_QUESTION)"

demo-scenarios:
	@$(PYTHON) -m app.cli --list-scenarios

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
