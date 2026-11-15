"""Minimal Shopify Admin GraphQL client with safe error mapping."""

from __future__ import annotations

from typing import Any

import httpx

from connectors.shopify.credentials import ShopifyCredentials
from contracts.channels import ErrorCode


class ShopifyError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ShopifyGraphQLClient:
    def __init__(
        self,
        creds: ShopifyCredentials,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.creds = creds
        self._http = httpx.Client(
            base_url=f"https://{creds.shop_domain}/admin/api/{creds.api_version}",
            headers={"X-Shopify-Access-Token": creds.access_token},
            transport=transport,
            timeout=timeout,
        )

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            resp = self._http.post(
                "/graphql.json", json={"query": query, "variables": variables or {}}
            )
        except httpx.TimeoutException as exc:
            raise ShopifyError(ErrorCode.UNKNOWN, "Shopify did not respond in time") from exc
        except httpx.HTTPError as exc:
            raise ShopifyError(ErrorCode.TRANSIENT, "Could not reach Shopify") from exc
        if resp.status_code in (401, 403):
            raise ShopifyError(ErrorCode.AUTH_FAILED, "Shopify rejected the access token")
        if resp.status_code == 429:
            raise ShopifyError(ErrorCode.RATE_LIMITED, "Shopify rate limit reached")
        if resp.status_code >= 500:
            raise ShopifyError(ErrorCode.TRANSIENT, f"Shopify error {resp.status_code}")
        if resp.status_code >= 400:
            raise ShopifyError(ErrorCode.VALIDATION_FAILED, f"Shopify returned {resp.status_code}")
        body = resp.json()
        errors = body.get("errors")
        if errors:
            codes = {(e.get("extensions") or {}).get("code") for e in errors}
            if "THROTTLED" in codes:
                raise ShopifyError(ErrorCode.RATE_LIMITED, "Shopify rate limit reached")
            if "ACCESS_DENIED" in codes:
                raise ShopifyError(ErrorCode.AUTH_FAILED, "Shopify app lacks a required scope")
            raise ShopifyError(ErrorCode.VALIDATION_FAILED, str(errors[0].get("message", "error")))
        return body.get("data") or {}
