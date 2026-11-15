from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConnectorKind(StrEnum):
    SHOPIFY = "shopify"


class ConnectorJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProductDraftIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    vendor: str = "SabBazaar"
    product_type: str = "General"
    tags: list[str] = Field(default_factory=list)
    price_inr: Decimal = Field(gt=0)
    sku: str = Field(min_length=1, max_length=80)
    evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)


class VariantOut(BaseModel):
    id: int
    external_variant_id: str | None
    sku: str
    price_inr: Decimal
    inventory_item_id: str | None = None


class ProductOut(BaseModel):
    id: int
    title: str
    description: str
    vendor: str
    product_type: str
    tags: list[str]
    handle: str
    status: str
    price_inr: Decimal
    version: int
    external_product_id: str | None
    admin_url: str | None
    variants: list[VariantOut]


class PublishResult(BaseModel):
    ok: bool
    external_product_id: str | None = None
    external_variant_id: str | None = None
    inventory_item_id: str | None = None
    admin_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class ApprovalActionOut(BaseModel):
    id: int
    action_type: str
    status: str
    idempotency_key: str
    created_at: datetime


class ActivityOut(BaseModel):
    id: int
    event_type: str
    message: str
    entity_type: str | None
    entity_id: str | None
    created_at: datetime
