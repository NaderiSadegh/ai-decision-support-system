# Design Decisions

## Use A New Domain

The project uses synthetic SaaS/cloud operations rather than any employer-specific or manufacturing workflow. This keeps the public artifact safe while preserving relevant AI Engineering depth: mixed retrieval, agent workflow, evidence synthesis, and evaluation.

## Deterministic Default LLM

`LLM_PROVIDER=mock` is the default. It makes the assistant runnable in CI and local environments without keys, GPUs, or network services. The mock provider does not pretend to be intelligent; the system's retrieval and reasoning layers produce the grounded answer.

## Optional Ollama Integration

Ollama support demonstrates model abstraction and local open-model usage without making the project dependent on an external API. If Ollama is unavailable, users can still run every core workflow with `mock`.

## Lightweight Retrieval

The project uses SQLite and a simple token-scoring text index instead of managed vector databases. That choice keeps the repo portable and easy to run while still showing how structured and unstructured evidence paths are separated and combined.

## Evaluation As A First-Class Feature

The evaluation suite checks routing, confidence, and answer evidence terms. It is not a substitute for human judgment, but it prevents regressions in the main product behavior and demonstrates production thinking.

## Product-Like Surface

The CLI shows intermediate steps for explainability. The FastAPI backend exposes a clean `/ask` endpoint for integration. Docker and Compose make it easy to run the system as a service.
