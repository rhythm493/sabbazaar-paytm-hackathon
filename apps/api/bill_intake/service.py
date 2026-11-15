"""Application service composing the ingestion graph (agents) with commerce services."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from langgraph.types import Command

from sabbazaar_agents.ingestion_graph import lines_of, questions_of
from sabbazaar_commerce.audit_log import record
from sabbazaar_commerce.domain import AuditEvent, Ingestion
from sabbazaar_commerce.intake.apply import ApplyError, ApplyService
from sabbazaar_commerce.intake.questions import AnswerError, apply_answers, parse_owner_value
from sabbazaar_commerce.repositories import Repositories
from sabbazaar_connectors.registry import ConnectorRegistry
from sabbazaar_contracts.ingestion import (
    Answer,
    FieldValue,
    IngestionStatus,
    IngestionView,
    JobView,
    Preview,
)

log = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "image/png": b"\x89PNG",
    "image/jpeg": b"\xff\xd8\xff",
    "application/pdf": b"%PDF",
}
EDITABLE_FIELDS = {"title", "author", "publisher", "quantity", "selling_price", "mrp", "unit_cost"}


def sniff_media_type(content: bytes) -> str | None:
    for media_type, magic in ALLOWED_TYPES.items():
        if content.startswith(magic):
            return media_type
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


class IngestionService:
    def __init__(
        self,
        repos: Repositories,
        graph: Any,
        registry: ConnectorRegistry,
        apply: ApplyService,
        upload_dir: Path,
    ) -> None:
        self.repos, self.graph, self.registry, self.apply = repos, graph, registry, apply
        self.upload_dir = upload_dir

    @staticmethod
    def _config(iid: str) -> dict:
        return {"configurable": {"thread_id": iid}}

    def _require(self, iid: str) -> Ingestion:
        ing = self.repos.ingestions.get(iid)
        if ing is None:
            raise ApplyError(404, "not_found", "Ingestion not found")
        return ing

    def _state(self, iid: str) -> dict[str, Any]:
        return dict(self.graph.get_state(self._config(iid)).values or {})

    # ---- create / run --------------------------------------------------------------------

    def create(
        self, content: bytes, filename: str, media_type: str, idempotency_key: str | None
    ) -> tuple[Ingestion, bool]:
        digest = hashlib.sha256(content).hexdigest()
        if idempotency_key:
            existing = self.repos.ingestions.find_by_idempotency_key(idempotency_key)
            if existing:
                if existing.content_hash != digest:
                    raise ApplyError(
                        422, "idempotency_key_reused", "Idempotency-Key was used for another file"
                    )
                return existing, False
        existing = self.repos.ingestions.find_by_hash(digest)
        if existing and existing.status != IngestionStatus.REJECTED:
            return existing, False
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        ext = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "application/pdf": ".pdf",
        }[media_type]
        path = self.upload_dir / f"{digest}{ext}"
        path.write_bytes(content)
        ing = Ingestion(
            content_hash=digest,
            idempotency_key=idempotency_key,
            filename=Path(filename or "bill").name[:200],
            media_type=media_type,
            file_path=str(path),
        )
        self.repos.ingestions.add(ing)
        record(
            self.repos.audit,
            correlation_id=ing.id,
            event_type="ingestion.received",
            actor="owner",
            summary=f"Bill uploaded ({media_type}, {len(content)} bytes)",
        )
        return ing, True

    def run(self, iid: str) -> None:
        ing = self._require(iid)
        try:
            self.graph.invoke(
                {"ingestion_id": iid, "file_path": ing.file_path, "media_type": ing.media_type},
                self._config(iid),
            )
        except Exception as exc:  # keep failures visible, never silent
            log.exception("ingestion %s graph run failed", iid)
            cur = self._require(iid)
            self.repos.ingestions.update(
                cur.model_copy(
                    update={
                        "status": IngestionStatus.FAILED,
                        "error": f"workflow_error: {type(exc).__name__}",
                    }
                )
            )
            record(
                self.repos.audit,
                correlation_id=iid,
                event_type="ingestion.failed",
                summary=f"Workflow error: {type(exc).__name__}",
            )

    # ---- owner input ---------------------------------------------------------------------

    def answer(self, iid: str, answers: list[Answer]) -> None:
        with self.apply.lock(iid):
            ing = self._require(iid)
            if ing.status != IngestionStatus.NEEDS_INPUT:
                raise ApplyError(409, "not_waiting_for_input", f"Ingestion is {ing.status.value}")
            state = self._state(iid)
            # Dry run validates everything before resuming; raises AnswerError (422).
            apply_answers(lines_of(state), questions_of(state), answers, self.repos.catalogue)
            self.graph.invoke(Command(resume=[a.model_dump() for a in answers]), self._config(iid))

    def edit_preview(
        self, iid: str, line_id: str, fields: dict[str, str | None], drop: bool
    ) -> None:
        with self.apply.lock(iid):
            ing = self._require(iid)
            if ing.status != IngestionStatus.AWAITING_CONFIRMATION:
                raise ApplyError(409, "not_editable", f"Ingestion is {ing.status.value}")
            lines = lines_of(self._state(iid))
            line = next((ln for ln in lines if ln.id == line_id and not ln.dropped), None)
            if line is None:
                raise ApplyError(404, "line_not_found", f"No active line {line_id}")
            errors: dict[str, str] = {}
            for name, raw in fields.items():
                if name not in EDITABLE_FIELDS:
                    errors[name] = "field cannot be edited"
                    continue
                try:
                    line.fields[name] = FieldValue(
                        value=parse_owner_value(name, raw), source="owner"
                    )
                except ValueError as exc:
                    errors[name] = str(exc)
            if errors:
                raise AnswerError(errors)
            if drop:
                line.dropped = True
                line.notes.append("Dropped by owner")
            dumped = [ln.model_dump(mode="json") for ln in lines]
            self.graph.update_state(self._config(iid), {"lines": dumped}, as_node="classify")
            record(
                self.repos.audit,
                correlation_id=iid,
                event_type="action.superseded",
                actor="owner",
                summary=f"Owner edited {line_id}; preview will be rebuilt",
            )
            self.graph.invoke(None, self._config(iid))

    def confirm(self, iid: str, version: int) -> None:
        self._require(iid)

        def load() -> Preview | None:
            raw = self._state(iid).get("preview")
            return Preview.model_validate(raw) if raw else None

        self.apply.confirm(iid, load, version)

    # ---- read ----------------------------------------------------------------------------

    def view(self, iid: str) -> IngestionView:
        ing = self._require(iid)
        state = self._state(iid)
        status = ing.status
        jobs = [
            JobView(
                id=j.id,
                line_id=j.line_id,
                channel=j.channel,
                operation=j.operation,
                status=j.status,
                attempts=j.attempts,
                error_code=j.error_code,
                message=j.message,
                admin_url=j.admin_url,
            )
            for j in self.repos.jobs.list_for(iid)
        ]
        return IngestionView(
            id=ing.id,
            status=status,
            filename=ing.filename,
            fallback_used=ing.fallback_used,
            simulated_channels=self.registry.simulated_channels(),
            lines=lines_of(state),
            questions=questions_of(state) if status == IngestionStatus.NEEDS_INPUT else [],
            preview=Preview.model_validate(state["preview"]) if state.get("preview") else None,
            jobs=jobs,
            error=ing.error,
        )

    def audit(self, iid: str) -> list[AuditEvent]:
        self._require(iid)
        return self.repos.audit.list_for(iid)
