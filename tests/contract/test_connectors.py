"""Connector contract tests: FakeConnector behaviour + Shopify operations against a mock transport."""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest

from sabbazaar_connectors.fake import FakeConnector
from sabbazaar_connectors.shopify_ops.connector import ShopifyConnector
from sabbazaar_connectors.shopify_ops.credentials import ShopifyCredentials, StaticCredentialsProvider
from sabbazaar_contracts.channels import ErrorCode, ExternalRef, ListingPayload

PAYLOAD = ListingPayload(
    sku="9781786330895",
    title="Ikigai",
    author="Hector Garcia",
    isbn="9781786330895",
    publisher="Hutchinson",
    price=Decimal("450.00"),
    unit_cost=Decimal("330.00"),
    quantity=6,
)
CREDS = ShopifyCredentials(
    shop_domain="demo.myshopify.com",
    access_token="shpat_test",
    location_id="gid://shopify/Location/1",
)


# ---------- FakeConnector ----------


def test_fake_publish_is_idempotent_and_reconciles():
    fake = FakeConnector()
    r1 = fake.publish_product(PAYLOAD, "k1")
    r2 = fake.publish_product(PAYLOAD, "k1")
    r3 = fake.publish_product(PAYLOAD, "k2")  # different key, same SKU -> no duplicate
    assert r1.ok and r1.ref == r2.ref and r3.ref.variant_id == r1.ref.variant_id
    assert len(fake.products) == 1


def test_fake_set_inventory_compare_and_set():
    fake = FakeConnector()
    ref = fake.add_existing("sku1", Decimal("10"), 12)
    assert fake.set_inventory(ref, 20, 12, "a").ok
    conflict = fake.set_inventory(ref, 30, 12, "b")
    assert not conflict.ok and conflict.error_code == ErrorCode.CONFLICT
    assert fake.find_by_sku("sku1").quantity == 20


def test_fake_failure_injection():
    fake = FakeConnector()
    fake.fail_next["publish_product"] = ErrorCode.TRANSIENT
    assert fake.publish_product(PAYLOAD, "k").error_code == ErrorCode.TRANSIENT
    assert fake.publish_product(PAYLOAD, "k").ok  # retry with same key succeeds


# ---------- Shopify operations ----------


class Recorder:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        assert request.headers["X-Shopify-Access-Token"] == "shpat_test"
        assert request.url.path == "/admin/api/2026-10/graphql.json"
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body)


def shopify(responses, creds=CREDS):
    rec = Recorder(responses)
    return ShopifyConnector(
        StaticCredentialsProvider(creds), transport=httpx.MockTransport(rec)
    ), rec


EMPTY_FIND = (200, {"data": {"productVariants": {"nodes": []}}})


def test_shopify_publish_creates_draft_with_exact_payload():
    created = (
        200,
        {
            "data": {
                "productSet": {
                    "userErrors": [],
                    "product": {
                        "id": "gid://shopify/Product/77",
                        "variants": {
                            "nodes": [
                                {
                                    "id": "gid://shopify/ProductVariant/88",
                                    "inventoryQuantity": 6,
                                    "inventoryItem": {"id": "gid://shopify/InventoryItem/99"},
                                }
                            ]
                        },
                    },
                }
            }
        },
    )
    conn, rec = shopify([EMPTY_FIND, created])
    result = conn.publish_product(PAYLOAD, "key-1")
    assert result.ok
    assert result.ref.admin_url == "https://demo.myshopify.com/admin/products/77"
    sent = rec.requests[1]["variables"]["input"]
    assert (
        sent["status"] == "DRAFT" and sent["title"] == "Ikigai" and sent["vendor"] == "Hutchinson"
    )
    v = sent["variants"][0]
    assert v["price"] == "450.00" and v["barcode"] == "9781786330895"
    assert v["inventoryItem"] == {"sku": "9781786330895", "tracked": True, "cost": "330.00"}
    assert v["inventoryQuantities"][0] == {
        "locationId": "gid://shopify/Location/1",
        "name": "available",
        "quantity": 6,
    }


