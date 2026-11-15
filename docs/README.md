# Documentation index

## Product

- [`product/mvp-scope.md`](product/mvp-scope.md) — prototype boundaries and priorities
- [`product/user-flows-and-acceptance.md`](product/user-flows-and-acceptance.md) — golden flows and testable outcomes
- [`product/demo-script.md`](product/demo-script.md) — deterministic judging flow and fallback plan

## Architecture

- [`architecture/overview.md`](architecture/overview.md) — context, components, principles, and runtime flow
- [`architecture/domain-model.md`](architecture/domain-model.md) — canonical entities and invariants
- [`architecture/agent-workflows.md`](architecture/agent-workflows.md) — bounded graphs and structured actions
- [`architecture/connector-contract.md`](architecture/connector-contract.md) — adapter interface and error semantics
- [`architecture/safety-and-approvals.md`](architecture/safety-and-approvals.md) — policy matrix and audit requirements
- [`architecture/api-and-events.md`](architecture/api-and-events.md) — initial HTTP and event contracts
- [`architecture/deployment-and-observability.md`](architecture/deployment-and-observability.md) — prototype topology and operations

## Plans

- [`plans/implementation-roadmap.md`](plans/implementation-roadmap.md) — six-hour critical path
- [`plans/team-ownership.md`](plans/team-ownership.md) — named ownership and integration cadence
- [`plans/open-decisions-and-risks.md`](plans/open-decisions-and-risks.md) — resolved decisions and delivery risks

## Decision records

- [`adr/0001-modular-monolith.md`](adr/0001-modular-monolith.md)
- [`adr/0002-canonical-commerce-model.md`](adr/0002-canonical-commerce-model.md)
- [`adr/0003-policy-gate-between-agents-and-connectors.md`](adr/0003-policy-gate-between-agents-and-connectors.md)
- [`adr/0004-human-approval-for-risky-actions.md`](adr/0004-human-approval-for-risky-actions.md)
- [`adr/0005-simulated-marketplace-connectors.md`](adr/0005-simulated-marketplace-connectors.md) (superseded)
- [`adr/0006-six-hour-local-shopify-first.md`](adr/0006-six-hour-local-shopify-first.md)

## Operations

- [`operations/local-development.md`](operations/local-development.md) — intended local topology and setup checklist
- [`operations/demo-runbook.md`](operations/demo-runbook.md) — reset, health, rehearsal, and recovery checklist

The original pitch remains in [`../SabBazaar.md`](../SabBazaar.md). If a document conflicts with an accepted ADR, the newer accepted ADR controls and the other document should be corrected.
