from __future__ import annotations

from agents.planner import Planner
from agents.router import QueryRouter
from llm.factory import build_llm
from reasoning.analyzer import RootCauseReasoner
from reasoning.models import AnalysisResult, StructuredEvidence
from retrieval.sqlite_store import OperationsStore
from retrieval.structured import StructuredRetriever
from retrieval.text import TextRetriever
from utils.config import Settings, get_settings


class OperationsAnalystPipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.store = OperationsStore(self.settings.data_dir)
        self.router = QueryRouter()
        self.planner = Planner()
        self.structured_retriever = StructuredRetriever(self.store)
        self.text_retriever = TextRetriever(self.settings.data_dir, top_k=self.settings.retrieval_top_k)
        self.reasoner = RootCauseReasoner(build_llm(self.settings))

    def answer(self, question: str) -> AnalysisResult:
        route = self.router.route(question)
        plan = self.planner.create_plan(question, route)
        structured = (
            self.structured_retriever.retrieve(plan) if route.use_structured_retrieval else StructuredEvidence()
        )
        text_evidence = self.text_retriever.retrieve(question, plan) if route.use_text_retrieval else []
        reasoning = self.reasoner.synthesize(route, plan, structured, text_evidence)
        return AnalysisResult(
            question=question,
            route=route,
            plan=plan,
            structured_evidence=structured,
            text_evidence=text_evidence,
            reasoning=reasoning,
        )