def test_shopify_publish_reconciles_existing_sku():
    found = (
        200,
        {
            "data": {
                "productVariants": {
                    "nodes": [
                        {
                            "id": "gid://shopify/ProductVariant/5",
                            "sku": PAYLOAD.sku,
                            "inventoryQuantity": 3,
                            "product": {"id": "gid://shopify/Product/4"},
                            "inventoryItem": {"id": "gid://shopify/InventoryItem/6"},
                        }
                    ]
                }
            }
        },
    )
    conn, rec = shopify([found])
    result = conn.publish_product(PAYLOAD, "key-1")
    assert result.ok and result.ref.product_id == "gid://shopify/Product/4"
    assert len(rec.requests) == 1  # no create call


@pytest.mark.parametrize(
    "status,body,code",
    [
        (401, {}, ErrorCode.AUTH_FAILED),
        (429, {}, ErrorCode.RATE_LIMITED),
        (503, {}, ErrorCode.TRANSIENT),
        (
            200,
            {"errors": [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]},
            ErrorCode.RATE_LIMITED,
        ),
    ],
)
def test_shopify_error_mapping(status, body, code):
    conn, _ = shopify([(status, body)])
    result = conn.publish_product(PAYLOAD, "k")
    assert not result.ok and result.error_code == code


def test_shopify_not_configured_is_honest():
    conn = ShopifyConnector(StaticCredentialsProvider(None))
    result = conn.publish_product(PAYLOAD, "k")
    assert result.error_code == ErrorCode.NOT_CONFIGURED
    assert conn.health_check().ok is False


REF = ExternalRef(
    product_id="gid://shopify/Product/4",
    variant_id="gid://shopify/ProductVariant/5",
    inventory_item_id="gid://shopify/InventoryItem/6",
)


def test_shopify_set_inventory_sends_idempotency_and_compare():
    ok = (
        200,
        {
            "data": {
                "inventorySetQuantities": {
                    "userErrors": [],
                    "inventoryAdjustmentGroup": {"reason": "x"},
                }
            }
        },
    )
    conn, rec = shopify([ok])
    assert conn.set_inventory(REF, 20, 12, "inv-key").ok
    variables = rec.requests[0]["variables"]
    assert variables["key"] == "inv-key"
    assert "@idempotent(key: $key)" in rec.requests[0]["query"]
    q = variables["input"]["quantities"][0]
    assert q == {
        "inventoryItemId": REF.inventory_item_id,
        "locationId": "gid://shopify/Location/1",
        "quantity": 20,
        "changeFromQuantity": 12,
    }


def test_shopify_stale_inventory_is_conflict():
    stale = (
        200,
        {
            "data": {
                "inventorySetQuantities": {
                    "inventoryAdjustmentGroup": None,
                    "userErrors": [
                        {"code": "CHANGE_FROM_QUANTITY_STALE", "message": "stale", "field": None}
                    ],
                }
            }
        },
    )
    conn, _ = shopify([stale])
    assert conn.set_inventory(REF, 20, 12, "k").error_code == ErrorCode.CONFLICT


def test_shopify_update_price():
    ok = (200, {"data": {"productVariantsBulkUpdate": {"userErrors": [], "productVariants": []}}})
    conn, rec = shopify([ok])
    assert conn.update_product(REF, Decimal("399.00"), "k").ok
    assert rec.requests[0]["variables"]["variants"] == [{"id": REF.variant_id, "price": "399.00"}]


def test_shopify_missing_location_blocks_inventory():
    creds = ShopifyCredentials(shop_domain="demo.myshopify.com", access_token="shpat_test")
    conn, _ = shopify([], creds=creds)
    assert conn.set_inventory(REF, 1, None, "k").error_code == ErrorCode.NOT_CONFIGURED
