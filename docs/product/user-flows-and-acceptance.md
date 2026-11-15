# User flows and acceptance criteria

## Flow 1: create a catalogue from evidence

### Steps

1. Merchant uploads supported product photos or a bill.
2. The system validates the files and starts a Catalogue Builder run.
3. The UI shows progress without blocking navigation.
4. Product drafts display extracted fields, evidence, confidence, and missing information.
5. Merchant edits and approves selected products.

### Acceptance criteria

- Invalid type/size is rejected with an actionable message.
- Model output is schema-validated before becoming a draft.
- Uncertain fields are highlighted; missing facts are not invented.
- Failed AI extraction preserves uploads and offers retry/manual entry.
- Merchant corrections are audited and supersede AI suggestions.

## Flow 2: publish across channels

### Steps

1. Merchant selects approved products and target channels.
2. Listing Specialist produces channel-specific drafts and validation issues.
3. System creates exact, versioned proposed actions.
4. Merchant approves the first batch.
5. Worker publishes through adapters and the UI updates per-channel status.

### Acceptance criteria

- Drafts show missing channel requirements before approval.
- Agent code cannot create a connector job without the policy/application service.
- Approval is invalidated if the listing payload changes.
- Repeated submission with the same idempotency key does not create duplicate listings.
- Each channel independently shows queued, publishing, live, or failed state.
- All simulated results are visibly labelled.

## Flow 3: receive order and synchronize stock

### Steps

1. Demo controller injects an order into a channel simulator.
2. Connector normalizes the event.
3. Commerce service persists the order and inventory ledger entry atomically.
4. Stock Keeper identifies every active listing for the variant.
5. Worker synchronizes the derived available quantity.

### Acceptance criteria

- The normalized order retains its external channel/order IDs.
- Processing the source event twice produces one order and one stock decrement.
- Inventory arithmetic is deterministic domain code.
- Every active channel receives the same derived available quantity.
- Failed synchronization is visible and can retry without another decrement.
- Uncertain/negative stock pauses listings and asks for reconciliation.

## Flow 4: answer a buyer question

### Steps

1. A simulated buyer asks a product/order question.
2. Order Desk retrieves verified relevant facts.
3. It drafts an answer with evidence.
4. Policy sends a routine answer automatically or requests merchant approval.

### Acceptance criteria

- Answer contains no unsupported claims.
- Prompt-like buyer text cannot alter system/tool rules.
- Uncertain, refund, return, dispute, or legal questions escalate.
- Sent or approved answer and its evidence are audited.

## Flow 5: approve a risky price change

### Steps

1. Agent or merchant proposes a price change.
2. Policy compares old/new prices and configured threshold.
3. Above-threshold changes create approval tasks.
4. Approved changes become channel jobs.

### Acceptance criteria

- UI shows old price, new price, absolute and percentage difference, targets, and rationale.
- The threshold is configuration, not prompt text.
- Rejection creates no connector job.
- Approval applies only to the displayed action version.

## Cross-flow UX requirements

- Every asynchronous operation has loading, success, empty, failure, and retry states.
- The merchant can always see whether work is draft, awaiting approval, queued, live, paused, or failed.
- User-facing text avoids technical connector/LLM jargon where possible.
- Responsive web supports a phone-sized viewport; native mobile is not required unless the open decision changes.
