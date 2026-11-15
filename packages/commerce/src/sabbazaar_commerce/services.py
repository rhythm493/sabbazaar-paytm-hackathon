import json
import re
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sabbazaar_commerce.models import AuditEvent, Product, ProductVariant, ProposedAction, Store
from sabbazaar_contracts import ProductDraftIn, ProductOut, VariantOut


def audit(db: Session, event_type: str, message: str, entity_type: str | None = None, entity_id: str | None = None, details: dict | None = None) -> None:
    db.add(AuditEvent(event_type=event_type, message=message, entity_type=entity_type, entity_id=entity_id, details_json=json.dumps(details or {})))


def slugify(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{base[:80] or 'product'}-{uuid.uuid4().hex[:8]}"


def ensure_store(db: Session) -> Store:
    store = db.scalar(select(Store).order_by(Store.id))
    if store:
        return store
    store = Store(name="Meena's Sarees", currency="INR", price_change_threshold_percent=10.0, shopify_shop_domain=__import__("os").getenv("SHOPIFY_SHOP_DOMAIN"))
    db.add(store)
    db.flush()
    return store


def create_product(db: Session, draft: ProductDraftIn) -> Product:
    store = ensure_store(db)
    product = Product(
        store_id=store.id,
        title=draft.title,
        description_html=draft.description,
        vendor=draft.vendor,
        product_type=draft.product_type,
        tags_json=json.dumps(draft.tags),
        handle=slugify(draft.title),
        price_inr=draft.price_inr,
        confidence=draft.confidence,
        missing_fields_json=json.dumps(draft.missing_fields),
        evidence_json=json.dumps(draft.evidence),
    )
    product.variants.append(ProductVariant(sku=draft.sku, price_inr=draft.price_inr, option_values_json=json.dumps(["Default Title"])))
    db.add(product)
    db.flush()
    audit(db, "catalogue.draft.created.v1", f"Draft created for {product.title}", "product", str(product.id), {"sku": draft.sku})
    return product


def product_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        title=product.title,
        description=product.description_html,
        vendor=product.vendor,
        product_type=product.product_type,
        tags=json.loads(product.tags_json),
        handle=product.handle,
        status=product.status,
        price_inr=Decimal(product.price_inr),
        version=product.version,
        external_product_id=product.external_product_id,
        admin_url=product.admin_url,
        variants=[VariantOut(id=v.id, external_variant_id=v.external_variant_id, sku=v.sku, price_inr=Decimal(v.price_inr), inventory_item_id=v.inventory_item_id) for v in product.variants],
    )


def approve_product(db: Session, product_id: int) -> ProposedAction:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product_not_found")
    action = ProposedAction(
        product_id=product.id,
        action_type="shopify.publish_product",
        status="approved",
        payload_json=json.dumps({"product_id": product.id, "version": product.version}),
        idempotency_key=f"shopify:product:{product.id}:{product.version}",
    )
    product.status = "approved"
    db.add(action)
    audit(db, "action.approved.v1", f"Publication approved for {product.title}", "product", str(product.id), {"action_type": action.action_type})
    return action
