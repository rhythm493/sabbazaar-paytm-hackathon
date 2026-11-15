"""Confirmation and application of an approved preview. The only path to connector mutations."""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from typing import Protocol

from sabbazaar_commerce.audit_log import record
from sabbazaar_commerce.domain import Approval, Book, ConnectorJob, InventoryEntry, Listing
from sabbazaar_commerce.repositories import Repositories
from sabbazaar_contracts.channels import ChannelConnector, ConnectorResult, ErrorCode, ListingPayload
from sabbazaar_contracts.ingestion import IngestionStatus, LineKind, Preview

AMBIGUOUS_PUBLISH = (
    "Outcome unknown; check the channel for this product before re-uploading (not auto-retried)"
)
NOT_RETRIED = {ErrorCode.CONFLICT.value, ErrorCode.VALIDATION_FAILED.value}


class ConnectorLookup(Protocol):
    def get(self, channel: str) -> ChannelConnector: ...


class ApplyError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class ApplyService:
    def __init__(self, repos: Repositories, connectors: ConnectorLookup) -> None:
        self.repos = repos
        self.connectors = connectors
        self._locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

    def lock(self, ingestion_id: str) -> threading.Lock:
        return self._locks[ingestion_id]

    # ---- confirm -------------------------------------------------------------------------

    def confirm(
        self,
        ingestion_id: str,
        load_preview: Callable[[], Preview | None],
        version: int,
        actor: str = "owner",
    ) -> None:
        """Approve exactly `version` of the current preview and apply it.

        The preview is loaded inside the per-ingestion lock so a concurrent edit cannot slip a
        different preview past the version check. Application is idempotent, so a confirm that
        was interrupted midway (status stays `applying`) resumes when confirmed again.
        """
        r = self.repos
        with self.lock(ingestion_id):
            ing = r.ingestions.get(ingestion_id)
            if ing is None:
                raise ApplyError(404, "not_found", "Ingestion not found")
            preview = load_preview()
            existing = r.approvals.for_ingestion(ingestion_id)
            if existing:
                if existing.preview_version != version:
                    raise ApplyError(
                        409,
                        "already_confirmed",
                        f"Preview v{existing.preview_version} was already confirmed",
                    )
                if ing.status != IngestionStatus.APPLYING:
                    return  # duplicate confirmation: nothing is applied twice
                if preview is None or preview.hash != existing.preview_hash:
                    raise ApplyError(409, "preview_changed", "Approved preview no longer matches")
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type="ingestion.apply_resumed",
                    actor=actor,
                    summary="Resuming an interrupted application of the approved preview",
                )
            else:
                if ing.status != IngestionStatus.AWAITING_CONFIRMATION or preview is None:
                    raise ApplyError(
                        409,
                        "not_ready",
                        f"Ingestion is {ing.status.value}, not awaiting confirmation",
                    )
                if version != preview.version:
                    raise ApplyError(
                        409,
                        "stale_preview",
                        f"Preview v{version} is outdated; the current one is v{preview.version}",
                    )
                r.approvals.add(
                    Approval(
                        ingestion_id=ingestion_id,
                        preview_version=preview.version,
                        preview_hash=preview.hash,
                        actor=actor,
                    )
                )
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type="action.approved",
                    actor=actor,
                    summary=f"Owner confirmed preview v{preview.version} ({preview.hash[:12]})",
                )
                r.ingestions.update(ing.model_copy(update={"status": IngestionStatus.APPLYING}))
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type="ingestion.applying",
                    summary="Applying confirmed changes",
                )
            self._apply_lines(ingestion_id, preview, actor)
        self.run_jobs(ingestion_id)

    def _apply_lines(self, ingestion_id: str, preview: Preview, actor: str) -> None:
        """Canonical changes + job creation. Safe to re-run: every write is keyed."""
        r = self.repos
        queued = {j.idempotency_key for j in r.jobs.list_for(ingestion_id)}
        for pl in preview.lines:
            book = r.catalogue.get(pl.book_id) if pl.book_id else None
            if book is None and pl.kind == LineKind.NEW:
                book = (r.catalogue.find_by_isbn(pl.isbn) if pl.isbn else None) or (
                    r.catalogue.find_by_sku(pl.sku)
                )
            if book is None:
                book = Book(
                    sku=pl.sku,
                    title=pl.title,
                    author=pl.author,
                    isbn=pl.isbn,
                    publisher=pl.publisher,
                    mrp=pl.mrp,
                    selling_price=pl.price_after,
                    unit_cost=pl.unit_cost,
                )
                r.catalogue.add(book)
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type="product.created",
                    entity_type="book",
                    entity_id=book.id,
                    actor=actor,
                    summary=f"Added '{book.title}' at ₹{book.selling_price}",
                )
            else:
                updated = book.model_copy(
                    update={
                        "selling_price": pl.price_after,
                        "mrp": pl.mrp or book.mrp,
                        "unit_cost": pl.unit_cost or book.unit_cost,
                    }
                )
                if updated != book:
                    r.catalogue.update(updated)
                    record(
                        r.audit,
                        correlation_id=ingestion_id,
                        event_type="product.updated",
                        entity_type="book",
                        entity_id=book.id,
                        actor=actor,
                        summary=f"Updated '{book.title}' price/MRP/cost from bill",
                    )
                book = updated
            added = r.inventory.append(
                InventoryEntry(
                    book_id=book.id,
                    delta=pl.quantity_added,
                    reason=f"bill {ingestion_id}",
                    source_key=f"ingestion:{ingestion_id}:{pl.line_id}",
                )
            )
            if added:
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type="inventory.changed",
                    entity_type="book",
                    entity_id=book.id,
                    summary=f"Stock +{pl.quantity_added} for '{book.title}'",
                )
            for change in pl.channel_changes:
                key = f"{ingestion_id}:{pl.line_id}:{change.channel}:{change.operation}"
                if key in queued:
                    continue
                queued.add(key)
                r.jobs.add(
                    ConnectorJob(
                        ingestion_id=ingestion_id,
                        line_id=pl.line_id,
                        book_id=book.id,
                        channel=change.channel,
                        operation=change.operation,
                        params=change.model_dump(mode="json"),
                        idempotency_key=key,
                    )
                )
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type="connector.job.queued",
                    summary=f"Queued {change.channel} {change.operation} for {pl.line_id}",
                )

    # ---- jobs ----------------------------------------------------------------------------

    def _execute(self, job: ConnectorJob) -> ConnectorResult:
        r = self.repos
        try:
            conn = self.connectors.get(job.channel)
        except KeyError:
            return ConnectorResult.fail(ErrorCode.NOT_CONFIGURED, f"{job.channel} is not connected")
        on_hand = r.inventory.on_hand(job.book_id)
        listing = r.listings.get(job.book_id, job.channel)
        if job.operation == "publish_product":
            payload = ListingPayload.model_validate(job.params["payload"])
            payload = payload.model_copy(update={"quantity": on_hand})
            result = conn.publish_product(payload, job.idempotency_key)
            if result.ok and result.ref:
                r.listings.upsert(
                    Listing(
                        book_id=job.book_id,
                        channel=job.channel,
                        ref=result.ref,
                        last_known_quantity=result.quantity
                        if result.quantity is not None
                        else on_hand,
                    )
                )
            return result
        if listing is None:
            return ConnectorResult.fail(
                ErrorCode.VALIDATION_FAILED, "book is not listed on channel"
            )
        if job.operation == "set_inventory":
            result = conn.set_inventory(
                listing.ref, on_hand, listing.last_known_quantity, job.idempotency_key
            )
            if result.ok:
                r.listings.upsert(listing.model_copy(update={"last_known_quantity": on_hand}))
            return result
        if job.operation == "update_product":
            return conn.update_product(
                listing.ref, Decimal(job.params["price"]), job.idempotency_key
            )
        return ConnectorResult.fail(
            ErrorCode.VALIDATION_FAILED, f"unknown operation {job.operation}"
        )

    def run_jobs(self, ingestion_id: str) -> None:
        r = self.repos
        with self.lock(ingestion_id):
            # Publish before inventory/price so later jobs can use the new listing.
            order = {"publish_product": 0, "set_inventory": 1, "update_product": 2}
            jobs = sorted(r.jobs.list_for(ingestion_id), key=lambda j: order.get(j.operation, 9))
            for job in jobs:
                if job.status not in ("pending", "retryable_failure", "running"):
                    continue
                if job.status == "running" and job.operation == "publish_product":
                    # A previous attempt died mid-call: the product may exist. Never re-create.
                    result = ConnectorResult.fail(ErrorCode.UNKNOWN, AMBIGUOUS_PUBLISH)
                else:
                    job.status, job.attempts = "running", job.attempts + 1
                    r.jobs.update(job)
                    try:
                        result = self._execute(job)
                    except Exception as exc:  # never leave a job stuck in "running"
                        result = ConnectorResult.fail(
                            ErrorCode.UNKNOWN, f"unexpected error: {type(exc).__name__}"
                        )
                if result.ok:
                    job.status, job.error_code, job.message = "succeeded", None, None
                    listing = r.listings.get(job.book_id, job.channel)
                    job.admin_url = listing.ref.admin_url if listing else None
                    event = "connector.job.succeeded"
                else:
                    code = result.error_code or ErrorCode.UNKNOWN
                    ambiguous = job.operation == "publish_product" and code == ErrorCode.UNKNOWN
                    job.status = (
                        "terminal_failure"
                        if code.value in NOT_RETRIED or ambiguous
                        else "retryable_failure"
                    )
                    message = result.message or ""
                    if ambiguous and message != AMBIGUOUS_PUBLISH:
                        message = f"{message}. {AMBIGUOUS_PUBLISH}"
                    job.error_code, job.message = code.value, message
                    event = "connector.job.failed"
                r.jobs.update(job)
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type=event,
                    entity_type="connector_job",
                    entity_id=job.id,
                    summary=f"{job.channel} {job.operation} {job.line_id}: "
                    + ("ok" if result.ok else f"{job.error_code} - {job.message}"),
                )
            final = r.jobs.list_for(ingestion_id)
            status = (
                IngestionStatus.COMPLETED
                if all(j.status == "succeeded" for j in final)
                else IngestionStatus.PARTIALLY_FAILED
            )
            ing = r.ingestions.get(ingestion_id)
            if ing and ing.status != status:
                r.ingestions.update(ing.model_copy(update={"status": status}))
                record(
                    r.audit,
                    correlation_id=ingestion_id,
                    event_type=f"ingestion.{status.value}",
                    summary=f"Ingestion is now {status.value}",
                )

    def retry(self, ingestion_id: str) -> None:
        ing = self.repos.ingestions.get(ingestion_id)
        if ing is None:
            raise ApplyError(404, "not_found", "Ingestion not found")
        if ing.status != IngestionStatus.PARTIALLY_FAILED:
            raise ApplyError(409, "nothing_to_retry", f"Ingestion is {ing.status.value}")
        retryable = [
            j for j in self.repos.jobs.list_for(ingestion_id) if j.status == "retryable_failure"
        ]
        if not retryable:
            raise ApplyError(
                409,
                "nothing_to_retry",
                "Remaining failures need a manual check (conflict, validation or unknown outcome)",
            )
        record(
            self.repos.audit,
            correlation_id=ingestion_id,
            event_type="connector.job.retry",
            actor="owner",
            summary=f"Owner retried {len(retryable)} job(s)",
        )
        self.run_jobs(ingestion_id)

    def reject(self, ingestion_id: str, actor: str = "owner") -> None:
        r = self.repos
        with self.lock(ingestion_id):
            ing = r.ingestions.get(ingestion_id)
            if ing is None:
                raise ApplyError(404, "not_found", "Ingestion not found")
            if ing.status not in (
                IngestionStatus.NEEDS_INPUT,
                IngestionStatus.AWAITING_CONFIRMATION,
                IngestionStatus.FAILED,
            ):
                raise ApplyError(409, "cannot_reject", f"Ingestion is {ing.status.value}")
            r.ingestions.update(ing.model_copy(update={"status": IngestionStatus.REJECTED}))
            record(
                r.audit,
                correlation_id=ingestion_id,
                event_type="ingestion.rejected",
                actor=actor,
                summary="Owner discarded this bill; nothing was applied",
            )
