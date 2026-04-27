# IncidentLens Demo Guide

This guide shows the fastest ways to demo IncidentLens locally. All data is synthetic.

## 1. Run The Default CLI Demo

```bash
make demo
```

Expected output shape:

```text
Root Cause
<one concise sentence>

Key Signals
- <signal 1>
- <signal 2>
- <signal 3>

Recommended Actions
- <action 1>
- <action 2>
- <action 3>

Confidence
<0.00-1.00>
```

## 2. List Demo Scenarios

```bash
make demo-scenarios
```

Built-in scenarios:

- incident: checkout-api cache regression
- anomaly: billing-worker retry queue anomaly
- debugging: search-api index rebuild contention

Run a specific question:

```bash
DEMO_QUESTION="What caused search-api latency to increase in us-west-2 on April 6?" make demo
```

## 3. Start The API

```bash
make api
```

Open:

```text
http://localhost:8000/docs
```

In Swagger:

1. Open `POST /ask`.
2. Click `Try it out`.
3. Paste:

```json
{
  "question": "Why did checkout-api latency spike in eu-central-1 on April 4?"
}
```

4. Click `Execute`.

## 4. Optional Ollama Demo

Install and run Ollama, then pull a model:

```bash
ollama pull llama3.1:8b
```

Run:

```bash
LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1:8b make demo
```

The Ollama prompt enforces the same clean plain-text incident brief format as mock mode.

## Example Questions

```text
Why did checkout-api latency spike in eu-central-1 on April 4?
Investigate the billing-worker retry queue anomaly in us-east-1 on April 5.
What caused search-api latency to increase in us-west-2 on April 6?
```

