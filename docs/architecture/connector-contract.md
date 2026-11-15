# Connector contract

## Six-hour constraint

Only Shopify is required to be real. The abstraction should be thin and should not delay integration. Do not spend time generalizing for ONDC, Amazon, Meesho, or Google during the event.

## Minimal protocol

Implemented in `packages/contracts/channels.py` (synchronous; adapters in `packages/connectors`):

```python
class ChannelConnector(Protocol):
    channel: str
    simulated: bool

    def health_check(self) -> ConnectorHealth: ...
    def find_by_sku(self, sku: str) -> ExternalRef | None: ...  # read-only
    def publish_product(self, payload: ListingPayload, idempotency_key: str) -> ConnectorResult: ...
    def update_product(
        self, ref: ExternalRef, price: Decimal, idempotency_key: str
    ) -> ConnectorResult: ...
    def set_inventory(
        self, ref: ExternalRef, quantity: int, expected_current: int | None, idempotency_key: str
    ) -> ConnectorResult: ...  # compare-and-set
```

Errors are normalized to `auth_failed`, `validation_failed`, `rate_limited`, `transient`, `conflict`, `not_configured`, `unknown`. `publish_product` looks the SKU up first and returns the existing product instead of creating a duplicate. `set_inventory` sends the canonical ledger quantity with Shopify `changeFromQuantity` and `@idempotent(key:)`, so a stock change made directly in Shopify surfaces as `conflict` instead of being overwritten.

Ownership: Ridam builds the Shopify OAuth/store-connection flow, which supplies credentials through `ShopifyCredentialsProvider`; the env-var provider is the interim implementation. `FakeConnector` is the labelled simulated channel used by tests and `CHANNEL_MODE=fake`.

If inventory/orders remain in scope, extend only with the methods required by the implemented slice. Do not add placeholder methods that are never tested.

## Shopify connector behavior

Configuration comes from local environment variables, never source:

- `SHOPIFY_SHOP_DOMAIN`, for example `your-store.myshopify.com`
- `SHOPIFY_ACCESS_TOKEN`
- `SHOPIFY_API_VERSION`
- optional `SHOPIFY_LOCATION_ID` for inventory

The connector must:

1. Validate configuration and report a readable blocked/error state.
2. Create a product with the exact approved normalized payload.
3. Default new products to `status=draft` unless the team explicitly decides otherwise.
4. Set tags/vendor/product type and description as supported by the selected Admin API version.
5. Respect an idempotency key or prevent obvious duplicates on retry; at minimum, persist `external_product_id` and do not blindly create on repeated approval.
6. Return the external product ID and admin/storefront URL when available.
7. Map authentication, validation, rate-limit, and transient failures to safe codes.

## Approval boundary

Connector methods are callable only from the publication application service after a recorded approval. Kedar's UI button requests the action; it does not call Shopify directly.

## Default tests

No default test may call Shopify. Tests use a fake connector. A development-store smoke check may be added as:

```text
RUN_LIVE_SHOPIFY_SMOKE=1 pytest tests/live/test_shopify_smoke.py
```

The live check must either create a clearly labelled draft product in the development store or perform a read-only shop query, depending on permissions. It must never delete or overwrite unrelated products on repeat runs.

## Future channels

The original proposed connectors remain roadmap work. Their presence in the pitch does not authorize six-hour implementation. Add one connector at a time only after Shopify is demonstrably stable.
