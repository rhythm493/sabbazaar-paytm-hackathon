# Marketplace connector contract

## Purpose

Connectors isolate channel protocols and payload formats from SabBazaar's canonical commerce model. The prototype implements simulators behind the same contract intended for future real adapters.

## Initial interface

The exact language-level interface will be finalized during tooling setup, but it should express these operations:

```python
class MarketplaceConnector:
    async def capabilities(self) -> ChannelCapabilities: ...
    async def validate_listing(self, draft: ListingDraft) -> ValidationResult: ...
    async def publish_listing(
        self, draft: ListingDraft, idempotency_key: str
    ) -> ConnectorResult: ...
    async def update_listing(
        self, listing: ListingUpdate, idempotency_key: str
    ) -> ConnectorResult: ...
    async def update_inventory(
        self, update: InventoryUpdate, idempotency_key: str
    ) -> ConnectorResult: ...
    async def update_price(
        self, update: PriceUpdate, idempotency_key: str
    ) -> ConnectorResult: ...
    async def fetch_orders(self, cursor: str | None = None) -> OrderPage: ...
    async def normalize_webhook(self, payload: bytes, headers: dict) -> list[InboundEvent]: ...
    async def get_operation(self, external_operation_id: str) -> ConnectorResult: ...
```

Agent code may consume read-only capability metadata through an application service. It may not obtain connector instances or execute these methods.

## Normalized results

A connector result should contain:

- Internal job and correlation IDs
- External resource/operation ID when available
- Status: success, pending, retryable failure, or terminal failure
- Safe response summary
- Normalized error code and merchant-facing remediation
- Retry-after hint where relevant
- Sanitized raw fixture reference for debugging

## Error categories

| Category | Behavior |
|---|---|
| `AUTHENTICATION` | Terminal until channel account is repaired |
| `VALIDATION` | Terminal; return field-level issues |
| `RATE_LIMITED` | Retry after connector-provided/default delay |
| `TEMPORARY_UNAVAILABLE` | Retry with bounded exponential backoff |
| `CONFLICT` | Re-read/reconcile before retrying |
| `NOT_FOUND` | Terminal or reconcile depending on operation |
| `UNKNOWN` | Limited retries, then merchant-visible failure |

## Idempotency and retries

- The caller supplies a stable idempotency key derived from the approved action and operation target.
- A simulator must return the original result when the same key is replayed.
- A worker crash after a remote success must not duplicate a listing or stock update.
- Retry timing belongs to the worker/job policy, not individual agents.
- Terminal failures retain enough structured context to fix and resubmit as a new action.

## Inbound order contract

Every normalized inbound event includes:

- Unique channel source event ID
- Channel account and external entity ID
- Event type and source timestamp
- Received timestamp
- Schema version
- Normalized payload
- Sanitized raw fixture reference

Processing inserts the source event key and applies domain changes in one transaction. Duplicate events are acknowledged but do not reapply changes.

## Simulator requirements

Each ONDC, Amazon, Meesho, and Google Business simulator must support:

- Predictable happy-path responses
- Configurable latency
- Validation failures
- Rate limiting and temporary failure injection
- Stable idempotency behavior
- Incoming order fixtures where meaningful
- Clear `SIMULATED` labels in UI and logs

One shared connector contract test suite must run against every adapter.
