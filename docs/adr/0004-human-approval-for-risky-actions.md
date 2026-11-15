# ADR 0004: Require human approval for risky actions

- Status: Accepted
- Date: 2026-11-15

## Context

SabBazaar should automate repetitive work without removing merchant control. Returns, refunds, disputes, legal submissions, first publication, and material price changes can create cost or obligation.

## Decision

Model approval as durable domain state enforced by server-side policy. Bind a decision to the exact proposed action version. Require merchant approval for the initial listing batch and protected actions defined in the safety matrix. Allow routine, reversible actions automatically only when policy explicitly permits them.

## Consequences

- The UI needs a first-class approval inbox and clear impact summary.
- Editing an action invalidates its approval.
- Approval state survives restarts and is auditable.
- The price threshold remains configurable and unresolved until the team decides it.
- Some flows are slower by design.
