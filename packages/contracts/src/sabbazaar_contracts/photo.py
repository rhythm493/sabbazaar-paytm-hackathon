"""Structured extraction from a single product photo (ADR 0007).

Used by the photo-upload endpoint to turn one image into typed product
fields. The model MUST NOT invent prices, barcodes, brands or ISBNs — any
field it cannot read from the photo stays ``None`` and lands in
``missing_fields``. Merchant approval remains the gate before anything
reaches a channel.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ProductPhotoExtraction(BaseModel):
    # Empty string means "the model could not produce a usable title".
    title: str = ""
    description: str = ""
    vendor: str | None = None
    product_type: str | None = None
    price_inr: Decimal | None = None
    sku: str | None = None
    # Overall confidence in the extraction, 0-1.
    confidence: float = Field(default=0.5, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
