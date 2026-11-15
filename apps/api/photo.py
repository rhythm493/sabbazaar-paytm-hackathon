"""Single product-photo upload -> ORM draft product. Mount with ``install(app)``.

Flow (ADR 0003 — agents never reach connectors):

  image upload (PNG/JPEG/WebP, <= 10 MB)
    -> Gemini vision via the ADR 0007 provider-neutral model layer
       (``sabbazaar_agents.photo_extract.extract_product_photo``)
    -> deterministic merge: merchant form overrides > extraction
    -> ``services.create_product`` (ORM Product + variant, audited)
    -> merchant reviews/edits in the Catalogue, then approves/publishes
       through the existing approve -> publish flow.

No price is ever invented: when neither the photo nor the merchant form
provides a price, the request is rejected with 422. SKU falls back to a
generated ``PHOTO-<hex>`` id (our own identifier, not a merchant fact).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from sabbazaar_commerce import SessionLocal, audit
from sabbazaar_commerce.services import create_product
from sabbazaar_contracts.schemas import ProductDraftIn

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"

router = APIRouter(tags=["photo-products"])


def get_db():
    with SessionLocal() as db:
        yield db


def sniff_image_type(content: bytes) -> str | None:
    if content.startswith(PNG_MAGIC):
        return "image/png"
    if content.startswith(JPEG_MAGIC):
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def _parse_json(text: str | None, fallback: Any) -> Any:
    try:
        return json.loads(text) if text else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat(sep=" ") if value else None


def _model_from_env() -> Any | None:
    enabled = os.getenv("MODEL_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    name = os.getenv("MODEL_NAME", "").strip()
    key = os.getenv("MODEL_API_KEY", "").strip()
    if not enabled or not name or not key:
        return None
    from sabbazaar_agents.models import build_chat_model

    return build_chat_model(
        provider=os.getenv("MODEL_PROVIDER", "google_genai").strip() or "google_genai",
        model=name,
        api_key=key,
        base_url=os.getenv("MODEL_BASE_URL", "").strip() or None,
    )


def product_api(product: Any) -> dict:
    missing = []
    for item in _parse_json(product.missing_fields_json, []):
        missing.append(item if isinstance(item, dict) else {"field": str(item), "reason": "Not provided in the source material"})

    evidence = _parse_json(product.evidence_json, product.evidence_json)
    evidence_summary = evidence.get("summary") if isinstance(evidence, dict) else None
    if not evidence_summary and evidence not in (None, {}, ""):
        evidence_summary = evidence if isinstance(evidence, str) else json.dumps(evidence, ensure_ascii=False)

    variants = [
        {
            "id": str(v.id),
            "sku": v.sku,
            "title": v.title,
            "price_inr": float(v.price_inr) if v.price_inr is not None else None,
            "inventory_item_id": v.inventory_item_id,
            "stock_on_hand": v.stock_on_hand,
        }
        for v in product.variants
    ]
    return {
        "id": str(product.id),
        "store_id": str(product.store_id),
        "status": product.status,
        "version": product.version,
        "title": product.title,
        "description": product.description_html or None,
        "price_inr": float(product.price_inr) if product.price_inr is not None else None,
        "category": product.product_type,
        "tags": _parse_json(product.tags_json, []),
        "image_url": None,
        "missing_fields": missing,
        "confidence": product.confidence,
        "evidence": evidence_summary,
        "created_at": _isoformat(product.created_at),
        "updated_at": _isoformat(product.updated_at),
        "ingestion_id": None,
        "external_product_id": product.external_product_id,
        "admin_url": product.admin_url,
        "variants": variants,
        "stock_on_hand": sum(v["stock_on_hand"] for v in variants),
    }


@router.post("/v1/products/photo", status_code=201)
async def photo_product(
    file: UploadFile = File(...),
    price_inr: str | None = Form(None),
    sku: str | None = Form(None),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
) -> Any:
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(422, "The uploaded image is empty")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"Images must be at most {MAX_IMAGE_BYTES // 1_048_576} MB")
    media_type = sniff_image_type(content)
    if media_type is None:
        raise HTTPException(415, "Upload a PNG, JPEG or WebP image of the product")

    # Merchant form overrides beat the model; nothing is invented.
    merchant_title = (title or "").strip()
    merchant_sku = (sku or "").strip()
    merchant_price: Decimal | None = None
    if price_inr is not None and price_inr.strip():
        try:
            merchant_price = Decimal(price_inr.strip())
        except InvalidOperation:
            raise HTTPException(422, "price_inr must be a number, e.g. 799 or 799.00") from None
        if merchant_price <= 0:
            raise HTTPException(422, "price_inr must be greater than 0")

    model = _model_from_env()
    extracted = None
    if model is not None:
        from sabbazaar_agents.photo_extract import PhotoExtractionFailed, extract_product_photo

        try:
            extracted = extract_product_photo(model, content, media_type)
        except PhotoExtractionFailed as exc:
            raise HTTPException(502, f"AI extraction failed: {exc}") from None
    elif merchant_title and merchant_price is not None:
        # Model not configured but the merchant gave everything required — allow the draft.
        pass
    else:
        raise HTTPException(
            503,
            "Photo AI is not configured (set MODEL_ENABLED/MODEL_NAME/MODEL_API_KEY) and the form "
            "did not supply a title and price.",
        )

    final_title = merchant_title or (extracted.title if extracted else "").strip()
    if not final_title:
        raise HTTPException(422, "Could not determine a product title; pass `title` or use a clearer photo")

    missing: list[str] = list(extracted.missing_fields) if extracted else ["description"]
    price = merchant_price
    if price is None:
        if extracted and extracted.price_inr is not None and extracted.price_inr > 0:
            price = extracted.price_inr
        else:
            raise HTTPException(422, "No price visible in the photo; pass price_inr in the form")

    final_sku = merchant_sku or (extracted.sku if extracted else None) or f"PHOTO-{uuid.uuid4().hex[:8].upper()}"
    sku_generated = not merchant_sku and not (extracted and extracted.sku)

    missing = sorted(set(missing) - {"title", "price_inr", "sku"})
    evidence: dict[str, Any] = {
        "source": "photo-upload",
        "filename": file.filename,
        "media_type": media_type,
        "model_name": os.getenv("MODEL_NAME", "").strip() if model is not None else None,
        "confidence": extracted.confidence if extracted else 1.0,
        "notes": extracted.notes if extracted else [],
        "sku_generated": sku_generated,
    }
    if extracted and extracted.price_inr is not None:
        evidence["extracted_price_inr"] = str(extracted.price_inr)

    draft = ProductDraftIn(
        title=final_title[:255],
        description=extracted.description if extracted else "",
        vendor=(extracted.vendor if extracted and extracted.vendor else "SabBazaar")[:160],
        product_type=(extracted.product_type if extracted and extracted.product_type else "General")[:160],
        tags=["sabbazaar", "photo-upload"],
        price_inr=price,
        sku=final_sku[:80],
        evidence=evidence,
        confidence=extracted.confidence if extracted else 1.0,
        missing_fields=missing,
    )
    try:
        product = create_product(db, draft)
    except Exception:
        db.rollback()
        raise
    db.commit()
    db.refresh(product)
    audit(
        db,
        "catalogue.photo.draft.created.v1",
        f"Draft created from product photo: {product.title}",
        "product",
        str(product.id),
        {"sku": final_sku, "filename": file.filename, "sku_generated": sku_generated},
    )
    db.commit()
    return product_api(product)


def install(app: FastAPI) -> None:
    app.include_router(router)
