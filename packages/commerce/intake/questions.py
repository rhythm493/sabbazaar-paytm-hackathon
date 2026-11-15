"""Decide what to ask the owner, and apply their answers. Deterministic code, not model reasoning."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from commerce.domain import Book
from commerce.intake.matching import classify_line
from commerce.intake.normalize import to_money
from commerce.intake.requirements import Level, label, rules_for
from commerce.repositories import CatalogueRepository
from contracts.ingestion import (
    MONEY_FIELDS,
    Answer,
    FieldValue,
    LineKind,
    Question,
    QuestionKind,
    WorkingLine,
)

MAX_PRICE = Decimal("1000000")
FIELD_LABELS = {
    "title": "the book title",
    "quantity": "the quantity received",
    "selling_price": "the selling price (₹)",
    "author": "the author",
    "publisher": "the publisher",
    "isbn": "the ISBN",
}


class AnswerError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def effective(line: WorkingLine, book: Book | None, field: str) -> Any:
    value = line.get(field)
    if value is None and book is not None and field != "quantity":
        value = getattr(book, field, None)
    return value


def _qid(line_id: str, kind: QuestionKind, field: str | None = None) -> str:
    return f"{line_id}:{kind.value}" + (f":{field}" if field else "")


def _price_question(line: WorkingLine, book: Book | None) -> Question | None:
    if line.get("selling_price") is not None:
        return None
    title = effective(line, book, "title")
    bill_mrp: Decimal | None = line.get("mrp")
    if line.kind == LineKind.NEW:
        prompt = f"What selling price should '{title}' have?"
        if bill_mrp:
            prompt += f" The bill shows MRP ₹{bill_mrp}."
    else:
        assert book is not None
        if book.selling_price is None:
            prompt = f"'{title}' has no selling price yet. What should it be?"
        elif bill_mrp is not None and book.mrp is not None and bill_mrp != book.mrp:
            prompt = (
                f"The MRP of '{title}' changed from ₹{book.mrp} to ₹{bill_mrp}. "
                f"Current selling price is ₹{book.selling_price}. What should the selling price be?"
            )
        else:
            return None
    suggestion = bill_mrp or (book.selling_price if book else None)
    return Question(
        id=_qid(line.id, QuestionKind.PRICE, "selling_price"),
        line_id=line.id,
        kind=QuestionKind.PRICE,
        field="selling_price",
        prompt=prompt,
        suggestion=str(suggestion) if suggestion is not None else None,
    )


def open_questions(
    lines: list[WorkingLine], catalogue: CatalogueRepository, channels: list[str]
) -> list[Question]:
    questions: list[Question] = []
    for line in lines:
        if line.dropped:
            continue
        if line.kind == LineKind.UNREADABLE:
            for field in ("title", "quantity"):
                if not line.get(field):
                    questions.append(
                        Question(
                            id=_qid(line.id, QuestionKind.MISSING_FIELD, field),
                            line_id=line.id,
                            kind=QuestionKind.MISSING_FIELD,
                            field=field,
                            prompt=(
                                f"Bill line {line.line_nos[0]} could not be read. "
                                f"Please enter {FIELD_LABELS[field]}, or drop this line."
                            ),
                            allow_drop=True,
                        )
                    )
            continue
        if line.kind == LineKind.UNCERTAIN_MATCH:
            cand = catalogue.get(line.candidate_book_id or "")
            assert cand is not None
            who = f" by {cand.author}" if cand.author else ""
            questions.append(
                Question(
                    id=_qid(line.id, QuestionKind.CONFIRM_MATCH),
                    line_id=line.id,
                    kind=QuestionKind.CONFIRM_MATCH,
                    prompt=(
                        f"The bill has '{line.get('title')}' without an ISBN. Is it the same book as "
                        f"'{cand.title}'{who} (ISBN {cand.isbn or 'none'}) already in your stock? "
                        "Answer yes or no."
                    ),
                    suggestion="yes",
                )
            )
            continue
        book = catalogue.get(line.matched_book_id) if line.matched_book_id else None
        pq = _price_question(line, book)
        if pq:
            questions.append(pq)
        asked = {q.field for q in questions if q.line_id == line.id}
        for channel in channels:
            for field, level in rules_for(channel).items():
                if level != Level.REQUIRED or field in asked:
                    continue
                if effective(line, book, field) in (None, ""):
                    asked.add(field)
                    questions.append(
                        Question(
                            id=_qid(line.id, QuestionKind.MISSING_FIELD, field),
                            line_id=line.id,
                            kind=QuestionKind.MISSING_FIELD,
                            field=field,
                            prompt=(
                                f"{label(channel)} needs {FIELD_LABELS.get(field, field)} for "
                                f"'{effective(line, book, 'title')}'."
                            ),
                        )
                    )
    return questions


def parse_owner_value(field: str, raw: str | None) -> Any:
    if raw is None or not str(raw).strip():
        raise ValueError("a value is required")
    raw = str(raw).strip()
    if field in MONEY_FIELDS:
        value = to_money(raw)
        if value is None or value > MAX_PRICE:
            raise ValueError("enter a price greater than 0, e.g. 499 or 499.00")
        return value
    if field == "quantity":
        if not raw.isdigit() or int(raw) <= 0:
            raise ValueError("enter a whole number greater than 0")
        return int(raw)
    return " ".join(raw.split())


def apply_answers(
    lines: list[WorkingLine],
    questions: list[Question],
    answers: list[Answer],
    catalogue: CatalogueRepository,
) -> list[WorkingLine]:
    """Validate all answers first (all-or-nothing), then apply them as owner-sourced facts."""
    by_id = {q.id: q for q in questions}
    errors: dict[str, str] = {}
    parsed: list[tuple[Question, Answer, Any]] = []
    if not answers:
        raise AnswerError({"answers": "provide at least one answer"})
    for ans in answers:
        q = by_id.get(ans.question_id)
        if q is None:
            errors[ans.question_id] = "unknown or already answered question"
            continue
        if ans.drop_line:
            if not q.allow_drop:
                errors[q.id] = "this line cannot be dropped"
            else:
                parsed.append((q, ans, None))
            continue
        try:
            if q.kind == QuestionKind.CONFIRM_MATCH:
                v = (ans.value or "").strip().casefold()
                if v not in ("yes", "no"):
                    raise ValueError("answer yes or no")
                parsed.append((q, ans, v == "yes"))
            else:
                parsed.append((q, ans, parse_owner_value(q.field or "", ans.value)))
        except ValueError as exc:
            errors[q.id] = str(exc)
    if errors:
        raise AnswerError(errors)

    out = {line.id: line.model_copy(deep=True) for line in lines}
    for q, ans, value in parsed:
        line = out[q.line_id]
        if ans.drop_line:
            line.dropped = True
            line.notes.append("Dropped by owner")
        elif q.kind == QuestionKind.CONFIRM_MATCH:
            if value:
                line.kind, line.matched_book_id = LineKind.RESTOCK, line.candidate_book_id
            else:
                line.kind = LineKind.NEW
            line.candidate_book_id = None
        else:
            line.fields[q.field or ""] = FieldValue(value=value, source="owner")
    for lid, line in out.items():
        if line.kind == LineKind.UNREADABLE and not line.dropped:
            out[lid] = classify_line(line, catalogue)
    return [out[line.id] for line in lines]
