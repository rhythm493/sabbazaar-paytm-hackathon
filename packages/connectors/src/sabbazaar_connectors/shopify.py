from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Protocol

from shopify_app import ShopifyApp, admin_graphql_request_async

from sabbazaar_contracts import PublishResult


class ChannelConnector(Protocol):
    async def publish_product(self, product: dict, idempotency_key: str) -> PublishResult: ...


class FakeShopifyConnector:
    async def publish_product(self, product: dict, idempotency_key: str) -> PublishResult:
        return PublishResult(
            ok=True,
            external_product_id=f"gid://shopify/Product/fake-{idempotency_key}",
            external_variant_id=f"gid://shopify/ProductVariant/fake-{idempotency_key}",
            inventory_item_id="gid://shopify/InventoryItem/fake",
            admin_url="https://demo.myshopify.com/admin/products/fake",
        )


class ShopifyConnector:
    def __init__(self) -> None:
        self.shop_name = self._normalize_shop(os.getenv("SHOPIFY_SHOP_DOMAIN", os.getenv("SHOPIFY_SHOP_NAME", "")))
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "").strip()
        self.client_id = os.getenv("SHOPIFY_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("SHOPIFY_CLIENT_SECRET", "").strip()
        self.api_version = os.getenv("SHOPIFY_API_VERSION", "2026-10").strip()
        self._cached_token: str | None = None
        self._token_expires_at = 0.0
        self._app = ShopifyApp(self.client_id, self.client_secret) if self.client_id and self.client_secret else None

        if not self.shop_name:
            raise ValueError("SHOPIFY_SHOP_DOMAIN or SHOPIFY_SHOP_NAME is required")
        if self.access_token:
            return
        if not self._app:
            raise ValueError("Set SHOPIFY_ACCESS_TOKEN or SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET")

    @staticmethod
    def _normalize_shop(value: str) -> str:
        shop = value.strip().lower().removesuffix(".myshopify.com")
        if shop and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", shop):
            raise ValueError("SHOPIFY_SHOP_DOMAIN must look like your-store.myshopify.com")
        return shop

    @property
    def shop_domain(self) -> str:
        return f"{self.shop_name}.myshopify.com"

    async def _access_token(self) -> str | None:
        if self.access_token:
            return self.access_token
        if self._cached_token and self._token_expires_at > time.time() + 60:
            return self._cached_token
        if not self._app:
            return None

        result = await self._app.exchange_using_client_credentials_async(shop=self.shop_name)
        if not result.ok or not result.access_token:
            return None

        self._cached_token = result.access_token.token
        expires = result.access_token.expires
        if expires:
            try:
                self._token_expires_at = datetime.fromisoformat(expires.replace("Z", "+00:00")).timestamp()
            except ValueError:
                self._token_expires_at = time.time() + 3600
        else:
            self._token_expires_at = time.time() + 3600
        return self._cached_token

    async def publish_product(self, product: dict, idempotency_key: str) -> PublishResult:
        query = """
        mutation SabBazaarCreateDraftProduct($input: ProductSetInput!, $identifier: ProductSetIdentifiers, $synchronous: Boolean!) {
          productSet(input: $input, identifier: $identifier, synchronous: $synchronous) {
            product {
              id
              variants(first: 1) {
                nodes { id sku title inventoryItem { id } }
              }
            }
            userErrors { field message code }
          }
        }
        """
        variant = product["variants"][0]
        variables = {
            "synchronous": True,
            "identifier": {"handle": product["handle"]},
            "input": {
                "title": product["title"],
                "descriptionHtml": product.get("description") or "",
                "vendor": product.get("vendor") or "SabBazaar",
                "productType": product.get("product_type") or "General",
                "tags": product.get("tags") or [],
                "handle": product["handle"],
                "status": "DRAFT",
                "productOptions": [
                    {"name": "Title", "position": 1, "values": [{"name": "Default Title"}]},
                ],
                "variants": [
                    {
                        "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                        "sku": variant["sku"],
                        "price": str(variant["price_inr"]),
                    }
                ],
            },
        }

        token = await self._access_token()
        if not token:
            return PublishResult(
                ok=False,
                error_code="shopify_auth_failed",
                error_message="Could not obtain a Shopify access token from the configured credentials.",
            )

        result = await admin_graphql_request_async(
            query=query,
            shop=self.shop_name,
            access_token=token,
            api_version=self.api_version,
            invalid_token_response=None,
            variables=variables,
        )
        if not result.ok:
            code = "shopify_auth_failed" if result.log.code in {"unauthorized", "http_error_401", "http_error_403"} else result.log.code
            return PublishResult(ok=False, error_code=code, error_message=(result.log.detail or "Shopify request failed")[:1000])

        data = result.data.get("productSet") if result.data else None
        if not data:
            return PublishResult(ok=False, error_code="shopify_bad_response", error_message="Shopify returned an unexpected response.")
        user_errors = data.get("userErrors") or []
        if user_errors:
            message = "; ".join(f"{'.'.join(str(x) for x in e.get('field', []))}: {e.get('message')}" for e in user_errors)
            return PublishResult(ok=False, error_code="shopify_user_error", error_message=message[:1000])

        shopify_product = data.get("product") or {}
        variants = (shopify_product.get("variants") or {}).get("nodes") or [{}]
        variant_node = variants[0]
        external_product_id = shopify_product.get("id")
        numeric_id = external_product_id.rsplit("/", 1)[-1] if external_product_id else None
        return PublishResult(
            ok=True,
            external_product_id=external_product_id,
            external_variant_id=variant_node.get("id"),
            inventory_item_id=(variant_node.get("inventoryItem") or {}).get("id"),
            admin_url=f"https://{self.shop_domain}/admin/products/{numeric_id}" if numeric_id else None,
        )
