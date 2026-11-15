"""LangGraph bill-ingestion workflow.

extract -> classify -> check -> (ask <-> check) -> preview -> END

The graph only reads commerce state and produces a preview (a set of proposed changes).
It never applies changes or calls a connector: confirmation is a commerce service (ADR 0003).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.extraction import ExtractionFailed, Extractor
from commerce.audit import record
from commerce.intake.matching import classify
from commerce.intake.normalize import normalize_extraction
from commerce.intake.preview import build_preview
from commerce.intake.questions import apply_answers, open_questions
from commerce.repositories import Repositories
from contracts.ingestion import Answer, IngestionStatus, Question, WorkingLine


class IngestionState(TypedDict, total=False):
    ingestion_id: str
    file_path: str
    media_type: str
    failed: bool
    lines: list[dict[str, Any]]
    questions: list[dict[str, Any]]
    preview: dict[str, Any] | None
    preview_version: int


@dataclass
class GraphDeps:
    repos: Repositories
    extractor: Extractor
    channels: Callable[[], list[str]]


def lines_of(state: IngestionState) -> list[WorkingLine]:
    return [WorkingLine.model_validate(x) for x in state.get("lines", [])]


def questions_of(state: IngestionState) -> list[Question]:
    return [Question.model_validate(x) for x in state.get("questions", [])]


def _dump(items: list[Any]) -> list[dict[str, Any]]:
    return [i.model_dump(mode="json") for i in items]


def build_ingestion_graph(deps: GraphDeps, checkpointer: Any):
    repos = deps.repos

    def set_status(iid: str, status: IngestionStatus, **extra: Any) -> None:
        ing = repos.ingestions.get(iid)
        if ing is None:
            return
        changed = ing.status != status or any(getattr(ing, k) != v for k, v in extra.items())
        if not changed:
            return
        ing = ing.model_copy(update={"status": status, **extra})
        repos.ingestions.update(ing)
        record(
            repos.audit,
            correlation_id=iid,
            event_type=f"ingestion.{status.value}",
            summary=f"Ingestion is now {status.value}",
        )

    def extract(state: IngestionState) -> IngestionState:
        iid = state["ingestion_id"]
        set_status(iid, IngestionStatus.EXTRACTING)
        try:
            content = Path(state["file_path"]).read_bytes()
            result = deps.extractor.extract(content, state["media_type"])
        except ExtractionFailed as exc:
            set_status(iid, IngestionStatus.FAILED, error=f"extraction_failed: {exc}")
            return {"failed": True}
        except OSError:
            set_status(iid, IngestionStatus.FAILED, error="extraction_failed: bill unreadable")
            return {"failed": True}
        record(
            repos.audit,
            correlation_id=iid,
            event_type="agent.extraction.completed",
            actor=f"agent:{result.provider}/{result.model}",
            summary=f"Extracted {len(result.extraction.lines)} bill lines"
            + (" (recorded fallback, model disabled)" if result.fallback_used else ""),
        )
        if result.fallback_used:
            set_status(iid, IngestionStatus.EXTRACTING, fallback_used=True)
        lines = normalize_extraction(result.extraction)
        return {"failed": False, "lines": _dump(lines), "preview_version": 0}

    def classify_node(state: IngestionState) -> IngestionState:
        lines = classify(lines_of(state), repos.catalogue)
        kinds = ", ".join(f"{ln.id}={ln.kind}" for ln in lines)
        record(
            repos.audit,
            correlation_id=state["ingestion_id"],
            event_type="intake.classified",
            summary=f"Classified lines: {kinds or 'none'}",
        )
        return {"lines": _dump(lines)}

    def check(state: IngestionState) -> IngestionState:
        set_status(state["ingestion_id"], IngestionStatus.CHECKING)
        qs = open_questions(lines_of(state), repos.catalogue, deps.channels())
        return {"questions": _dump(qs), "preview": None}

    def ask(state: IngestionState) -> IngestionState:
        iid = state["ingestion_id"]
        qs = questions_of(state)
        set_status(iid, IngestionStatus.NEEDS_INPUT)
        raw_answers = interrupt({"questions": _dump(qs)})
        answers = [Answer.model_validate(a) for a in raw_answers]
        lines = apply_answers(lines_of(state), qs, answers, repos.catalogue)
        record(
            repos.audit,
            correlation_id=iid,
            event_type="intake.answers.applied",
            actor="owner",
            summary=f"Owner answered {len(answers)} question(s)",
        )
        return {"lines": _dump(lines)}

    def preview(state: IngestionState) -> IngestionState:
        iid = state["ingestion_id"]
        version = state.get("preview_version", 0) + 1
        p = build_preview(
            ingestion_id=iid,
            lines=lines_of(state),
            catalogue=repos.catalogue,
            inventory=repos.inventory,
            listings=repos.listings,
            channels=deps.channels(),
            version=version,
        )
        record(
            repos.audit,
            correlation_id=iid,
            event_type="action.proposed",
            actor="agent:catalogue-builder",
            summary=f"Preview v{version} proposes {len(p.lines)} line change(s), hash {p.hash[:12]}",
        )
        set_status(iid, IngestionStatus.AWAITING_CONFIRMATION)
        return {"preview": p.model_dump(mode="json"), "preview_version": version}

    def after_extract(state: IngestionState) -> str:
        return END if state.get("failed") else "classify"

    def after_check(state: IngestionState) -> str:
        return (
            "ask" if any(q.get("blocking", True) for q in state.get("questions", [])) else "preview"
        )

    g = StateGraph(IngestionState)
    g.add_node("extract", extract)
    g.add_node("classify", classify_node)
    g.add_node("check", check)
    g.add_node("ask", ask)
    g.add_node("preview", preview)
    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", after_extract, ["classify", END])
    g.add_edge("classify", "check")
    g.add_conditional_edges("check", after_check, ["ask", "preview"])
    g.add_edge("ask", "check")
    g.add_edge("preview", END)
    return g.compile(checkpointer=checkpointer)
