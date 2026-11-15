"""Structured output of bill extraction. Every value must be printed on the bill; absent means None."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ExtractedLine(BaseModel):
    line_no: int = Field(description="1-based position of the line on the bill")
    title: str | None = Field(default=None, description="Book title exactly as printed")
    author: str | None = Field(default=None, description="Author if printed, else null")
    isbn: str | None = Field(default=None, description="ISBN digits as printed, else null")
    publisher: str | None = Field(default=None, description="Publisher if printed, else null")
    quantity: int | None = Field(default=None, description="Quantity supplied")
    mrp: Decimal | None = Field(default=None, description="Printed MRP per unit in INR")
    unit_cost: Decimal | None = Field(
        default=None, description="Net rate per unit charged to the shop, in INR"
    )
    confidence: float = Field(default=1.0, ge=0, le=1, description="Confidence in this line")


class BillExtraction(BaseModel):
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    currency: str = "INR"
    lines: list[ExtractedLine] = Field(default_factory=list)
