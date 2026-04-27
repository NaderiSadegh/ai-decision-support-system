# Architecture

AI Operations Analyst is built as a small but production-shaped investigation system. The default path is deterministic so it can run in CI, while the LLM interface can be switched to Ollama for local open-model demos.

## Runtime Flow

1. The user asks an operational question.
2. `QueryRouter` classifies the intent, such as incident investigation, remediation guidance, or performance summary.
3. `Planner` extracts service, region, metrics, and time window.
4. `StructuredRetriever` queries SQLite-backed synthetic metrics, events, and anomaly labels.
5. `TextRetriever` searches synthetic logs, incident summaries, and runbooks.
6. `RootCauseReasoner` compares current metrics with clean baselines, correlates events and text evidence, selects a likely cause, assigns confidence, and produces recommendations.
7. The selected LLM provider formats the final answer.

## Components

### `src/app`

Contains the CLI and FastAPI entrypoints. The CLI is used by `make demo`; the API powers Docker and local service demos.

### `src/agents`

Contains workflow orchestration:

- router: intent and retrieval strategy
- planner: service, region, metric, and time-window extraction
- pipeline: end-to-end user question to answer flow

### `src/retrieval`

Contains two retrieval paths:

- structured retrieval through SQLite tables generated from synthetic CSV files
- lightweight text retrieval over JSONL logs, incidents, and runbooks

### `src/reasoning`

Contains shared dataclasses and the root-cause synthesis logic. The reasoner is deliberately deterministic around evidence selection so tests and evaluation are stable.

### `src/llm`

Defines the LLM provider abstraction:

- `mock`: deterministic, default, CI-safe
- `ollama`: optional local model provider

### `src/evaluation`

Contains test questions and threshold-based evaluation. CI writes reports to a temporary path and fails if the score drops below the configured threshold.

## Data Model

The synthetic data represents a generic SaaS platform:

- services: `checkout-api`, `billing-worker`, `auth-service`, `search-api`, `notification-service`, `analytics-pipeline`
- regions: `us-east-1`, `us-west-2`, `eu-central-1`
- metrics: latency, error rate, throughput, CPU, memory, queue depth, saturation score
- events: deployments, alerts, rollbacks, dependency issues, maintenance
- logs: warning/error events with operational messages
- incidents: historical synthetic incident summaries
- runbooks: remediation guidance
- labels: known synthetic anomaly windows for evaluation

## Safety Boundary

The project has no dependency on private platforms, private schemas, cloud credentials, or employer data. It is intentionally generic and synthetic.

