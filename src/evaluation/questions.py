from __future__ import annotations

EVAL_CASES = [
    {
        "id": "checkout_cache_regression",
        "question": "Why did checkout-api latency and errors spike in eu-central-1 on April 4?",
        "expected_intent": "incident_investigation",
        "required_terms": ["checkout-api", "cache", "deployment", "queue"],
        "min_confidence": 0.8,
    },
    {
        "id": "billing_provider_timeout",
        "question": "Investigate the billing-worker retry queue anomaly in us-east-1 on April 5.",
        "expected_intent": "incident_investigation",
        "required_terms": ["billing-worker", "payment", "retry", "queue"],
        "min_confidence": 0.75,
    },
    {
        "id": "search_cpu_contention",
        "question": "What caused search-api latency to increase in us-west-2 on April 6?",
        "expected_intent": "incident_investigation",
        "required_terms": ["search-api", "index", "cpu", "rebuild"],
        "min_confidence": 0.75,
    },
    {
        "id": "ops_summary",
        "question": "Give me a performance summary for checkout-api on April 4.",
        "expected_intent": "performance_summary",
        "required_terms": ["checkout-api", "latency", "error", "baseline"],
        "min_confidence": 0.65,
    },
]
