"""Canonical commerce entities (persistence-agnostic; Ridam's ORM maps these)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from sabbazaar_contracts.channels import ExternalRef
from sabbazaar_contracts.ingestion import IngestionStatus


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(UTC)


class Book(BaseModel):
    id: str = Field(default_factory=new_id)
    sku: str
    title: str
    author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    mrp: Decimal | None = None
    selling_price: Decimal | None = None
    unit_cost: Decimal | None = None


class InventoryEntry(BaseModel):
    id: str = Field(default_factory=new_id)
    book_id: str
    delta: int
    reason: str
    source_key: str
    at: datetime = Field(default_factory=now)


class Listing(BaseModel):
    book_id: str
    channel: str
    ref: ExternalRef
    last_known_quantity: int | None = None


class Ingestion(BaseModel):
    id: str = Field(default_factory=new_id)
    content_hash: str
    idempotency_key: str | None = None
    filename: str
    media_type: str
    file_path: str
    status: IngestionStatus = IngestionStatus.RECEIVED
    fallback_used: bool = False
    error: str | None = None
    created_at: datetime = Field(default_factory=now)


class Approval(BaseModel):
    id: str = Field(default_factory=new_id)
    ingestion_id: str
    preview_version: int
    preview_hash: str
    actor: str
    at: datetime = Field(default_factory=now)


class ConnectorJob(BaseModel):
    id: str = Field(default_factory=new_id)
    ingestion_id: str
    line_id: str
    book_id: str
    channel: str
    operation: str
    params: dict[str, Any]
    idempotency_key: str
    status: str = "pending"  # pending | running | succeeded | retryable_failure | terminal_failure
    attempts: int = 0
    error_code: str | None = None
    message: str | None = None
    admin_url: str | None = None


class AuditEvent(BaseModel):
    id: str = Field(default_factory=new_id)
    at: datetime = Field(default_factory=now)
    actor: str
    event_type: str
    entity_type: str
    entity_id: str
    correlation_id: str
    summary: str
