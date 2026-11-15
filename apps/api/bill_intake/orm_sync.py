"""Sync confirmed bill-intake changes into the SQLAlchemy ORM catalogue.

Wired into ApplyService as `on_lines_applied` / `on_jobs_run` callbacks by the
container, so the commerce layer stays database-agnostic. Every mutation is
keyed and audited:

- `inventory_ledger.source_key` = `ingestion:{ingestion_id}:{line_id}` (unique) —
  replaying the same bill never double-counts stock.
- `proposed_actions.idempotency_key` = `orm:bill:{ingestion_id}:{line_id}` —
  replaying the same bill never double-creates/double-updates products.
- `proposed_actions.idempotency_key` = `orm:bill:{ingestion_id}:{line_id}:listing` —
  listing/product gid is synced at most once per (ingestion, line).

Nothing here raises: failures roll back the unit's session and write a fresh
`bill.orm_sync_failed` audit row so the bill-intake flow is never blocked by a
catalogue-sync problem.
"""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from sabbazaar_commerce.db import SessionLocal
from sabbazaar_commerce.models import (
    InventoryLedger,
    Listing,
    Product,
    ProductVariant,
    ProposedAction,
)
from sabbazaar_commerce.services import audit, ensure_store, slugify

log = logging.getLogger(__name__)

_GID_RE = re.compile(r"products/(\d+)")


def build_orm_sync(repos):
    """Return (on_lines_applied, on_jobs_run) closures bound to the in-memory repos."""

    def on_lines_applied(ingestion_id: str, lines: list[dict[str, Any]], actor: str) -> None:
        for line in lines:
            _with_session(_sync_line, ingestion_id, line, actor)

    def on_jobs_run(ingestion_id: str, jobs: list[dict[str, Any]], actor: str) -> None:
        for job in jobs:
            _with_session(_sync_job, ingestion_id, job, actor)

    return on_lines_applied, on_jobs_run


def _safe(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, default=str))


def _with_session(fn, ingestion_id: str, item: dict[str, Any], actor: str) -> None:
    db = SessionLocal()
    try:
        fn(db, ingestion_id, item, actor)
        db.commit()
    except Exception as exc:
        db.rollback()
        log.warning("orm sync failed for ingestion %s item %s", ingestion_id, item.get("line_id"), exc_info=True)
        try:
            fail_db = SessionLocal()
            audit(
                fail_db,
                "bill.orm_sync_failed",
                f"ORM sync failed for ingestion {ingestion_id} line {item.get('line_id')}: {type(exc).__name__}",
                "ingestion",
                ingestion_id,
                {"item": _safe(item), "error": type(exc).__name__},
            )
            fail_db.commit()
        except Exception:
            fail_db.rollback()
            log.warning("failed to record orm sync failure for %s", ingestion_id, exc_info=True)
        finally:
            fail_db.close()
    finally:
        db.close()


def _marker_exists(db, key: str) -> bool:
    return db.scalar(select(ProposedAction).where(ProposedAction.idempotency_key == key)) is not None


