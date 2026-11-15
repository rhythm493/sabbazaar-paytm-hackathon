"""Turn raw extraction into working lines: validate ISBNs, parse money, merge duplicates."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from commerce.isbn import normalize_isbn
from contracts.bill import BillExtraction
from contracts.ingestion import FieldValue, WorkingLine

CENT = Decimal("0.01")


def to_money(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        d = Decimal(str(value).replace(",", "").replace("₹", "").strip())
    except InvalidOperation:
        return None
    if not d.is_finite() or d <= 0:
        return None
    return d.quantize(CENT)


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    text = " ".join(text.split())
    return text or None


def normalize_extraction(extraction: BillExtraction) -> list[WorkingLine]:
    lines: list[WorkingLine] = []
    by_isbn: dict[str, WorkingLine] = {}
    for raw in sorted(extraction.lines, key=lambda x: x.line_no):
        notes: list[str] = []
        isbn = normalize_isbn(raw.isbn)
        if raw.isbn and not isbn:
            notes.append(
                f"ISBN '{raw.isbn}' on bill line {raw.line_no} is not valid and was ignored"
            )
        quantity = raw.quantity if raw.quantity and raw.quantity > 0 else None

        if isbn and isbn in by_isbn:
            target = by_isbn[isbn]
            target.line_nos.append(raw.line_no)
            prev = target.get("quantity") or 0
            if quantity:
                target.fields["quantity"] = FieldValue(
                    value=prev + quantity, source="bill", confidence=raw.confidence
                )
            target.notes.append(
                f"Bill line {raw.line_no} has the same ISBN; quantities were combined"
            )
            continue

        values: dict[str, object] = {
            "title": _clean(raw.title),
            "author": _clean(raw.author),
            "isbn": isbn,
            "publisher": _clean(raw.publisher),
            "quantity": quantity,
            "mrp": to_money(raw.mrp),
            "unit_cost": to_money(raw.unit_cost),
        }
        line = WorkingLine(
            id=f"L{raw.line_no}",
            line_nos=[raw.line_no],
            fields={
                k: FieldValue(value=v, source="bill", confidence=raw.confidence)
                for k, v in values.items()
                if v is not None
            },
            notes=notes,
        )
        lines.append(line)
        if isbn:
            by_isbn[isbn] = line
    return lines
