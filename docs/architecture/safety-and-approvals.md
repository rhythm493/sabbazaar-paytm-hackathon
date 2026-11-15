# Safety, policy, and approvals

## Principle

SabBazaar automates routine, reversible work while keeping the merchant in control of financial, legal, reputational, or ambiguous actions. Approval is enforced server-side; hiding or disabling a UI button is not a safety control.

## Initial action policy

| Action | Default decision | Notes |
|---|---|---|
| Create catalogue draft | Automatic | Draft only; retain evidence/confidence |
| Publish first listing batch | Merchant approval | Approval is per exact action version |
| Answer routine factual question | Automatic | Only from verified catalogue/order data |
| Answer uncertain or policy-sensitive question | Merchant approval | Include proposed answer and evidence |
| Apply confirmed order to inventory | Automatic | Deterministic and idempotent |
| Synchronize confirmed stock | Automatic | Pause instead if stock is uncertain |
| Change price within configured threshold | Configurable | Threshold remains an open product decision |
| Change price outside threshold | Merchant approval | Show old/new amount and percentage |
| Accept return or issue refund | Merchant only | Prototype may simulate state, not money movement |
| Resolve dispute | Merchant only | Agent may summarize and prepare context |
| Submit PAN/GST/bank/legal data | Merchant only | Sensitive data and attestation |
| Post review/testimonial | Prohibited | No fake reviews or undisclosed claims |

## Policy evaluation output

Every proposed action is evaluated into one of:

- `ALLOW_AUTOMATICALLY`
- `REQUIRE_APPROVAL`
- `REQUIRE_MORE_INFORMATION`
- `DENY`

The result includes policy rule/version, rationale safe for display, missing information, and expiration when applicable. Policies are deterministic code/configuration; the LLM may describe context but does not make the final authorization decision.

## Approval requirements

- Bind approval to a hash/version of the proposed action payload.
- Show material effects, target channels, evidence, and expected cost where known.
- Editing an approved payload invalidates the approval.
- Record approving actor and timestamp.
- Allow rejection with an optional reason.
- Expire stale approvals and prevent replay.
- Provide undo only when the downstream operation is genuinely reversible; otherwise provide a compensating action.

## Audit requirements

Record an immutable audit event for:

- Agent workflow started/completed/failed
- Proposed action created or superseded
- Policy decision
- Approval, rejection, expiration, or cancellation
- Connector job queued, attempted, retried, succeeded, or failed
- Listing/order/inventory state transition
- Manual override or correction

Audit records contain actor type/ID, store, correlation ID, event type, safe summary, timestamps, entity references, and previous/new state where safe. They must not contain credentials, complete bank/KYC payloads, raw chain-of-thought, or unnecessarily complete uploaded documents.

## AI safety controls

- Validate model output against strict schemas and business rules.
- Treat uploaded document text and external buyer messages as untrusted content, not instructions.
- Retrieve only merchant-scoped records.
- Ground buyer responses in approved catalogue/order facts.
- Surface confidence and missing facts.
- Bound retries, tool access, token usage, and workflow duration.
- Use deterministic fallbacks for the demo.
- Log provider/model/version and safe usage metrics, not sensitive prompts by default.

## Failure behavior

- If policy cannot decide safely, require approval.
- If stock is inconsistent, pause the listing and create a reconciliation task.
- If a connector state is unknown after timeout, reconcile before retrying a create operation.
- If an agent fails, preserve merchant input and allow manual catalogue entry.
- If external services are unavailable during the demo, use clearly labelled deterministic simulation.
