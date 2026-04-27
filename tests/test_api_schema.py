from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import create_app


def test_ask_endpoint_declares_json_request_body(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_ANALYST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    schema = create_app().openapi()
    ask_operation = schema["paths"]["/ask"]["post"]

    assert "requestBody" in ask_operation
    assert "application/json" in ask_operation["requestBody"]["content"]
    assert "checkout_latency" in ask_operation["requestBody"]["content"]["application/json"]["examples"]
    assert (
        schema["components"]["schemas"]["AskResponse"]["properties"]["result"]["$ref"]
        == "#/components/schemas/AnalysisResponse"
    )
    assert "additionalProperties" not in schema["components"]["schemas"]["AskResponse"]["properties"]["result"]


def test_ask_endpoint_returns_analysis_response(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_ANALYST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    client = TestClient(create_app())
    response = client.post(
        "/ask",
        json={"question": "Why did checkout-api latency spike in eu-central-1 on April 4?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["route"]["intent"] == "incident_investigation"
    assert "cache" in body["result"]["reasoning"]["likely_cause"].lower()
