import json
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
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
    product_out,
)
from sabbazaar_connectors import FakeShopifyConnector, ShopifyConnector
from sabbazaar_contracts import ActivityOut, ProductDraftIn


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


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ready"}


@app.post("/v1/products", status_code=201)
def create_product_endpoint(draft: ProductDraftIn, db: Session = Depends(get_db)):
    product = create_product(db, draft)
    db.commit()
    db.refresh(product)
    return product_out(product)


@app.get("/v1/products")
def list_products(db: Session = Depends(get_db)):
    products = db.scalars(select(Product).order_by(Product.created_at.desc())).all()
    return [product_out(p) for p in products]


@app.get("/v1/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product_out(product)


@app.post("/v1/products/{product_id}/approve")
def approve_product_endpoint(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    key = f"shopify:product:{product.id}:{product.version}"
    existing = db.scalar(select(ProposedAction).where(ProposedAction.idempotency_key == key))
    action = existing or approve_product(db, product_id)
    db.commit()
    return {"id": action.id, "action_type": action.action_type, "status": action.status, "idempotency_key": action.idempotency_key}


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


@app.post("/v1/products/{product_id}/publish")
async def publish_product(product_id: int, db: Session = Depends(get_db), connector=Depends(get_connector)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    listing = db.scalar(select(Listing).where(Listing.product_id == product.id, Listing.channel == "shopify"))
    if listing:
        return {"ok": True, "reused": True, "external_product_id": listing.external_product_id, "external_variant_id": listing.external_variant_id, "admin_url": listing.admin_url}

    action = db.scalar(select(ProposedAction).where(ProposedAction.product_id == product.id, ProposedAction.status == "approved").order_by(ProposedAction.id.desc()))
    if not action:
        raise HTTPException(409, "Merchant approval is required before Shopify publication")

    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id).order_by(ProductVariant.id))
    if not variant:
        raise HTTPException(422, "Product is missing a variant")

    idempotency_key = action.idempotency_key
    job = db.scalar(select(ConnectorJob).where(ConnectorJob.idempotency_key == idempotency_key))
    if job and job.status == "succeeded":
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
        db.add(Listing(product_id=product.id, channel="shopify", external_product_id=result.external_product_id or "", external_variant_id=result.external_variant_id, admin_url=result.admin_url, status="draft"))
        audit(db, "listing.published.v1", f"Shopify draft created for {product.title}", "product", str(product.id), {"external_product_id": result.external_product_id})
        db.commit()
        return {**result.model_dump(), "reused": False}

    job.status = "failed"
    job.error_code = result.error_code
    job.error_message = result.error_message
    job.response_summary_json = result.model_dump_json()
    product.status = "publish_failed"
    audit(db, "listing.failed.v1", f"Shopify publication failed for {product.title}", "product", str(product.id), {"error_code": result.error_code})
    db.commit()
    raise HTTPException(502, result.error_message or "Shopify publication failed")


@app.get("/v1/activity", response_model=list[ActivityOut])
def activity(db: Session = Depends(get_db)):
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(30)).all()
    return [ActivityOut(id=e.id, event_type=e.event_type, message=e.message, entity_type=e.entity_type, entity_id=e.entity_id, created_at=e.created_at) for e in events]
