# Worker application

Planned background worker entry point.

Claims durable SQLite-backed jobs, invokes approved connector operations, applies bounded retry policy, and persists normalized results/audit transitions. It must be safe under duplicate delivery and process crashes. For the six-hour sprint, an in-process implementation is acceptable only if publication remains approved, idempotent, and visible in activity.

Implementation starts in Phase 1 of `docs/plans/implementation-roadmap.md`.
