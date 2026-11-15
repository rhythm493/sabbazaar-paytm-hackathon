# Worker application

Planned background worker entry point.

Claims durable PostgreSQL outbox jobs, invokes approved connector operations, applies bounded retry policy, and persists normalized results/audit transitions. It must be safe under duplicate delivery and process crashes.

Implementation starts in Phase 1 of `docs/plans/implementation-roadmap.md`.
