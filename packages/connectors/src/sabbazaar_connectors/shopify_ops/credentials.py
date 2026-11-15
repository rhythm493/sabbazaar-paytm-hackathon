"""Shopify credentials for bill-intake operations. Tokens are never logged.

`EnvCredentialsProvider` uses a static token or the same client-credentials exchange as the
publish connector (`sabbazaar_connectors.shopify`).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

DEFAULT_API_VERSION = "2026-10"


@dataclass(frozen=True)
class ShopifyCredentials:
    shop_domain: str
    access_token: str = field(repr=False)
    api_version: str = DEFAULT_API_VERSION
    location_id: str | None = None


class ShopifyCredentialsProvider(Protocol):
    def get(self) -> ShopifyCredentials | None: ...


TokenSource = Callable[[], str | None]


def client_credentials_token_source() -> TokenSource | None:
    """Reuse the publish connector's client-credentials exchange (cached short-lived token)."""
    if not (os.getenv("SHOPIFY_CLIENT_ID", "").strip() and os.getenv("SHOPIFY_CLIENT_SECRET", "").strip()):
        return None
    from sabbazaar_connectors.shopify import ShopifyConnector as PublishConnector

    try:
        publisher = PublishConnector()
    except ValueError:
        return None

    def token() -> str | None:
        try:
            return asyncio.run(publisher._access_token())
        except Exception:  # network/auth failure surfaces as "not connected", never as a crash
            return None

    return token


class EnvCredentialsProvider:
    """Static `SHOPIFY_ACCESS_TOKEN`, or client-credentials exchange via `SHOPIFY_CLIENT_ID/SECRET`.

    Call `get()` from worker threads (FastAPI sync handlers), not from inside a running event loop.
    """

    def __init__(self, token_source: TokenSource | None = None) -> None:
        self._token_source = token_source
        self._resolved = token_source is not None

    def _token(self) -> str | None:
        static = os.getenv("SHOPIFY_ACCESS_TOKEN", "").strip()
        if static:
            return static
        if not self._resolved:
            self._token_source = client_credentials_token_source()
            self._resolved = True
        return self._token_source() if self._token_source else None

    def get(self) -> ShopifyCredentials | None:
        domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "").strip()
        if not domain:
            return None
        if "." not in domain:
            domain = f"{domain}.myshopify.com"
        token = self._token()
        if not token:
            return None
        location = os.getenv("SHOPIFY_LOCATION_ID", "").strip() or None
        if location and not location.startswith("gid://"):
            location = f"gid://shopify/Location/{location}"
        return ShopifyCredentials(
            shop_domain=domain,
            access_token=token,
            api_version=os.getenv("SHOPIFY_API_VERSION", "").strip() or DEFAULT_API_VERSION,
            location_id=location,
        )


class StaticCredentialsProvider:
    def __init__(self, creds: ShopifyCredentials | None) -> None:
        self._creds = creds

    def get(self) -> ShopifyCredentials | None:
        return self._creds
