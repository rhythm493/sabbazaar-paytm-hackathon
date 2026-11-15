# Team ownership

The system has more than three architectural layers, but three stable workstreams are the right ownership model for Team Big Ben. Assign Harsimar, Kedar, and Rythm to roles after confirming strengths and availability; do not guess names into roles.

## Workstream A: AI and agent lead

Owns:

- LangGraph workflow state and transitions
- Model-provider abstraction and deterministic fake
- Vision/document extraction orchestration
- Catalogue Builder, Listing Specialist, Order Desk, Stock Keeper, and supervisor
- Structured outputs, confidence, evidence, and missing-field behavior
- Prompt/tool safety and agent evaluations

Collaborates with commerce owner on action schemas/policy and app owner on understandable agent states.

## Workstream B: merchant application lead

Owns:

- React application and design system
- Store/onboarding and channel-status experience
- Upload and browser voice/Soundbox simulation
- Catalogue review/editor
- Approval queue
- Orders, inventory status, and activity timeline
- Responsive behavior, accessibility, and demo presentation

Collaborates with commerce owner on API contracts and agent owner on evidence/confidence display. Do not expose raw chain-of-thought.

## Workstream C: commerce and connector lead

Owns:

- FastAPI composition and request validation
- PostgreSQL schema, migrations, and seed/reset
- Canonical catalogue, order, and inventory services
- Proposed actions, policy gate, approvals, and audit events
- Transactional outbox, worker, retries, and idempotency
- Connector interface and four simulators
- Deployment foundation and health checks

Collaborates with agent owner on typed proposed actions and app owner on generated/shared contracts.

## Cross-cutting DRI matrix

| Area | Directly responsible | Reviewers |
|---|---|---|
| Domain/API/event contracts | Commerce lead | Both leads |
| Agent guardrails/evaluations | AI lead | Commerce lead |
| UX/demo story | Application lead | Both leads |
| Connector contract tests | Commerce lead | AI lead |
| End-to-end golden path | All; application lead coordinates | All |
| Deployment/runbook | Commerce lead | Application lead |
| Synthetic demo data | AI + application leads | Commerce lead |
| Presentation/rehearsal | All | All |

## Team working agreement

- One DRI per task; reviewers do not share ambiguous ownership.
- Shared schema changes require quick review from affected owners.
- Integrate daily and run the golden path after material merges.
- Raise blockers at the daily sync, not at the end of a phase.
- Protect the frozen demo before adding optional features.
- Update `SESSION_LOG.md` with consequential decisions and handoffs.

## Assignment table

Fill this before implementation begins:

| Member | Primary workstream | Secondary/reviewer role | Availability |
|---|---|---|---|
| Harsimar | TBD | TBD | TBD |
| Kedar | TBD | TBD | TBD |
| Rythm | TBD | TBD | TBD |
