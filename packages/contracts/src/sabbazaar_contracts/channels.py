"""Channel-neutral connector contract. Adapters in `connectors` implement `ChannelConnector`."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel


class ListingPayload(BaseModel):
    sku: str
    title: str
    author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    product_type: str = "Book"
    price: Decimal
    unit_cost: Decimal | None = None
    quantity: int
    status: str = "draft"


class ExternalRef(BaseModel):
    product_id: str
    variant_id: str
    inventory_item_id: str
    quantity: int | None = None
    admin_url: str | None = None


class ErrorCode(StrEnum):
    AUTH_FAILED = "auth_failed"
    VALIDATION_FAILED = "validation_failed"
    RATE_LIMITED = "rate_limited"
    TRANSIENT = "transient"
    CONFLICT = "conflict"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"


RETRYABLE = {ErrorCode.RATE_LIMITED, ErrorCode.TRANSIENT, ErrorCode.UNKNOWN}


class ConnectorResult(BaseModel):
    ok: bool
    ref: ExternalRef | None = None
    quantity: int | None = None
    error_code: ErrorCode | None = None
    message: str | None = None

    @classmethod
    def fail(cls, code: ErrorCode, message: str) -> ConnectorResult:
        return cls(ok=False, error_code=code, message=message)


class ConnectorHealth(BaseModel):
    channel: str
    ok: bool
    simulated: bool = False
    message: str | None = None


class ChannelConnector(Protocol):
    channel: str
    simulated: bool

    def health_check(self) -> ConnectorHealth: ...

    def find_by_sku(self, sku: str) -> ExternalRef | None: ...

    def publish_product(self, payload: ListingPayload, idempotency_key: str) -> ConnectorResult: ...

    def update_product(
        self, ref: ExternalRef, price: Decimal, idempotency_key: str
    ) -> ConnectorResult: ...

    def set_inventory(
        self,
        ref: ExternalRef,
        quantity: int,
        expected_current: int | None,
        idempotency_key: str,
    ) -> ConnectorResult: ...
