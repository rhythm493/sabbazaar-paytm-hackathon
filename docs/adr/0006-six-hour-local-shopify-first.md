# ADR 0006: Six-hour local SQLite Shopify-first prototype

- Status: Accepted
- Date: 2026-11-15
- Supersedes: ADR 0001 (database/runtime clarification) and ADR 0005 (simulator-first scope)

## Context

The delivery window is 6 hours. The team has access to a Shopify development account and wants the demo to show one real integration rather than four four-hour-quality simulators. Paytm Soundbox production access is unavailable. The application will run locally.

## Decision

- Persistence uses SQLite.
- Frontend is responsive React web.
- Deployment is local-only.
- Vision and general LLM calls use a Goedel Machines OpenAI-compatible endpoint configured locally.
- Sarvam is used for speech; text/recorded input remains a fallback.
- Shopify is the first real connector and must be attempted from hour 0 through the Admin API.
- Agents still propose typed actions; a deterministic approval gate authorizes connector mutations.
- Orders/inventory and secondary channels are stretch goals after a stable product-publication golden path.

## Consequences

- The demo has one honest external integration and much less integration surface.
- SQLite is simpler and sufficient for local state but does not prove production scale.
- Shopify credentials become a critical local dependency and must never enter source control.
- Paytm remains the pitch narrative and roadmap, not a current integration.
- If Shopify fails, the team may show a clearly labelled recorded proof or failure recovery, not a silent simulated success.
- The original 10-day roadmap and four-simulator scope are deferred.
