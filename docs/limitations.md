# Limitations

- The dataset is synthetic and intentionally small.
- The text retrieval implementation is lightweight keyword scoring, not a production vector database.
- The mock LLM provider is deterministic and does not provide open-ended language reasoning.
- Ollama quality depends on the local model selected by the user.
- The planner uses pragmatic pattern matching for dates, services, regions, and metrics.
- The evaluation suite is behavior-focused and small; a real production system would need larger datasets, adversarial questions, retrieval quality metrics, and human review.
- The API has no authentication because this is designed for local demonstration.

## Future Work

- Add a Streamlit or lightweight web UI.
- Add embeddings as an optional local retrieval backend.
- Add richer temporal reasoning and anomaly detection.
- Add tracing output in OpenTelemetry format.
- Add more eval cases and retrieval-specific metrics.
