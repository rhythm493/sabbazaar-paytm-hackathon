"""Voice/text command contracts: transcript -> structured commands -> approval actions.

Commands are never executed directly. They are turned into ``ProposedAction``
rows (path A) that a merchant approves or rejects, after which a connector job
operation runs. See docs/adr/0003-policy-gate-between-agents-and-connectors.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class CommandOp(StrEnum):
    SET_PRICE = "set_price"
    SET_STOCK = "set_stock"
    ADJUST_STOCK = "adjust_stock"


class InventoryCommand(BaseModel):
    """One proposed inventory modification parsed from an instruction.

    ``price_inr`` is required for ``set_price``, ``quantity`` (absolute level)
    for ``set_stock`` and ``delta`` (signed, may be negative) for
    ``adjust_stock``. Anything missing is treated as unparseable, not guessed.
    """

    op: CommandOp
    product_query: str
    price_inr: float | None = None
    quantity: int | None = None
    delta: int | None = None
    rationale: str


class CommandExtraction(BaseModel):
    """Structured-output target for the command-parsing model call."""

    commands: list[InventoryCommand] = []
    unparsed: list[str] = []


class ActionOut(BaseModel):
    """Web-facing view of a ``ProposedAction`` (mirrors apps/web Action type)."""

    id: int
    store_id: int
    type: str
    status: str  # proposed | awaiting_approval | approved | executed | rejected | cancelled | failed
    payload: dict
    rationale: str | None
    idempotency_key: str
    created_at: datetime
    resolved_at: datetime | None = None


class CommandResponse(BaseModel):
    transcript: str
    language_code: str | None = None
    actions: list[ActionOut] = []
    unparsed: list[str] = []
    message: str
