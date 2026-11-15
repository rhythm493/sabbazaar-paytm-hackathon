# Agent workflows

## Design approach

SabBazaar uses specialist, bounded workflows coordinated by a small supervisor. The implementation may use LangGraph if setup is quick; otherwise a small explicit state machine is preferable. It provides explicit states, transitions, retries, and human-interrupt points. The model is not allowed to run an open-ended loop or invoke a marketplace adapter.

All workflow outputs are validated structured objects. Invalid output is retried within a small limit and then escalated visibly.

## Shared output requirements

Each proposed action must include:

- `action_type` and schema version
- Merchant/store and target entity identifiers
- Typed payload
- Source/evidence references
- Confidence per AI-derived field where relevant
- Missing required fields
- Safe, concise rationale suitable for an audit view
- Requested execution time
- Idempotency seed/correlation ID

Do not persist or display raw chain-of-thought.

## Catalogue Builder

**Input:** uploaded rack/product images, bill image/text, merchant notes, language, and optional sample sales data.

**Steps:**

1. Validate file metadata and create evidence references.
2. Extract observable products and bill lines.
3. Normalize names, attributes, units, and categories.
4. Suggest title, description, tags, and price only from available evidence or clearly labelled policy.
5. Detect ambiguity, duplicates, and missing channel requirements.
6. Emit product drafts for merchant review.

**Must not:** invent brand, material, certification, stock, tax status, or price.

## Listing Specialist

**Input:** approved canonical Shopify destination product/variant.

**Steps:**

1. Validate a minimal Shopify draft-product payload.
2. Transform canonical fields to each channel's listing draft.
3. Report unsupported or missing attributes.
4. Propose one publication action for Shopify.
5. Route first-batch publication through merchant approval.

The policy and publication services—not the agent—enqueue connector jobs.

## Order Desk

**Input:** normalized order, buyer question, relevant approved catalogue data, and store policies.

**Steps:**

1. Classify the request.
2. Retrieve only relevant verified product/order facts.
3. Draft a grounded response with evidence references.
4. Auto-answer only routine questions allowed by policy.
5. Escalate returns, refunds, disputes, legal claims, harassment, and uncertain answers.

## Stock Keeper

**Input:** confirmed normalized order/inventory event and current ledger-derived availability.

**Steps:**

1. Check source event idempotency.
2. Propose or apply the deterministic inventory ledger transition.
3. Determine affected listings.
4. Propose synchronized quantities or a pause when stock is uncertain.
5. Expose reconciliation differences to the merchant.

Stock arithmetic is deterministic domain code, not model reasoning.

## Supervisor

The supervisor classifies a merchant request and starts one known workflow. It may ask for clarification but cannot create new tool capabilities or bypass policy.

## Evaluation baseline

Maintain fixed fixtures for:

- Clear product image to valid draft
- Bill with incomplete prices
- Multiple similar sarees and duplicate detection
- Unsupported product claims
- Prompt injection text inside an uploaded document
- Routine buyer question with a grounded answer
- Return request that must escalate
- Duplicate order event that cannot double-decrement inventory
- Malformed model output and retry exhaustion

Default tests use deterministic model fakes. Live-model evaluations are opt-in and their provider/model/version must be recorded.
