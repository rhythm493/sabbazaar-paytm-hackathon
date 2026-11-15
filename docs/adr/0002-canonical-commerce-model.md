# ADR 0002: Use a canonical commerce model

- Status: Accepted
- Date: 2026-11-15

## Context

Shopify and future channels represent products, listings, orders, and errors differently. Allowing each integration to define internal state would make synchronization and the merchant experience inconsistent.

## Decision

Keep merchant-owned products, variants, prices, inventory ledger, and normalized orders in a channel-neutral canonical model. Represent each marketplace entry as a `Listing` projection and translate only at connector boundaries.

## Consequences

- The dashboard and agent workflows operate on one stable model.
- Channel-specific fields remain possible in a typed extension/mapping area.
- Connectors need explicit mapping and validation logic.
- Unsupported or missing fields must be surfaced rather than forced into the canonical core.
- Connector contract tests become essential.
