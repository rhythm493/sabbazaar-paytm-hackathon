"""Declarative per-channel listing requirements. Data only; an entry here does not imply a connector."""

from __future__ import annotations

from enum import StrEnum


class Level(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"


SHOPIFY_BOOKS: dict[str, Level] = {
    "title": Level.REQUIRED,
    "selling_price": Level.REQUIRED,
    "quantity": Level.REQUIRED,
    "isbn": Level.RECOMMENDED,
    "author": Level.RECOMMENDED,
    "publisher": Level.RECOMMENDED,
}

REGISTRY: dict[tuple[str, str], dict[str, Level]] = {
    ("shopify", "books"): SHOPIFY_BOOKS,
}

CHANNEL_LABELS = {"shopify": "Shopify"}


def rules_for(channel: str, category: str = "books") -> dict[str, Level]:
    return REGISTRY.get((channel, category), {})


def label(channel: str) -> str:
    return CHANNEL_LABELS.get(channel, channel.title())
