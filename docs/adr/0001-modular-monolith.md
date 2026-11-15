# ADR 0001: Use a modular monolith and background worker

- Status: Accepted
- Date: 2026-11-15

## Context

Three contributors must deliver and integrate a reliable hackathon demonstration quickly. The product still needs clean boundaries among agent workflows, commerce rules, APIs, and channel adapters.

## Decision

Implement one modular backend codebase exposed by a FastAPI process, plus a worker process built from the same codebase. Use PostgreSQL for canonical state and the transactional outbox. Keep the React application separate at runtime.

## Consequences

- Transactions and local development stay simple.
- Modules can later be extracted if scale or team ownership justifies it.
- Boundary discipline must be enforced in code and tests rather than by network separation.
- One backend failure domain is acceptable for the prototype.
- New infrastructure/services require another ADR.
