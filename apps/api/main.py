import json
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from apps.api.bill_intake.routes import install as install_bill_intake
from sabbazaar_commerce import (
    AuditEvent,
    ConnectorJob,
    Listing,
    Product,
    ProductVariant,
    ProposedAction,
    SessionLocal,
    approve_product,
    audit,
    create_product,
    ensure_store,
)
from sabbazaar_connectors import FakeShopifyConnector, ShopifyConnector
from sabbazaar_contracts import ProductDraftIn


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        ensure_store(db)
        db.commit()
    yield


app = FastAPI(title="SabBazaar API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("WEB_ORIGINS", "http://localhost:5173").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

install_bill_intake(app)


def get_db():
    with SessionLocal() as db:
        yield db


def get_connector():
    if os.getenv("SHOPIFY_CONNECTOR", "shopify").lower() == "fake":
        return FakeShopifyConnector()
    try:
        return ShopifyConnector()
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


class StorePatch(BaseModel):
    price_change_threshold_pct: float = Field(..., ge=1, le=50)


class ProductPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    price_inr: float | None = Field(default=None, gt=0)
    category: str | None = None
    tags: list[str] | None = None
    image_url: str | None = None
    version: int


class PublicationRequest(BaseModel):
    product_ids: list[str]
    channels: list[str] = ["shopify"]


def parse_json(value: str | None, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default


def int_id(value: str | int, field: str = "id") -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(422, f"Invalid {field}: expected an integer ID")
    if parsed < 1:
        raise HTTPException(422, f"Invalid {field}: expected a positive integer ID")
    return parsed


def isoformat(value) -> str | None:
    return value.isoformat() if value else None


def store_api(store):
    return {
        "id": str(store.id),
        "name": store.name,
        "owner_name": "Meena",
        "gst_number": None,
        "pan_number": None,
        "price_change_threshold_pct": store.price_change_threshold_percent,
    }


def product_api(product: Product) -> dict:
    missing = []
    for item in parse_json(product.missing_fields_json, []):
        if isinstance(item, dict):
            missing.append(item)
        else:
            missing.append({"field": str(item), "reason": "Not provided in the source material"})

    evidence = parse_json(product.evidence_json, product.evidence_json)
    evidence_summary = evidence.get("summary") if isinstance(evidence, dict) else None
    if not evidence_summary and evidence not in (None, {}, ""):
        evidence_summary = json.dumps(evidence, ensure_ascii=False)

    return {
        "id": str(product.id),
        "store_id": str(product.store_id),
        "status": product.status,
        "version": product.version,
        "title": product.title,
        "description": product.description_html or None,
        "price_inr": float(product.price_inr) if product.price_inr is not None else None,
        "category": product.product_type,
        "tags": parse_json(product.tags_json, []),
        "image_url": None,
        "missing_fields": missing,
        "confidence": product.confidence,
        "evidence": evidence_summary,
        "created_at": isoformat(product.created_at),
        "updated_at": isoformat(product.updated_at),
        "ingestion_id": None,
        "external_product_id": product.external_product_id,
        "admin_url": product.admin_url,
    }


def listing_api(listing: Listing) -> dict:
    return {
        "id": str(listing.id),
        "product_id": str(listing.product_id),
        "channel": listing.channel,
        "status": listing.status,
        "channel_listing_id": listing.external_product_id,
        "channel_url": listing.admin_url,
        "error": None,
        "job_id": None,
        "created_at": isoformat(listing.created_at),
        "updated_at": isoformat(listing.updated_at),
    }


def activity_api(event: AuditEvent, store_id: int) -> dict:
    event_type = event.event_type.removesuffix(".v1")
    event_type = "product.approved" if event_type == "action.approved" else event_type
    details = parse_json(event.details_json, {})
    return {
        "id": str(event.id),
        "event_type": event_type,
        "occurred_at": isoformat(event.created_at),
        "merchant_id": str(store_id),
        "aggregate_type": event.entity_type or "unknown",
        "aggregate_id": event.entity_id or "",
        "summary": event.message,
        "metadata": details if isinstance(details, dict) else {"value": details},
    }


def get_product_or_404(db: Session, product_id: str | int) -> Product:
    product = db.get(Product, int_id(product_id, "product_id"))
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ready"}


@app.get("/v1/store")
def get_store(db: Session = Depends(get_db)):
    store = ensure_store(db)
    db.commit()
    return store_api(store)


@app.patch("/v1/store")
def update_store(patch: StorePatch, db: Session = Depends(get_db)):
    store = ensure_store(db)
    store.price_change_threshold_percent = patch.price_change_threshold_pct
    audit(db, "store.updated.v1", "Price change threshold updated", "store", str(store.id), {"price_change_threshold_pct": patch.price_change_threshold_pct})
    db.commit()
    db.refresh(store)
    return store_api(store)


@app.get("/v1/channels")
def channels():
    if os.getenv("SHOPIFY_CONNECTOR", "shopify").lower() == "fake":
        shopify_connected = True
        shopify_message = "Fake connector selected for local development"
    else:
        shopify_connected = bool(
            os.getenv("SHOPIFY_SHOP_DOMAIN")
            and (os.getenv("SHOPIFY_ACCESS_TOKEN") or (os.getenv("SHOPIFY_CLIENT_ID") and os.getenv("SHOPIFY_CLIENT_SECRET")))
        )
        shopify_message = "Configured for draft products only" if shopify_connected else "Set the Shopify development-store credentials to connect"
    return [
        {"channel": "shopify", "connected": shopify_connected, "label": "Shopify Dev Store", "status_message": shopify_message},
        {"channel": "ondc", "connected": False, "label": "ONDC", "status_message": "Deferred roadmap integration"},
        {"channel": "meesho", "connected": False, "label": "Meesho", "status_message": "Deferred roadmap integration"},
        {"channel": "amazon", "connected": False, "label": "Amazon", "status_message": "Deferred roadmap integration"},
    ]


@app.post("/v1/ingestions")
async def create_ingestion(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        raise HTTPException(501, "Image/PDF AI extraction is not implemented yet. Use the sample fixture for this demo.")

    if content_type.startswith("application/json"):
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "Invalid JSON body") from exc
    else:
        payload = {}
    if payload.get("fixture") != "saree_sample":
        raise HTTPException(400, "Unsupported ingestion fixture. Use fixture 'saree_sample'.")

    store = ensure_store(db)
    handle = "fixture-kanjivaram-silk-saree"
    product = db.scalar(select(Product).where(Product.handle == handle))
    if product is None:
        product = Product(
            store_id=store.id,
            title="Kanjivaram Silk Saree",
            description_html="<p>Traditional Kanjivaram silk saree with a rich border. Sample fixture for SabBazaar.</p>",
            vendor="Meena's Sarees",
            product_type="Sarees",
            tags_json=json.dumps(["saree", "kanjivaram", "silk", "fixture"]),
            handle=handle,
            status="draft",
            price_inr="8999.00",
            confidence=0.96,
            missing_fields_json="[]",
            evidence_json=json.dumps({"source": "fixture", "summary": "Sample catalogue fixture"}),
        )
        product.variants.append(ProductVariant(sku="FIX-SARI-0001", price_inr="8999.00", option_values_json='["Default Title"]'))
        db.add(product)
        db.flush()
        audit(db, "ingestion.requested.v1", "Sample saree ingestion requested", "product", str(product.id))
        audit(db, "catalogue.draft.created.v1", f"Draft created for {product.title}", "product", str(product.id), {"fixture": "saree_sample"})
        db.commit()
        db.refresh(product)

    return {
        "id": f"ingestion-{product.id}",
        "store_id": str(store.id),
        "status": "completed",
        "file_name": "saree_sample.fixture",
        "file_type": "fixture",
        "error": None,
        "products": [product_api(product)],
        "created_at": isoformat(product.created_at),
        "updated_at": isoformat(product.updated_at),
    }


@app.post("/v1/products", status_code=201)
def create_product_endpoint(draft: ProductDraftIn, db: Session = Depends(get_db)):
    product = create_product(db, draft)
    db.commit()
    db.refresh(product)
    return product_api(product)


@app.get("/v1/products")
def list_products(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Product)
    count_stmt = select(func.count(Product.id))
    if status:
        stmt = stmt.where(Product.status == status)
        count_stmt = count_stmt.where(Product.status == status)
    total = db.scalar(count_stmt) or 0
    products = db.scalars(stmt.order_by(Product.created_at.desc(), Product.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [product_api(p) for p in products], "total": total, "offset": offset, "limit": limit}


@app.get("/v1/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    return product_api(get_product_or_404(db, product_id))


@app.patch("/v1/products/{product_id}")
def patch_product(product_id: str, patch: ProductPatch, db: Session = Depends(get_db)):
    product = get_product_or_404(db, product_id)
    if patch.version != product.version:
        raise HTTPException(409, "Product was updated. Refresh and try again.")
    if patch.image_url is not None:
        raise HTTPException(422, "Image updates are not supported by the current backend")
    if patch.title is not None:
        product.title = patch.title
    if patch.description is not None:
        product.description_html = patch.description
    if patch.price_inr is not None:
        product.price_inr = patch.price_inr
        for variant in product.variants:
            variant.price_inr = patch.price_inr
    if patch.category is not None:
        product.product_type = patch.category
    if patch.tags is not None:
        product.tags_json = json.dumps(patch.tags)
    product.status = "draft"
    product.version += 1
    audit(db, "catalogue.draft.updated.v1", f"Draft updated for {product.title}", "product", str(product.id))
    db.commit()
    db.refresh(product)
    return product_api(product)


@app.post("/v1/products/{product_id}/approve")
def approve_product_endpoint(product_id: str, db: Session = Depends(get_db)):
    product = get_product_or_404(db, product_id)
    key = f"shopify:product:{product.id}:{product.version}"
    existing = db.scalar(select(ProposedAction).where(ProposedAction.idempotency_key == key))
    if not existing:
        approve_product(db, product.id)
    db.commit()
    db.refresh(product)
    return product_api(product)


def merchant_product_payload(product: Product, variant: ProductVariant) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description_html,
        "vendor": product.vendor,
        "product_type": product.product_type,
        "tags": json.loads(product.tags_json),
        "handle": product.handle,
        "variants": [{"sku": variant.sku, "price_inr": variant.price_inr}],
    }


async def execute_publish(product: Product, db: Session, connector, force_retry: bool = False):
    listing = db.scalar(select(Listing).where(Listing.product_id == product.id, Listing.channel == "shopify"))
    if listing and not (force_retry and listing.status == "failed"):
        return {"ok": True, "reused": True, "external_product_id": listing.external_product_id, "external_variant_id": listing.external_variant_id, "admin_url": listing.admin_url}

    action = db.scalar(select(ProposedAction).where(ProposedAction.product_id == product.id, ProposedAction.status == "approved").order_by(ProposedAction.id.desc()))
    if not action:
        raise HTTPException(409, "Merchant approval is required before Shopify publication")

    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id).order_by(ProductVariant.id))
    if not variant:
        raise HTTPException(422, "Product is missing a variant")

    idempotency_key = action.idempotency_key
    job = db.scalar(select(ConnectorJob).where(ConnectorJob.idempotency_key == idempotency_key))
    if job and job.status == "succeeded" and not force_retry:
        return {"ok": True, "reused": True, "external_product_id": job.external_product_id, "admin_url": job.admin_url}

    if not job:
        job = ConnectorJob(
            action_id=action.id,
            connector="shopify",
            operation="publish_product",
            status="running",
            idempotency_key=idempotency_key,
            request_summary_json=json.dumps({"product_id": product.id, "sku": variant.sku, "price_inr": str(variant.price_inr)}),
        )
        db.add(job)
        audit(db, "listing.publish.requested.v1", f"Shopify publication requested for {product.title}", "product", str(product.id))
        db.commit()
    else:
        job.status = "running"
        job.error_code = None
        job.error_message = None
        db.commit()

    result = await connector.publish_product(merchant_product_payload(product, variant), idempotency_key)
    if result.ok:
        variant.external_variant_id = result.external_variant_id
        variant.inventory_item_id = result.inventory_item_id
        product.external_product_id = result.external_product_id
        product.admin_url = result.admin_url
        product.status = "shopify_draft"
        job.status = "succeeded"
        job.external_product_id = result.external_product_id
        job.admin_url = result.admin_url
        job.response_summary_json = result.model_dump_json(exclude={"error_message"})
        if listing:
            listing.external_product_id = result.external_product_id or listing.external_product_id
            listing.external_variant_id = result.external_variant_id
            listing.admin_url = result.admin_url
            listing.status = "draft"
        else:
            db.add(Listing(product_id=product.id, channel="shopify", external_product_id=result.external_product_id or "", external_variant_id=result.external_variant_id, admin_url=result.admin_url, status="draft"))
        audit(db, "listing.published.v1", f"Shopify draft created for {product.title}", "product", str(product.id), {"external_product_id": result.external_product_id})
        db.commit()
        return {**result.model_dump(), "reused": False}

    job.status = "failed"
    job.error_code = result.error_code
    job.error_message = result.error_message
    job.response_summary_json = result.model_dump_json()
    product.status = "publish_failed"
    if listing:
        listing.status = "failed"
        listing.admin_url = result.admin_url
    audit(db, "listing.failed.v1", f"Shopify publication failed for {product.title}", "product", str(product.id), {"error_code": result.error_code})
    db.commit()
    raise HTTPException(502, result.error_message or "Shopify publication failed")


@app.post("/v1/products/{product_id}/publish")
async def publish_product(product_id: str, db: Session = Depends(get_db), connector=Depends(get_connector)):
    return await execute_publish(get_product_or_404(db, product_id), db, connector)


@app.post("/v1/publications")
async def create_publications(payload: PublicationRequest, db: Session = Depends(get_db), connector=Depends(get_connector)):
    if not payload.product_ids:
        raise HTTPException(422, "Select at least one approved product")
    if any(channel != "shopify" for channel in payload.channels):
        raise HTTPException(422, "Only Shopify is available in this build")

    ids = [int_id(product_id, "product_id") for product_id in payload.product_ids]
    listings = []
    for product_id in ids:
        await execute_publish(get_product_or_404(db, str(product_id)), db, connector)
        listing = db.scalar(select(Listing).where(Listing.product_id == product_id, Listing.channel == "shopify"))
        if not listing:
            raise HTTPException(502, "Shopify publication completed without a listing record")
        listings.append(listing_api(listing))
    return listings


@app.get("/v1/listings")
def list_listings(product_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Listing)
    if product_id:
        stmt = stmt.where(Listing.product_id == int_id(product_id, "product_id"))
    listings = db.scalars(stmt.order_by(Listing.created_at.desc(), Listing.id.desc())).all()
    return [listing_api(listing) for listing in listings]


@app.get("/v1/listings/{listing_id}")
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    listing = db.get(Listing, int_id(listing_id, "listing_id"))
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing_api(listing)


@app.post("/v1/listings/{listing_id}/retry")
async def retry_listing(listing_id: str, db: Session = Depends(get_db), connector=Depends(get_connector)):
    listing = db.get(Listing, int_id(listing_id, "listing_id"))
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing.status == "draft":
        return listing_api(listing)
    if listing.status != "failed":
        raise HTTPException(409, "Only failed listings can be retried")
    await execute_publish(get_product_or_404(db, str(listing.product_id)), db, connector, force_retry=True)
    db.refresh(listing)
    return listing_api(listing)


@app.get("/v1/activity")
def activity(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db)):
    store = ensure_store(db)
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)).all()
    return [activity_api(event, store.id) for event in events]
