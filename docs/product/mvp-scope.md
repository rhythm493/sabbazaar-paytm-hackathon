# MVP scope

## Six-hour outcome

Demonstrate the narrowest end-to-end path that proves the SabBazaar idea with a real first integration:

1. A merchant uploads a product image or bill.
2. The Catalogue Builder creates a structured draft.
3. The merchant reviews and corrects missing facts.
4. The merchant approves publication.
5. SabBazaar creates the product in the Shopify development store.
6. The UI shows the Shopify URL/result and a complete local audit trail.

Paytm is not integrated for this event. Other marketplaces are not critical-path for the six-hour build.

## Must have in 6 hours

### Merchant experience — Kedar

- Responsive React single-page dashboard
- One seeded store/profile
- Upload or select a product image/fixture
- Product draft review/editor
- Clear missing-field warnings
- Approve/reject controls
- Shopify publication status and result link
- Simple activity timeline
- Manual fallback for catalogue creation

### Intelligence — Harsimar

- OpenAI-compatible vision/general LLM client using `https://api.goedelmachines.com/v1`
- Strict structured product-draft response
- Text fallback when the external model is unavailable
- Sarvam speech input as a thin adapter or canned/pre-recorded path
- Confidence, evidence, and missing-field handling
- No autonomous execution before approval

### Commerce and connectors — Ridam

- FastAPI API incrementally backed by SQLite
- Canonical product/listing/action/audit tables
- Shopify development-store connection via local environment variables
- Product creation against Shopify Admin API
- Basic job status, idempotency key, and audit events
- Synthetic seed data and reset command if time permits
- Opt-in Shopify smoke check; default tests remain offline

## Stretch only after the golden path works

- Shopify inventory publication
- Webhook verification and order ingestion
- Price-change control exposed in the UI
- Buyer-question prototype
- Mock/synthesized secondary channel preview
- Better voice interaction

Each stretch item requires the core demo to remain stable. Do not trade the Shopify vertical slice for breadth.

## Not in six-hour scope

- Paytm production or physical Soundbox integration
- ONDC, Amazon, Meesho, or Google production access
- Real payment, refund, settlement, lending, or delivery flows
- Production authentication, compliance certification, or multi-tenancy
- Native mobile
- General-purpose agents/tools
- Business-model and pilot metrics in the app

These may be shown as future roadmap only if clearly labelled.

## Success criteria

- Repeatable local boot and reset or a documented fallback setup command.
- A product image/fixture produces a schema-valid draft.
- Missing facts do not block publication unless required by Shopify.
- A first publication cannot bypass recorded merchant approval.
- The approved payload determines exactly what is sent to Shopify.
- Shopify credentials never enter source control or logs.
- The demo can succeed with model/speech disabled by using deterministic catalogue fixtures.
- Shopify failure is shown honestly with retry/manual correction where feasible.

## Assumptions

- A Shopify development store and app credentials are available locally.
- The team can install and access a Shopify Admin API app.
- Network access to Goedel Machines, Sarvam, and Shopify is available at demo time.
- Local-only deployment is acceptable.
- No live Paytm data will be used.

## Scope guardrails

If time or API access fails, cut in this order:

1. Live speech; keep text input and canned demo command.
2. Live LLM; keep deterministic draft fixture.
3. Live Shopify product publication only after approval; keep the real connector stub visible but unexecutable.
4. Orders/inventory sync; retain audit and catalogue publication as the proof point.

Never silently replace a live success claim with a fake result in the UI.
