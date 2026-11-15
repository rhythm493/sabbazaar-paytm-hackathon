"""Integration tests for the voice/text command pipeline (apps.api.voice).

Mounts only the voice router on a fresh FastAPI app. The LLM parse step
(`propose_inventory_commands`) and Sarvam STT (`transcribe_audio`) are
monkeypatched — no network calls. The Shopify channel is the in-memory
FakeConnector (SHOPIFY_CONNECTOR=fake).

Note: `apps.api.voice` keeps a module-level connector singleton, so tests use
`voice.get_connector().add_existing(...)` to seed channel state before approval.
"""

import os
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from alembic import command

TEST_DIR = Path(tempfile.mkdtemp(prefix="sabbazaar-test-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DIR / 'test.db'}")
os.environ.setdefault("SHOPIFY_CONNECTOR", "fake")
os.environ["SPEECH_ENABLED"] = "false"

import apps.api.voice as voice  # noqa: E402
from sabbazaar_commerce import Product, ProductVariant, SessionLocal, ensure_store  # noqa: E402
from sabbazaar_contracts.commands import CommandExtraction, CommandOp, InventoryCommand  # noqa: E402

app = FastAPI()
app.include_router(voice.router)


@pytest.fixture(scope="module")
def client():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def seeded(client):
    """Two products sharing a title word (for ambiguity tests) plus one unique."""
    seeds = [
        ("Banarasi Silk Saree Alpha", "TEST-BAN-001", "8999.00"),
        ("Banarasi Cotton Dupatta Beta", "TEST-BAN-002", "1499.00"),
        ("Chanderi Silk Saree Gamma", "TEST-CHAND-003", "2200.00"),
    ]
    with SessionLocal() as db:
        store = ensure_store(db)
        for title, sku, price in seeds:
            product = Product(
                store_id=store.id,
                title=title,
                handle=f"test-{sku.lower()}",
                price_inr=Decimal(price),
                status="draft",
                description_html="<p>test</p>",
                vendor="Test Vendor",
                product_type="Sarees",
                tags_json="[]",
                confidence=0.9,
                missing_fields_json="[]",
                evidence_json="{}",
            )
            product.variants.append(
                ProductVariant(sku=sku, price_inr=Decimal(price), option_values_json='["Default Title"]')
            )
            db.add(product)
        db.commit()
    return seeds


def extraction(commands):
    return CommandExtraction(commands=commands, unparsed=[])


def test_text_command_proposes_action(client, seeded, monkeypatch):
    cmd = InventoryCommand(
        op=CommandOp.SET_PRICE,
        product_query="TEST-CHAND-003",
        price_inr=450,
        rationale="Merchant asked to set the price to 450.",
    )
    monkeypatch.setattr(voice, "propose_inventory_commands", lambda transcript: extraction([cmd]))

    resp = client.post("/v1/commands", data={"text": "price of TEST-CHAND-003 to 450"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["message"].startswith("Proposed")
    assert len(body["actions"]) == 1
    action = body["actions"][0]
    assert action["type"] == "shopify.update_product"
    assert action["status"] == "awaiting_approval"
    assert action["payload"]["price_inr_new"] == 450.0
    assert action["payload"]["sku"] == "TEST-CHAND-003"

    listed = client.get("/v1/actions", params={"status": "awaiting_approval"})
    assert listed.status_code == 200
    ids = [a["id"] for a in listed.json()]
    assert action["id"] in ids


def test_approve_set_price_updates_orm_and_channel_is_recorded(client, seeded, monkeypatch):
    cmd = InventoryCommand(
        op=CommandOp.SET_PRICE,
        product_query="TEST-BAN-001",
        price_inr=7500,
        rationale="Festival discount.",
    )
    monkeypatch.setattr(voice, "propose_inventory_commands", lambda transcript: extraction([cmd]))

    created = client.post("/v1/commands", data={"text": "price of TEST-BAN-001 to 7500"})
    assert created.status_code == 200, created.text
    action_id = created.json()["actions"][0]["id"]

    # Pretend the product already exists on the channel.
    connector = voice.get_connector()
    assert getattr(connector, "simulated", False) is True
    connector.add_existing("TEST-BAN-001", Decimal("8999.00"), 10)

    approved = client.post(f"/v1/actions/{action_id}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "executed"

    with SessionLocal() as db:
        variant = db.query(ProductVariant).filter_by(sku="TEST-BAN-001").one()
        product = db.get(Product, variant.product_id)
        assert float(variant.price_inr) == 7500.0
        assert float(product.price_inr) == 7500.0
        assert product.version == 2  # bumped from the seeded default of 1

    # Idempotent re-approve: returns current state, does not re-execute.
    again = client.post(f"/v1/actions/{action_id}/approve")
    assert again.status_code == 200
    assert again.json()["status"] == "executed"


def test_reject_action(client, seeded, monkeypatch):
    cmd = InventoryCommand(
        op=CommandOp.SET_STOCK,
        product_query="TEST-CHAND-003",
        quantity=40,
        rationale="Restock.",
    )
    monkeypatch.setattr(voice, "propose_inventory_commands", lambda transcript: extraction([cmd]))

    created = client.post("/v1/commands", data={"text": "stock of TEST-CHAND-003 to 40"})
    assert created.status_code == 200, created.text
    action_id = created.json()["actions"][0]["id"]

    rejected = client.post(f"/v1/actions/{action_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    # Rejecting twice is a conflict.
    rejected_again = client.post(f"/v1/actions/{action_id}/reject")
    assert rejected_again.status_code == 409


def test_ambiguous_query_creates_no_action(client, seeded, monkeypatch):
    cmd = InventoryCommand(
        op=CommandOp.SET_STOCK,
        product_query="Banarasi",
        quantity=40,
        rationale="Restock all banarasi.",
    )
    monkeypatch.setattr(voice, "propose_inventory_commands", lambda transcript: extraction([cmd]))

    resp = client.post("/v1/commands", data={"text": "stock of banarasi to 40"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["actions"] == []
    assert any("matches:" in note for note in body["unparsed"])
    assert body["message"].startswith("Which product did you mean")


def test_speech_disabled_file_upload_returns_503(client, seeded):
    resp = client.post(
        "/v1/commands",
        files={"file": ("note.webm", b"fake-audio-bytes", "audio/webm")},
    )
    assert resp.status_code == 503
    assert "SPEECH_ENABLED" in resp.json()["detail"]


def test_speech_enabled_stt_path_uses_monkeypatched_transcribe(client, seeded, monkeypatch):
    cmd = InventoryCommand(
        op=CommandOp.SET_STOCK,
        product_query="TEST-CHAND-003",
        quantity=25,
        rationale="Restock from voice note.",
    )
    monkeypatch.setenv("SPEECH_ENABLED", "true")
    monkeypatch.setattr(voice, "transcribe_audio", lambda *a, **kw: ("stock of TEST-CHAND-003 to 25", "en-IN"))
    monkeypatch.setattr(voice, "propose_inventory_commands", lambda transcript: extraction([cmd]))

    resp = client.post(
        "/v1/commands",
        files={"file": ("note.webm", b"fake-audio-bytes", "audio/webm")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["transcript"] == "stock of TEST-CHAND-003 to 25"
    assert body["language_code"] == "en-IN"
    assert len(body["actions"]) == 1
