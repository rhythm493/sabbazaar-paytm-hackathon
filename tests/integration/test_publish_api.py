import os
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

TEST_DIR = Path(tempfile.mkdtemp(prefix="sabbazaar-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR / 'test.db'}"
os.environ["SHOPIFY_CONNECTOR"] = "fake"
os.environ["WEB_ORIGINS"] = "http://localhost:5173"

from apps.api.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    with TestClient(app) as test_client:
        yield test_client


def draft(title="Kanjivaram Silk Saree"):
    return {
        "title": title,
        "description": "<p>Demo saree</p>",
        "vendor": "Meena's Sarees",
        "product_type": "Sarees",
        "tags": ["saree"],
        "price_inr": "8999.00",
        "sku": "SBZ-SARI-0001",
        "evidence": {"source": "test"},
        "confidence": 0.95,
        "missing_fields": [],
    }


def test_publish_requires_approval_and_is_idempotent(client):
    created = client.post("/v1/products", json=draft())
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    before_approval = client.post(f"/v1/products/{product_id}/publish")
    assert before_approval.status_code == 409

    approved = client.post(f"/v1/products/{product_id}/approve")
    assert approved.status_code == 200, approved.text

    published = client.post(f"/v1/products/{product_id}/publish")
    assert published.status_code == 200, published.text
    assert published.json()["ok"] is True
    assert published.json()["external_product_id"].startswith("gid://shopify/Product/")

    retried = client.post(f"/v1/products/{product_id}/publish")
    assert retried.status_code == 200, retried.text
    assert retried.json()["reused"] is True

    listed = client.get(f"/v1/products/{product_id}")
    assert listed.status_code == 200
    assert listed.json()["status"] == "shopify_draft"
    assert listed.json()["external_product_id"]

    activity = client.get("/v1/activity")
    assert activity.status_code == 200
    event_types = [event["event_type"] for event in activity.json()]
    assert "catalogue.draft.created.v1" in event_types
    assert "action.approved.v1" in event_types
    assert "listing.publish.requested.v1" in event_types
    assert "listing.published.v1" in event_types
