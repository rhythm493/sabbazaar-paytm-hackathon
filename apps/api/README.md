# API application

Planned FastAPI control-plane entry point.

Owns HTTP transport, merchant context, validation, application-service composition, health endpoints, and OpenAPI exposure. Domain rules belong in `packages/commerce`; agent workflows in `packages/agents`; channel mapping in `packages/connectors`.

Implementation starts in Phase 1 of `docs/plans/implementation-roadmap.md`.
