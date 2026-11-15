# Implementation roadmap

This is a 10-working-day baseline for three contributors. Re-estimate it immediately after the actual deadline, availability, and role assignment are known.

## Delivery rule

Build one complete vertical slice before filling out layers. Integrate to the shared branch daily after review; avoid three long-lived branches that only meet at the end.

## Phase 0: scope and contracts — Day 1

**Together**

- Freeze the golden demo flow and out-of-scope list.
- Assign named workstream owners.
- Confirm model/speech providers and deployment target.
- Review canonical entities and connector operations.
- Define product draft, proposed action, approval, connector job, and event envelopes.
- Turn unresolved numeric thresholds into explicit configuration/TODO decisions.

**Exit:** each person can build against agreed schemas without inventing incompatible formats.

## Phase 1: foundations — Days 2–3

### AI/agent owner

- Initialize agent package and provider/fake interfaces.
- Implement structured Catalogue Builder extraction against fixtures.
- Add schema-failure and missing-data evaluation cases.

### Merchant application owner

- Initialize React application, navigation, visual tokens, and API client.
- Build catalogue review, approval queue, order list, and activity skeletons.
- Cover phone and desktop layouts.

### Commerce/connectors owner

- Initialize FastAPI, database, migrations, and seed command.
- Implement core entities, connector protocol, outbox, and worker skeleton.
- Add first simulator and contract test harness.

**Exit:** the UI renders seeded products through the real API and database.

## Phase 2: first vertical slice — Days 4–5

Deliver one end-to-end path:

```text
upload fixture
 -> Catalogue Builder draft
 -> merchant correction/approval
 -> publication action/approval
 -> ONDC simulator job
 -> listing and audit result
```

Add integration and one browser-level golden-path test.

**Exit:** one product reaches one simulated channel through all intended internal safety boundaries.

## Phase 3: multi-channel orders and inventory — Days 6–7

- Add remaining channel simulators behind the same contract.
- Add normalized inbound order/event processing.
- Implement append-only inventory ledger and duplicate-event protection.
- Fan out availability updates to active listings.
- Add channel/job status, retry, and reconciliation UI.

**Exit:** a simulated sale on one channel changes stock once and synchronizes every channel.

## Phase 4: safety and secondary flow — Day 8

- Complete policy matrix and server-side approval enforcement.
- Add buyer question routine/escalation cases.
- Add above-threshold price and return/refund demonstrations.
- Add prompt-injection, malformed output, transient connector, and duplicate-order tests.

**Exit:** risky operations cannot execute without exact recorded approval, including through direct API use.

## Phase 5: demo hardening — Days 9–10

- Deploy to the chosen target and document commands.
- Add deterministic seed/reset/health workflows.
- Complete loading, empty, failure, retry, and disconnected states.
- Validate observability and sensitive-data redaction.
- Rehearse the script three times from a reset environment.
- Record a backup video and prepare offline/local fallback.

**Exit:** the complete demo succeeds three consecutive times and its limitations are accurately labelled.

## Integration cadence

- 15-minute daily contract/blocker sync
- One integration window near the middle/end of each day
- Schema changes announced before dependent implementation
- Shared demo rehearsal from Day 5 onward
- Stop adding features 24 hours before presentation; only fix demo blockers

## Definition of project-ready MVP

- Golden path and safety acceptance criteria pass.
- Connector contract suite passes for all simulators.
- Agent fixtures pass without mandatory live API access.
- Fresh setup and demo reset are documented and verified.
- Open limitations are visible in README/demo.
- Architecture documents match implementation.
