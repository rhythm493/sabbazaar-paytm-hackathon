import os
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from alembic import command

TEST_DIR = Path(tempfile.mkdtemp(prefix="sabbazaar-test-photo-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DIR / 'test.db'}")
os.environ.setdefault("SHOPIFY_CONNECTOR", "fake")
os.environ["WEB_ORIGINS"] = "http://localhost:5173"

import sabbazaar_agents.photo_extract as photo_extract  # noqa: E402
from apps.api import photo  # noqa: E402
from sabbazaar_commerce import AuditEvent, Product, SessionLocal  # noqa: E402
from sabbazaar_contracts.photo import ProductPhotoExtraction  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"\x00" * 64


class DummyModel:
    """Stand-in for a chat model; extraction is always monkeypatched."""


@pytest.fixture(scope="module")
def client():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    app = FastAPI()
    photo.install(app)
    with TestClient(app) as test_client:
        yield test_client


def test_photo_creates_draft_with_form_price(client, monkeypatch):
    monkeypatch.setattr(photo, "_model_from_env", lambda: DummyModel())
    monkeypatch.setattr(
        photo_extract,
        "extract_product_photo",
        lambda model, content, media_type: ProductPhotoExtraction(
            title="Photo Draft Kurti", price_inr=None, confidence=0.8
        ),
    )
    r = client.post(
        "/v1/products/photo",
        files={"file": ("kurti.png", PNG, "image/png")},
        data={"price_inr": "799.00"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "Photo Draft Kurti"
    assert body["price_inr"] == 799.0
    assert body["status"] == "draft"
    assert body["variants"][0]["stock_on_hand"] == 0

    with SessionLocal() as db:
        product = db.scalar(select(Product).where(Product.id == int(body["id"])))
        assert product is not None
        assert product.product_type == "General"
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.event_type == "catalogue.photo.draft.created.v1")
        ).all()
        assert events, "expected photo draft audit event"


def test_photo_requires_a_price(client, monkeypatch):
    monkeypatch.setattr(photo, "_model_from_env", lambda: DummyModel())
    monkeypatch.setattr(
        photo_extract,
        "extract_product_photo",
        lambda model, content, media_type: ProductPhotoExtraction(title="No Price Photo", price_inr=None),
    )
    r = client.post("/v1/products/photo", files={"file": ("p.png", PNG, "image/png")})
    assert r.status_code == 422
    assert "price" in r.json()["detail"].lower()


def test_photo_uses_extracted_price_when_no_form_price(client, monkeypatch):
    monkeypatch.setattr(photo, "_model_from_env", lambda: DummyModel())
    monkeypatch.setattr(
        photo_extract,
        "extract_product_photo",
        lambda model, content, media_type: ProductPhotoExtraction(
            title="Priced Photo Vase", price_inr=Decimal("1250.00"), confidence=0.9
        ),
    )
    r = client.post("/v1/products/photo", files={"file": ("vase.png", PNG, "image/png")})
    assert r.status_code == 201, r.text
    assert r.json()["price_inr"] == 1250.0


def test_photo_rejects_non_image(client):
    r = client.post("/v1/products/photo", files={"file": ("bill.pdf", PDF, "application/pdf")})
    assert r.status_code == 415


def test_photo_rejects_oversize(client, monkeypatch):
    monkeypatch.setattr(photo, "MAX_IMAGE_BYTES", 16)
    r = client.post("/v1/products/photo", files={"file": ("big.png", PNG, "image/png")})
    assert r.status_code == 413


def test_photo_503_without_model_and_form_fields(client, monkeypatch):
    monkeypatch.setattr(photo, "_model_from_env", lambda: None)
    r = client.post("/v1/products/photo", files={"file": ("p.png", PNG, "image/png")})
    assert r.status_code == 503


def test_photo_502_when_extraction_fails(client, monkeypatch):
    monkeypatch.setattr(photo, "_model_from_env", lambda: DummyModel())

    def boom(model, content, media_type):
        raise photo_extract.PhotoExtractionFailed("nope")

    monkeypatch.setattr(photo_extract, "extract_product_photo", boom)
    r = client.post("/v1/products/photo", files={"file": ("p.png", PNG, "image/png")})
    assert r.status_code == 502


def test_photo_rejects_bad_price(client, monkeypatch):
    monkeypatch.setattr(photo, "_model_from_env", lambda: DummyModel())
    r = client.post(
        "/v1/products/photo",
        files={"file": ("p.png", PNG, "image/png")},
        data={"price_inr": "abc"},
    )
    assert r.status_code == 422
