from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]+")


@dataclass(frozen=True)
class SearchResult:
    document: dict[str, Any]
    score: float


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class TextIndex:
    def __init__(self, documents: list[dict[str, Any]], text_fields: list[str]) -> None:
        self.documents = documents
        self.text_fields = text_fields
        self.doc_tokens = [tokenize(self._document_text(doc)) for doc in documents]
        self.doc_freq: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            self.doc_freq.update(set(tokens))

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        query_counts = Counter(query_tokens)
        scored: list[SearchResult] = []
        total_docs = max(1, len(self.documents))
        for doc, tokens in zip(self.documents, self.doc_tokens, strict=True):
            token_counts = Counter(tokens)
            score = 0.0
            for token, query_weight in query_counts.items():
                if token not in token_counts:
                    continue
                idf = math.log((1 + total_docs) / (1 + self.doc_freq[token])) + 1.0
                score += query_weight * token_counts[token] * idf
            if score > 0:
                scored.append(SearchResult(document=doc, score=round(score, 4)))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def _document_text(self, doc: dict[str, Any]) -> str:
        return " ".join(str(doc.get(field, "")) for field in self.text_fields)
