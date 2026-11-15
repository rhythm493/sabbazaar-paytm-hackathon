"""In-memory repositories for tests and local dev until the ORM-backed implementation lands.

Not durable: data is lost on restart. Thread-safe via one lock per repository.
"""

from __future__ import annotations

import threading

from commerce.domain import (
    Approval,
    AuditEvent,
    Book,
    ConnectorJob,
    Ingestion,
    InventoryEntry,
    Listing,
)
from commerce.repositories import Repositories


class _Locked:
    def __init__(self) -> None:
        self._lock = threading.RLock()


class MemoryCatalogue(_Locked):
    def __init__(self) -> None:
        super().__init__()
        self._books: dict[str, Book] = {}

    def get(self, book_id: str) -> Book | None:
        with self._lock:
            b = self._books.get(book_id)
            return b.model_copy() if b else None

    def find_by_isbn(self, isbn: str) -> Book | None:
        with self._lock:
            for b in self._books.values():
                if b.isbn == isbn:
                    return b.model_copy()
            return None

    def find_by_sku(self, sku: str) -> Book | None:
        with self._lock:
            for b in self._books.values():
                if b.sku == sku:
                    return b.model_copy()
            return None

    def list(self) -> list[Book]:
        with self._lock:
            return [b.model_copy() for b in self._books.values()]

    def add(self, book: Book) -> None:
        with self._lock:
            self._books[book.id] = book.model_copy()

    def update(self, book: Book) -> None:
        with self._lock:
            self._books[book.id] = book.model_copy()


class MemoryInventory(_Locked):
    def __init__(self) -> None:
        super().__init__()
        self._entries: list[InventoryEntry] = []
        self._keys: set[str] = set()

    def append(self, entry: InventoryEntry) -> bool:
        with self._lock:
            if entry.source_key in self._keys:
                return False
            self._keys.add(entry.source_key)
            self._entries.append(entry.model_copy())
            return True

    def on_hand(self, book_id: str) -> int:
        with self._lock:
            return sum(e.delta for e in self._entries if e.book_id == book_id)


class MemoryListings(_Locked):
    def __init__(self) -> None:
        super().__init__()
        self._rows: dict[tuple[str, str], Listing] = {}

    def get(self, book_id: str, channel: str) -> Listing | None:
        with self._lock:
            row = self._rows.get((book_id, channel))
            return row.model_copy(deep=True) if row else None

    def upsert(self, listing: Listing) -> None:
        with self._lock:
            self._rows[(listing.book_id, listing.channel)] = listing.model_copy(deep=True)


class MemoryIngestions(_Locked):
    def __init__(self) -> None:
        super().__init__()
        self._rows: dict[str, Ingestion] = {}

    def add(self, ingestion: Ingestion) -> None:
        with self._lock:
            self._rows[ingestion.id] = ingestion.model_copy()

    def get(self, ingestion_id: str) -> Ingestion | None:
        with self._lock:
            row = self._rows.get(ingestion_id)
            return row.model_copy() if row else None

    def find_by_hash(self, content_hash: str) -> Ingestion | None:
        with self._lock:
            for row in self._rows.values():
                if row.content_hash == content_hash:
                    return row.model_copy()
            return None

    def find_by_idempotency_key(self, key: str) -> Ingestion | None:
        with self._lock:
            for row in self._rows.values():
                if row.idempotency_key == key:
                    return row.model_copy()
            return None

    def update(self, ingestion: Ingestion) -> None:
        with self._lock:
            self._rows[ingestion.id] = ingestion.model_copy()


class MemoryApprovals(_Locked):
    def __init__(self) -> None:
        super().__init__()
        self._rows: dict[str, Approval] = {}

    def add(self, approval: Approval) -> None:
        with self._lock:
            self._rows[approval.ingestion_id] = approval.model_copy()

    def for_ingestion(self, ingestion_id: str) -> Approval | None:
        with self._lock:
            row = self._rows.get(ingestion_id)
            return row.model_copy() if row else None


class MemoryJobs(_Locked):
    def __init__(self) -> None:
        super().__init__()
        self._rows: dict[str, ConnectorJob] = {}

    def add(self, job: ConnectorJob) -> None:
        with self._lock:
            self._rows[job.id] = job.model_copy(deep=True)

    def list_for(self, ingestion_id: str) -> list[ConnectorJob]:
        with self._lock:
            return [
                j.model_copy(deep=True)
                for j in self._rows.values()
                if j.ingestion_id == ingestion_id
            ]

    def update(self, job: ConnectorJob) -> None:
        with self._lock:
            self._rows[job.id] = job.model_copy(deep=True)


class MemoryAudit(_Locked):
    def __init__(self) -> None:
        super().__init__()
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event.model_copy())

    def list_for(self, correlation_id: str) -> list[AuditEvent]:
        with self._lock:
            return [e.model_copy() for e in self._events if e.correlation_id == correlation_id]


def memory_repositories() -> Repositories:
    return Repositories(
        catalogue=MemoryCatalogue(),
        inventory=MemoryInventory(),
        listings=MemoryListings(),
        ingestions=MemoryIngestions(),
        approvals=MemoryApprovals(),
        jobs=MemoryJobs(),
        audit=MemoryAudit(),
    )
