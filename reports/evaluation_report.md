# Evaluation Report

Provider: `mock`
Average score: `1.000`
Required average score: `0.750`

| Case | Score | Pass | Details |
| --- | ---: | --- | --- |
| `checkout_cache_regression` | 1.000 | yes | intent=pass (incident_investigation); confidence=pass (0.95); terms=checkout-api:pass, cache:pass, deployment:pass, queue:pass |
| `billing_provider_timeout` | 1.000 | yes | intent=pass (incident_investigation); confidence=pass (0.95); terms=billing-worker:pass, payment:pass, retry:pass, queue:pass |
| `search_cpu_contention` | 1.000 | yes | intent=pass (incident_investigation); confidence=pass (0.95); terms=search-api:pass, index:pass, cpu:pass, rebuild:pass |
| `ops_summary` | 1.000 | yes | intent=pass (performance_summary); confidence=pass (0.90); terms=checkout-api:pass, latency:pass, error:pass, baseline:pass |

The evaluation checks deterministic behavior against synthetic incidents only.
CI writes its report to a temporary path and validates thresholds without committing generated output.
