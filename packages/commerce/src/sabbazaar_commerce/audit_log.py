from __future__ import annotations

from sabbazaar_commerce.domain import AuditEvent
from sabbazaar_commerce.repositories import AuditRepository


def record(
    audit: AuditRepository,
    *,
    correlation_id: str,
    event_type: str,
    summary: str,
    entity_type: str = "ingestion",
    entity_id: str | None = None,
    actor: str = "system",
) -> None:
    """Append one audit event. Summaries must be safe: ids and short facts, never secrets or files."""
    audit.append(
        AuditEvent(
            actor=actor,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id or correlation_id,
            correlation_id=correlation_id,
            summary=summary,
        )
    )
