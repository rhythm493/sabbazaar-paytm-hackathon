"""Match bill lines to the canonical catalogue. Ambiguity becomes a question, never a merge."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from commerce.domain import Book
from commerce.repositories import CatalogueRepository
from contracts.ingestion import LineKind, WorkingLine

TITLE_MATCH_THRESHOLD = 0.9


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.casefold()).strip()


def best_title_candidate(title: str, books: list[Book]) -> Book | None:
    target = _norm_title(title)
    best: tuple[float, Book] | None = None
    for book in books:
        ratio = SequenceMatcher(None, target, _norm_title(book.title)).ratio()
        if ratio >= TITLE_MATCH_THRESHOLD and (best is None or ratio > best[0]):
            best = (ratio, book)
    return best[1] if best else None


def classify_line(line: WorkingLine, catalogue: CatalogueRepository) -> WorkingLine:
    line = line.model_copy(deep=True)
    line.matched_book_id = None
    line.candidate_book_id = None
    title, quantity, isbn = line.get("title"), line.get("quantity"), line.get("isbn")
    if not title or not quantity:
        line.kind = LineKind.UNREADABLE
        return line
    if isbn:
        book = catalogue.find_by_isbn(isbn)
        if book:
            line.kind, line.matched_book_id = LineKind.RESTOCK, book.id
        else:
            line.kind = LineKind.NEW
        return line
    candidate = best_title_candidate(title, catalogue.list())
    if candidate:
        line.kind, line.candidate_book_id = LineKind.UNCERTAIN_MATCH, candidate.id
    else:
        line.kind = LineKind.NEW
    return line


def classify(lines: list[WorkingLine], catalogue: CatalogueRepository) -> list[WorkingLine]:
    return [classify_line(line, catalogue) for line in lines]
