"""Build the exact, hashed preview the owner confirms. Confirmation is bound to this hash."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from commerce.intake.questions import effective
from commerce.intake.requirements import Level, label, rules_for
from commerce.repositories import CatalogueRepository, InventoryRepository, ListingRepository
from contracts.channels import ListingPayload
from contracts.ingestion import ChannelChange, LineKind, Preview, PreviewLine, WorkingLine


class PreviewNotReady(ValueError):
    pass


def sku_for(ingestion_id: str, line: WorkingLine) -> str:
    return line.get("isbn") or f"SB-{ingestion_id[:8]}-{line.id}"


def preview_hash(lines: list[PreviewLine]) -> str:
    blob = json.dumps([pl.model_dump(mode="json") for pl in lines], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def build_preview(
    *,
    ingestion_id: str,
    lines: list[WorkingLine],
    catalogue: CatalogueRepository,
    inventory: InventoryRepository,
    listings: ListingRepository,
    channels: list[str],
    version: int,
) -> Preview:
    out: list[PreviewLine] = []
    for line in lines:
        if line.dropped:
            continue
        if line.kind not in (LineKind.RESTOCK, LineKind.NEW):
            raise PreviewNotReady(f"line {line.id} is not resolved ({line.kind})")
        book = catalogue.get(line.matched_book_id) if line.matched_book_id else None
        qty: int = line.get("quantity")
        price_after: Decimal | None = effective(line, book, "selling_price")
        if price_after is None:
            raise PreviewNotReady(f"line {line.id} has no selling price")
        before = inventory.on_hand(book.id) if book else 0
        after = before + qty
        price_before = book.selling_price if book else None
        pct = (
            round(float((price_after - price_before) / price_before * 100), 2)
            if price_before and price_after != price_before
            else None
        )
        title = effective(line, book, "title")
        sku = book.sku if book else sku_for(ingestion_id, line)
        mrp = line.get("mrp") or (book.mrp if book else None)
        unit_cost = line.get("unit_cost") or (book.unit_cost if book else None)

        warnings: list[str] = []
        changes: list[ChannelChange] = []
        for channel in channels:
            for field, level in rules_for(channel).items():
                if level == Level.RECOMMENDED and effective(line, book, field) in (None, ""):
                    warnings.append(f"{label(channel)}: {field} is missing (recommended)")
            listing = listings.get(book.id, channel) if book else None
            if listing:
                changes.append(
                    ChannelChange(
                        channel=channel,
                        operation="set_inventory",
                        summary=(
                            f"{label(channel)}: inventory "
                            f"{listing.last_known_quantity if listing.last_known_quantity is not None else '?'}"
                            f" -> {after}"
                        ),
                        quantity=after,
                        expected_current=listing.last_known_quantity,
                    )
                )
                if price_before is not None and price_after != price_before:
                    changes.append(
                        ChannelChange(
                            channel=channel,
                            operation="update_product",
                            summary=f"{label(channel)}: price ₹{price_before} -> ₹{price_after}",
                            price=price_after,
                        )
                    )
            else:
                changes.append(
                    ChannelChange(
                        channel=channel,
                        operation="publish_product",
                        summary=(
                            f"{label(channel)}: create draft product at ₹{price_after}, "
                            f"inventory {after}"
                        ),
                        payload=ListingPayload(
                            sku=sku,
                            title=title,
                            author=effective(line, book, "author"),
                            isbn=effective(line, book, "isbn"),
                            publisher=effective(line, book, "publisher"),
                            price=price_after,
                            unit_cost=unit_cost,
                            quantity=after,
                        ),
                    )
                )
        out.append(
            PreviewLine(
                line_id=line.id,
                kind=line.kind,
                book_id=book.id if book else None,
                sku=sku,
                title=title,
                stock_before=before,
                stock_after=after,
                quantity_added=qty,
                price_before=price_before,
                price_after=price_after,
                price_change_pct=pct,
                mrp=mrp,
                unit_cost=unit_cost,
                author=effective(line, book, "author"),
                isbn=effective(line, book, "isbn"),
                publisher=effective(line, book, "publisher"),
                warnings=warnings,
                notes=list(line.notes),
                channel_changes=changes,
            )
        )
    return Preview(version=version, hash=preview_hash(out), lines=out)
