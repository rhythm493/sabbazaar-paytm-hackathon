# ADR 0003: Place a policy gate between agents and connectors

- Status: Accepted
- Date: 2026-11-15

## Context

Model output is probabilistic and may be incomplete or invalid. Marketplace mutations can affect merchant money, reputation, legal status, and inventory. Direct agent-to-connector tool access would bypass consistent authorization and auditing.

## Decision

Agents can emit typed `ProposedAction` objects only. Deterministic application policy evaluates them. Approved actions produce durable connector jobs through the commerce/publication service; workers alone invoke mutation methods on connectors.

Read-only channel capability metadata may be exposed to agent workflows through an application service.

## Consequences

- Safety is enforceable independently of prompts and UI.
- Every mutation receives a stable idempotency key and audit lifecycle.
- The implementation includes more explicit action/job states.
- Agent workflows remain testable with no connector credentials.
- Any direct connector import from `packages/agents` violates the architecture.