def _sync_line(db, ingestion_id: str, line: dict[str, Any], actor: str) -> None:
    marker_key = f"orm:bill:{ingestion_id}:{line['line_id']}"
    if _marker_exists(db, marker_key):
        return

    store = ensure_store(db)
    price = Decimal(str(line["price"]))
    mrp = Decimal(str(line["mrp"])) if line.get("mrp") else None
    variant = db.scalar(select(ProductVariant).where(ProductVariant.sku == line["sku"]))
    if variant is not None:
        product = db.get(Product, variant.product_id)
        product.price_inr = price
        product.version += 1
        if mrp is not None:
            variant.compare_at_price_inr = mrp
        variant.price_inr = price
        message = f"Bill intake updated '{product.title}' price to ₹{price} (v{product.version})"
    else:
        product = Product(
            store_id=store.id,
            title=line["title"],
            description_html="",
            vendor=(line.get("publisher") or "SabBazaar"),
            product_type="Book",
            tags_json=json.dumps(["sabbazaar", "bill-ingestion"]),
            handle=slugify(line["title"]),
            status="draft",
            price_inr=price,
            confidence=1.0,
            missing_fields_json=json.dumps([]),
            evidence_json=json.dumps(
                {
                    "source": "bill-ingestion",
                    "ingestion_id": ingestion_id,
                    "isbn": line.get("isbn"),
                    "publisher": line.get("publisher"),
                    "author": line.get("author"),
                }
            ),
        )
        db.add(product)
        db.flush()
        variant = ProductVariant(
            product_id=product.id,
            sku=line["sku"],
            title="Default Title",
            price_inr=price,
            compare_at_price_inr=mrp,
            option_values_json=json.dumps(["Default Title"]),
        )
        db.add(variant)
        db.flush()
        message = f"Bill intake created draft '{product.title}' (₹{price})"

    source_key = f"ingestion:{ingestion_id}:{line['line_id']}"
    ledger_exists = db.scalar(select(InventoryLedger).where(InventoryLedger.source_key == source_key))
    if ledger_exists is None:
        delta = int(line["quantity"])
        db.add(InventoryLedger(variant_id=variant.id, delta=delta, reason=f"bill {ingestion_id}", source_key=source_key))
        variant.stock_on_hand = (variant.stock_on_hand or 0) + delta
        db.flush()

    db.add(
        ProposedAction(
            product_id=product.id,
            action_type="bill.catalogue.sync",
            status="executed",
            payload_json=json.dumps({"ingestion_id": ingestion_id, "line_id": line["line_id"], "sku": line["sku"]}),
            idempotency_key=marker_key,
        )
    )
    audit(
        db,
        "bill.catalogue.synced.v1",
        message,
        "product",
        str(product.id),
        {"ingestion_id": ingestion_id, "line_id": line["line_id"], "sku": line["sku"], "actor": actor},
    )


def _sync_job(db, ingestion_id: str, job: dict[str, Any], actor: str) -> None:
    if job.get("operation") != "publish_product" or job.get("status") != "succeeded":
        return
    marker_key = f"orm:bill:{ingestion_id}:{job['line_id']}:listing"
    if _marker_exists(db, marker_key):
        return

    sku = job.get("sku")
    if not sku:
        log.warning("orm listing sync skipped: no sku resolved for ingestion %s line %s", ingestion_id, job.get("line_id"))
        return
    variant = db.scalar(select(ProductVariant).where(ProductVariant.sku == sku))
    if variant is None:
        log.warning("orm listing sync skipped: variant %s not in ORM (ingestion %s)", sku, ingestion_id)
        return
    product = db.get(Product, variant.product_id)
    gid = None
    admin_url = job.get("admin_url")
    if admin_url:
        match = _GID_RE.search(admin_url)
        if match:
            gid = f"gid://shopify/Product/{match.group(1)}"
    if gid:
        channel = job.get("channel") or "shopify"
        product.external_product_id = gid
        product.admin_url = admin_url
        if product.status in ("draft", "approved", "publish_failed"):
            product.status = "shopify_draft"
        listing = db.scalar(select(Listing).where(Listing.product_id == product.id, Listing.channel == channel))
        if listing is None:
            listing = Listing(product_id=product.id, channel=channel, external_product_id=gid, admin_url=admin_url, status="draft")
            db.add(listing)
        else:
            listing.external_product_id = gid
            listing.admin_url = admin_url
            listing.status = "draft"
    db.add(
        ProposedAction(
            product_id=product.id,
            action_type="bill.listing.sync",
            status="executed",
            payload_json=json.dumps({"ingestion_id": ingestion_id, "line_id": job["line_id"], "channel": job.get("channel")}),
            idempotency_key=marker_key,
        )
    )
    audit(
        db,
        "bill.listing.synced.v1",
        f"Bill intake listing synced for '{product.title}' ({job.get('channel')})",
        "product",
        str(product.id),
        {"ingestion_id": ingestion_id, "line_id": job["line_id"], "admin_url": admin_url, "actor": actor},
    )
