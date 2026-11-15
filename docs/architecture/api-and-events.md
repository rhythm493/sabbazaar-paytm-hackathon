# Initial API and event contracts

This document establishes resource boundaries, not a frozen OpenAPI specification. Implementation must define schemas once under `packages/contracts` and generate or share clients where practical.

## HTTP resources

All endpoints are versioned under `/v1` and scoped to the authenticated/seeded merchant.

### Stores and channels

- `GET /v1/store`
- `PATCH /v1/store`
- `GET /v1/channels`
- `POST /v1/channels/{channel}/simulate/connect`

### Ingestion and catalogue

- `POST /v1/ingestions` — upload metadata and create an ingestion job
- `GET /v1/ingestions/{id}` — status, evidence, errors, and resulting drafts
- `GET /v1/products`
- `POST /v1/products` — manual fallback
- `GET /v1/products/{id}`
- `PATCH /v1/products/{id}` — merchant correction with version check
- `POST /v1/products/{id}/approve`

### Agent runs and actions

- `POST /v1/agent-runs` — start a known workflow
- `GET /v1/agent-runs/{id}`
- `GET /v1/actions?status=awaiting_approval`
- `GET /v1/actions/{id}`
- `POST /v1/actions/{id}/approve`
- `POST /v1/actions/{id}/reject`
- `POST /v1/actions/{id}/cancel`

### Publication and listings

- `POST /v1/publications` — propose publication for selected products/channels
- `GET /v1/listings`
- `GET /v1/listings/{id}`
- `POST /v1/listings/{id}/retry` — creates a new authorized action/job where safe
- `POST /v1/listings/{id}/pause`

### Orders and inventory

- `GET /v1/orders`
- `GET /v1/orders/{id}`
- `GET /v1/inventory`
- `POST /v1/inventory/adjustments` — manual adjustment with audit reason
- `POST /v1/simulators/{channel}/orders` — demo-only inbound order fixture

### Activity and health

- `GET /v1/activity`
- `GET /health/live`
- `GET /health/ready`

## Concurrency and idempotency

- Mutable resources expose a version and reject stale writes.
- Command endpoints accept `Idempotency-Key`.
- Duplicate requests return the original operation/resource rather than repeating side effects.
- Long-running operations return `202 Accepted` with a resource that can be polled.
- Errors use a stable machine code plus a safe merchant-facing message and field issues.

## Event envelope

Internal domain/outbox events use a versioned envelope:

```json
{
  "event_id": "uuid",
  "event_type": "listing.publish.requested.v1",
  "occurred_at": "ISO-8601 timestamp",
  "merchant_id": "uuid",
  "store_id": "uuid",
  "correlation_id": "uuid",
  "causation_id": "uuid-or-null",
  "aggregate_type": "listing",
  "aggregate_id": "uuid",
  "aggregate_version": 3,
  "payload": {}
}
```

## Initial event catalogue

- `ingestion.requested.v1`
- `ingestion.completed.v1`
- `catalogue.draft.created.v1`
- `product.approved.v1`
- `action.proposed.v1`
- `action.approved.v1`
- `action.rejected.v1`
- `listing.publish.requested.v1`
- `listing.published.v1`
- `listing.failed.v1`
- `channel.order.received.v1`
- `order.normalized.v1`
- `inventory.changed.v1`
- `inventory.sync.requested.v1`
- `inventory.sync.failed.v1`

Event consumers must tolerate additional fields and reject unsupported major/schema event versions safely. Once emitted, an event meaning is not changed in place.

## Demo-only surfaces

Simulator endpoints and failure-injection controls must be unavailable or separately protected outside demo/development mode. The UI must label their outputs as simulated.
