"""Photo-to-product extraction: provider-neutral model, structured output.

Given one product photo, ask the vision-capable chat model (ADR 0007) for a
``ProductPhotoExtraction``. Never talks to connectors and never persists
anything — the API layer owns validation, merging with merchant overrides and
draft creation.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from pydantic import ValidationError

from sabbazaar_contracts.photo import ProductPhotoExtraction

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You identify a single retail/wholesale product from ONE photo.

Return:
- title: a short, accurate product title (required if at all inferable).
- description: one or two factual sentences, no marketing fluff.
- vendor: the brand or manufacturer, only if visible on the packaging/label.
- product_type: a short category (e.g. "Books", "Sarees", "Grocery", "Dairy").
- price_inr: the MRP/printed price, ONLY if a price tag or printed price is clearly legible (digits).
- sku: ONLY if a barcode or printed SKU/code is clearly legible (digits/letters).
- confidence: 0-1 overall confidence in the extraction.
- missing_fields: list the fields you could NOT determine (e.g. "price_inr", "sku", "vendor").
- notes: short notes on anything uncertain.

Rules:
- NEVER invent a price, barcode, brand, MRP or ISBN. If unsure, leave the field null and add it to missing_fields.
- If the image shows packaging text (language/brand), transcribe it faithfully; do not translate.
- If the image is not a product photo or is unreadable, set title to "" and explain in notes.
"""

USER_PROMPT = "Extract the product details from this photo."


class PhotoExtractionFailed(Exception):
    """Raised when the model cannot produce a usable structured extraction."""


def _image_block(content: bytes, media_type: str) -> dict[str, Any]:
    return {"type": "image", "base64": base64.b64encode(content).decode(), "mime_type": media_type}


def extract_product_photo(
    model: Any,
    content: bytes,
    media_type: str,
    *,
    max_attempts: int = 2,
) -> ProductPhotoExtraction:
    """Extract product fields from a photo. Raises ``PhotoExtractionFailed``."""
    from langchain_core.messages import HumanMessage, SystemMessage

    structured = model.with_structured_output(ProductPhotoExtraction)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=[{"type": "text", "text": USER_PROMPT}, _image_block(content, media_type)]
        ),
    ]
    last: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            out = structured.invoke(messages)
            if isinstance(out, dict):
                out = ProductPhotoExtraction.model_validate(out)
            if not isinstance(out, ProductPhotoExtraction):
                raise PhotoExtractionFailed("model returned no structured output")
            return out
        except (ValidationError, PhotoExtractionFailed, ValueError) as exc:
            last = exc
            log.warning("photo extraction attempt %d failed: %s", attempt, type(exc).__name__)
        except Exception as exc:  # provider/network errors
            last = exc
            log.warning("photo extraction attempt %d error: %s", attempt, type(exc).__name__)
    raise PhotoExtractionFailed(f"photo extraction failed after {max_attempts} attempts") from last
