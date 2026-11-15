"""Shopify operations: lookup, create, price update, inventory. Credentials via provider (OAuth later)."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import httpx

from sabbazaar_connectors.shopify_ops.client import ShopifyError, ShopifyGraphQLClient
from sabbazaar_connectors.shopify_ops.credentials import ShopifyCredentialsProvider
from sabbazaar_contracts.channels import (
    ConnectorHealth,
    ConnectorResult,
    ErrorCode,
    ExternalRef,
    ListingPayload,
)

SHOP_QUERY = "query { shop { name myshopifyDomain } }"

FIND_BY_SKU = """
query FindBySku($q: String!) {
  productVariants(first: 1, query: $q) {
    nodes { id sku inventoryQuantity product { id } inventoryItem { id } }
  }
}
"""

PRODUCT_SET = """
mutation CreateProduct($input: ProductSetInput!) {
  productSet(synchronous: true, input: $input) {
    product {
      id
      variants(first: 1) { nodes { id inventoryQuantity inventoryItem { id } } }
    }
    userErrors { field message code }
  }
}
"""

VARIANT_PRICE = """
mutation UpdatePrice($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price }
    userErrors { field message code }
  }
}
"""

SET_INVENTORY = """
mutation SetInventory($input: InventorySetQuantitiesInput!, $key: String!) {
  inventorySetQuantities(input: $input) @idempotent(key: $key) {
    inventoryAdjustmentGroup { reason }
    userErrors { field message code }
  }
}
"""


def _numeric(gid: str) -> str:
    return gid.rsplit("/", 1)[-1]


def _sku_query(sku: str) -> str:
    return 'sku:"' + sku.replace("\\", "").replace('"', "") + '"'


class ShopifyConnector:
    channel = "shopify"
    simulated = False

    def __init__(
        self,
        credentials: ShopifyCredentialsProvider,
        transport: httpx.BaseTransport | None = None,
        client_factory: Callable[..., ShopifyGraphQLClient] = ShopifyGraphQLClient,
    ) -> None:
        self._credentials = credentials
        self._transport = transport
        self._factory = client_factory

    def _client(self) -> ShopifyGraphQLClient:
        creds = self._credentials.get()
        if creds is None:
            raise ShopifyError(ErrorCode.NOT_CONFIGURED, "Shopify store is not connected")
        return self._factory(creds, transport=self._transport)

    def _admin_url(self, client: ShopifyGraphQLClient, product_gid: str) -> str:
        return f"https://{client.creds.shop_domain}/admin/products/{_numeric(product_gid)}"

    def health_check(self) -> ConnectorHealth:
        try:
            data = self._client().execute(SHOP_QUERY)
            return ConnectorHealth(
                channel=self.channel, ok=True, message=f"Connected to {data['shop']['name']}"
            )
        except ShopifyError as exc:
            return ConnectorHealth(channel=self.channel, ok=False, message=exc.message)

    def _find(self, client: ShopifyGraphQLClient, sku: str) -> ExternalRef | None:
        nodes = client.execute(FIND_BY_SKU, {"q": _sku_query(sku)})["productVariants"]["nodes"]
        node = next((n for n in nodes if n.get("sku") == sku), None)
        if not node:
            return None
        return ExternalRef(
            product_id=node["product"]["id"],
            variant_id=node["id"],
            inventory_item_id=node["inventoryItem"]["id"],
            quantity=node.get("inventoryQuantity"),
            admin_url=self._admin_url(client, node["product"]["id"]),
        )

    def find_by_sku(self, sku: str) -> ExternalRef | None:
        try:
            return self._find(self._client(), sku)
        except ShopifyError:
            return None

    @staticmethod
    def _user_error(errors: list[dict]) -> ConnectorResult | None:
        if not errors:
            return None
        first = errors[0]
        code = ErrorCode.VALIDATION_FAILED
        if first.get("code") in ("CHANGE_FROM_QUANTITY_STALE", "COMPARE_QUANTITY_STALE"):
            code = ErrorCode.CONFLICT
        elif first.get("code") == "IDEMPOTENCY_CONCURRENT_REQUEST":
            code = ErrorCode.TRANSIENT
        return ConnectorResult.fail(code, str(first.get("message", "Shopify rejected the change")))

    def publish_product(self, payload: ListingPayload, idempotency_key: str) -> ConnectorResult:
        try:
            client = self._client()
            existing = self._find(client, payload.sku)  # reconcile before create: no duplicates
            if existing:
                return ConnectorResult(ok=True, ref=existing, quantity=existing.quantity)
            location = client.creds.location_id
            if not location:
                return ConnectorResult.fail(
                    ErrorCode.NOT_CONFIGURED, "SHOPIFY_LOCATION_ID is required to stock products"
                )
            variant: dict = {
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "price": str(payload.price),
                "inventoryItem": {"sku": payload.sku, "tracked": True},
                "inventoryQuantities": [
                    {"locationId": location, "name": "available", "quantity": payload.quantity}
                ],
            }
            if payload.isbn:
                variant["barcode"] = payload.isbn
            if payload.unit_cost is not None:
                variant["inventoryItem"]["cost"] = str(payload.unit_cost)
            product: dict = {
                "title": payload.title,
                "productType": payload.product_type,
                "status": payload.status.upper(),
                "tags": ["sabbazaar"],
                "productOptions": [{"name": "Title", "values": [{"name": "Default Title"}]}],
                "variants": [variant],
            }
            if payload.publisher:
                product["vendor"] = payload.publisher
            if payload.author:
                product["metafields"] = [
                    {
                        "namespace": "custom",
                        "key": "author",
                        "type": "single_line_text_field",
                        "value": payload.author,
                    }
                ]
            data = client.execute(PRODUCT_SET, {"input": product})["productSet"]
            if err := self._user_error(data.get("userErrors") or []):
                return err
            prod = data["product"]
            v = prod["variants"]["nodes"][0]
            ref = ExternalRef(
                product_id=prod["id"],
                variant_id=v["id"],
                inventory_item_id=v["inventoryItem"]["id"],
                quantity=v.get("inventoryQuantity", payload.quantity),
                admin_url=self._admin_url(client, prod["id"]),
            )
            return ConnectorResult(ok=True, ref=ref, quantity=ref.quantity)
        except ShopifyError as exc:
            return ConnectorResult.fail(exc.code, exc.message)

    def update_product(
        self, ref: ExternalRef, price: Decimal, idempotency_key: str
    ) -> ConnectorResult:
        try:
            data = self._client().execute(
                VARIANT_PRICE,
                {
                    "productId": ref.product_id,
                    "variants": [{"id": ref.variant_id, "price": str(price)}],
                },
            )["productVariantsBulkUpdate"]
            if err := self._user_error(data.get("userErrors") or []):
                return err
            return ConnectorResult(ok=True, ref=ref)
        except ShopifyError as exc:
            return ConnectorResult.fail(exc.code, exc.message)

    def set_inventory(
        self,
        ref: ExternalRef,
        quantity: int,
        expected_current: int | None,
        idempotency_key: str,
    ) -> ConnectorResult:
        try:
            client = self._client()
            location = client.creds.location_id
            if not location:
                return ConnectorResult.fail(
                    ErrorCode.NOT_CONFIGURED, "SHOPIFY_LOCATION_ID is required for inventory sync"
                )
            data = client.execute(
                SET_INVENTORY,
                {
                    "key": idempotency_key,
                    "input": {
                        "name": "available",
                        "reason": "received",
                        "referenceDocumentUri": f"sabbazaar://inventory/{idempotency_key}",
                        "quantities": [
                            {
                                "inventoryItemId": ref.inventory_item_id,
                                "locationId": location,
                                "quantity": quantity,
                                "changeFromQuantity": expected_current,
                            }
                        ],
                    },
                },
            )["inventorySetQuantities"]
            if err := self._user_error(data.get("userErrors") or []):
                return err
            return ConnectorResult(ok=True, ref=ref, quantity=quantity)
        except ShopifyError as exc:
            return ConnectorResult.fail(exc.code, exc.message)
