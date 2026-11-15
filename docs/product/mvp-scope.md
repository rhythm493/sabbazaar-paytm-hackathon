# MVP scope

## Product outcome

Demonstrate that one bounded AI teammate can help a small shop create a catalogue, publish it across multiple simulated marketplaces, receive an order, and safely keep stock synchronized—with the merchant retaining control of consequential actions.

## Primary persona

An owner-operated Indian retail shop with many physical products, limited time, one phone, and little appetite for learning multiple marketplace dashboards. The demo persona is Meena, a saree-shop owner in Pune.

## Must have

### Merchant experience

- Seeded/single-merchant onboarding and store profile
- Product/rack image or bill upload
- Browser voice/text request or Soundbox-style simulator
- AI-created product drafts with confidence/missing fields
- Manual review, correction, and approval
- Channel selection and first-publication approval
- Unified listing status, orders, approvals, and activity timeline
- Visible `SIMULATED` labelling for external channels

### Intelligence

- Catalogue Builder structured workflow
- Listing Specialist channel transformations
- Order Desk routine factual question path plus escalation path
- Stock Keeper triggered by confirmed normalized order
- Deterministic policy gate and typed proposed actions
- Fake/cached model fallback for a repeatable demo

### Commerce and connectors

- Canonical product, variant, price, listing, order, and inventory models
- Append-only inventory ledger and duplicate-event protection
- Durable job/outbox and retry behavior
- Shared connector contract
- ONDC, Amazon, Meesho, and Google Business simulators
- Audit trail from agent proposal through connector result

## Golden path

1. Upload evidence.
2. Generate catalogue drafts.
3. Correct and approve the draft.
4. Propose and approve publication.
5. Publish to channel simulators.
6. Inject one simulated order.
7. Normalize it and adjust inventory once.
8. Synchronize remaining quantity to all active listings.
9. Show the full activity trail.

## Should have, after the golden path is stable

- Hindi voice/text input and response
- Buyer question answer with evidence
- Price change inside/outside threshold demonstration
- Connector failure injection and retry UI
- Inventory uncertainty causing listing pause
- Basic dashboard impact metrics

## Not in the hackathon MVP

- Live Paytm data or physical Soundbox control
- Real marketplace certification or production credentials
- Real payment, settlement, refund, or lending movement
- Automated legal/KYC submission
- Production-grade authentication, tenant isolation, or compliance certification
- Native mobile applications
- Delivery partner orchestration
- Broad product-category perfection
- General-purpose autonomous browsing or arbitrary tool use

Roadmap items may appear as clearly disabled or “coming next” UI, but must not compete with the golden path.

## MVP success criteria

- The seeded demo can be reset and completed three consecutive times.
- A first batch cannot publish without recorded approval.
- A duplicate channel order cannot decrement stock twice.
- Remaining stock reaches all active simulated channels.
- A connector failure is visible, retryable when transient, and audited.
- Missing catalogue facts are requested rather than fabricated.
- A return/refund request is escalated instead of auto-executed.
- No live Paytm or marketplace behavior is implied.

## Open scope inputs

The deadline, team role assignment, model/speech providers, deployment target, mobile requirement, price threshold, business-model numbers, and pilot targets remain unresolved. See `docs/plans/open-decisions-and-risks.md`.
