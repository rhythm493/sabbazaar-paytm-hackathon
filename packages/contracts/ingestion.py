"""Bill-ingestion contracts shared by agents, commerce and the API."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from contracts.channels import ListingPayload


class IngestionStatus(StrEnum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    NEEDS_INPUT = "needs_input"
    CHECKING = "checking"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    APPLYING = "applying"
    COMPLETED = "completed"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"
    REJECTED = "rejected"


class LineKind(StrEnum):
    RESTOCK = "restock"
    NEW = "new"
    UNCERTAIN_MATCH = "uncertain_match"
    UNREADABLE = "unreadable"


class QuestionKind(StrEnum):
    MISSING_FIELD = "missing_field"
    PRICE = "price"
    CONFIRM_MATCH = "confirm_match"


FieldSource = Literal["bill", "owner", "catalogue", "config"]

# Canonical line field names.
TEXT_FIELDS = ("title", "author", "isbn", "publisher")
MONEY_FIELDS = ("mrp", "unit_cost", "selling_price")
INT_FIELDS = ("quantity",)


class FieldValue(BaseModel):
    value: Any = None
    source: FieldSource
    confidence: float | None = None


class WorkingLine(BaseModel):
    id: str
    line_nos: list[int]
    kind: LineKind | None = None
    matched_book_id: str | None = None
    candidate_book_id: str | None = None
    fields: dict[str, FieldValue] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    dropped: bool = False

    @model_validator(mode="after")
    def _coerce_types(self) -> WorkingLine:
        # Keep money as Decimal and quantity as int across JSON round-trips (graph checkpoints).
        for name, fv in self.fields.items():
            if fv.value is None:
                continue
            if name in MONEY_FIELDS and not isinstance(fv.value, Decimal):
                fv.value = Decimal(str(fv.value))
            elif name in INT_FIELDS and not isinstance(fv.value, int):
                fv.value = int(fv.value)
        return self

    def get(self, name: str) -> Any:
        fv = self.fields.get(name)
        return fv.value if fv else None


class Question(BaseModel):
    id: str
    line_id: str
    kind: QuestionKind
    field: str | None = None
    prompt: str
    suggestion: str | None = None
    blocking: bool = True
    allow_drop: bool = False


class Answer(BaseModel):
    question_id: str
    value: str | None = None
    drop_line: bool = False


class ChannelChange(BaseModel):
    channel: str
    operation: Literal["publish_product", "update_product", "set_inventory"]
    summary: str
    payload: ListingPayload | None = None
    price: Decimal | None = None
    quantity: int | None = None
    expected_current: int | None = None


class PreviewLine(BaseModel):
    line_id: str
    kind: LineKind
    book_id: str | None
    sku: str
    title: str
    stock_before: int
    stock_after: int
    quantity_added: int
    price_before: Decimal | None
    price_after: Decimal
    price_change_pct: float | None
    mrp: Decimal | None
    unit_cost: Decimal | None
    author: str | None
    isbn: str | None
    publisher: str | None
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    channel_changes: list[ChannelChange] = Field(default_factory=list)


class Preview(BaseModel):
    version: int
    hash: str
    lines: list[PreviewLine]


class JobView(BaseModel):
    id: str
    line_id: str
    channel: str
    operation: str
    status: str
    attempts: int
    error_code: str | None = None
    message: str | None = None
    admin_url: str | None = None


class IngestionView(BaseModel):
    id: str
    status: IngestionStatus
    filename: str
    fallback_used: bool = False
    simulated_channels: list[str] = Field(default_factory=list)
    lines: list[WorkingLine] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    preview: Preview | None = None
    jobs: list[JobView] = Field(default_factory=list)
    error: str | None = None
