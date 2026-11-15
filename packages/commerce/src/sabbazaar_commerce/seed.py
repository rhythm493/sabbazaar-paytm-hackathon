"""Demo seed catalogue (synthetic test data). Used by the dev seed endpoint and tests."""

from __future__ import annotations

from decimal import Decimal

from sabbazaar_commerce.domain import Book, InventoryEntry
from sabbazaar_commerce.repositories import Repositories

SEED_BOOKS = [
    (
        Book(
            sku="9781847941831",
            title="Atomic Habits",
            author="James Clear",
            isbn="9781847941831",
            publisher="Random House Business",
            mrp=Decimal("799.00"),
            selling_price=Decimal("699.00"),
            unit_cost=Decimal("500.00"),
        ),
        12,
    ),
    (
        Book(
            sku="9789390166268",
            title="The Psychology of Money",
            author="Morgan Housel",
            isbn="9789390166268",
            publisher="Jaico Publishing House",
            mrp=Decimal("350.00"),
            selling_price=Decimal("340.00"),
            unit_cost=Decimal("230.00"),
        ),
        3,
    ),
    (
        Book(
            sku="9788173711466",
            title="Wings of Fire",
            author="A. P. J. Abdul Kalam",
            isbn="9788173711466",
            publisher="Universities Press",
            mrp=Decimal("350.00"),
            selling_price=Decimal("300.00"),
            unit_cost=Decimal("210.00"),
        ),
        2,
    ),
]


def seed_catalogue(repos: Repositories) -> list[tuple[Book, int]]:
    """Idempotently add the seed books with opening stock. Returns (book, stock) for each."""
    out = []
    for template, stock in SEED_BOOKS:
        existing = repos.catalogue.find_by_isbn(template.isbn or "")
        book = existing or template.model_copy(update={"id": template.sku})
        if not existing:
            repos.catalogue.add(book)
        repos.inventory.append(
            InventoryEntry(
                book_id=book.id, delta=stock, reason="opening stock", source_key=f"seed:{book.sku}"
            )
        )
        out.append((book, repos.inventory.on_hand(book.id)))
    return out
