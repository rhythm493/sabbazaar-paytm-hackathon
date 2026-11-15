"""Shopify credentials come from Ridam's OAuth/store-connection flow via this protocol.

`EnvCredentialsProvider` is the stand-in until that flow lands. Tokens are never logged.
"""

from __future__ import annotations

import os
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


class EnvCredentialsProvider:
    def get(self) -> ShopifyCredentials | None:
        domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "").strip()
        token = os.getenv("SHOPIFY_ACCESS_TOKEN", "").strip()
        if not domain or not token:
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
