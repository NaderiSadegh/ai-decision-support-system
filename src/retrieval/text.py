from __future__ import annotations

from pathlib import Path

from reasoning.models import InvestigationPlan, TextEvidence
from retrieval.loaders import read_jsonl
from retrieval.text_index import TextIndex


class TextRetriever:
    def __init__(self, data_dir: Path, top_k: int = 5) -> None:
        self.data_dir = data_dir
        self.top_k = top_k
        docs = []
        for source_type, filename in [
            ("log", "logs.jsonl"),
            ("incident", "incidents.jsonl"),
            ("runbook", "runbooks.jsonl"),
        ]:
            for row in read_jsonl(data_dir / filename):
                row["_source_type"] = source_type
                docs.append(row)
        self.index = TextIndex(
            docs,
            text_fields=["service", "region", "level", "message", "title", "summary", "resolution", "content"],
        )

    def retrieve(self, question: str, plan: InvestigationPlan) -> list[TextEvidence]:
        query_parts = [question, plan.service or "", plan.region or "", " ".join(plan.metrics)]
        results = self.index.search(" ".join(query_parts), top_k=self.top_k)
        evidence: list[TextEvidence] = []
        for result in results:
            doc = result.document
            source_type = doc.get("_source_type", "document")
            source_id = (
                doc.get("incident_id")
                or doc.get("runbook_id")
                or f"{doc.get('timestamp', 'unknown')}:{doc.get('service', 'unknown')}"
            )
            title = doc.get("title") or doc.get("message") or source_id
            content = doc.get("content") or doc.get("summary") or doc.get("resolution") or doc.get("message") or ""
            evidence.append(
                TextEvidence(
                    source_type=source_type,
                    source_id=str(source_id),
                    title=str(title),
                    content=str(content),
                    score=result.score,
                )
            )
        return evidence
