# Demo script

Target an 8–10 minute demonstration. Keep one minute of buffer and avoid typing long data live.

## Pre-demo checklist

- Deploy/launch the known commit and run migrations.
- Reset to the deterministic Meena's Sarees seed.
- Verify API, optional worker, SQLite, model or fallback, Sarvam/text fallback, and Shopify development-store health.
- Confirm every connector is marked `SIMULATED`.
- Preload approved synthetic images/bill fixtures.
- Keep the backup recording and screenshots available.

## Story

### 1. Problem and starting state — 45 seconds

Introduce Meena: 400 sarees, one phone, regular customers moving online, and separate forms for every marketplace. Show an empty/new store workspace rather than explaining architecture first.

### 2. Snap to catalogue — 2 minutes

- Upload a rack/product image or bill.
- Give a short Hindi/English voice or text instruction.
- Show Catalogue Builder progress.
- Open generated drafts and highlight evidence, confidence, and a deliberately missing field.
- Correct one field and approve the products.

Message: AI accelerates routine work without inventing facts or taking control away.

### 3. One approval, Shopify publication — 2 minutes

- Show the Shopify draft-product payload.
- Show channel-specific transformed previews and one validation difference.
- Approve the publication action.
- Show Shopify returning an external product ID and URL/status.

Message: one canonical catalogue is translated into each marketplace format.

### 4. One order, synchronized stock — 2 minutes

- If implemented, show a Shopify order in the unified inbox; otherwise clearly show orders/inventory as the roadmap after publication.
- Show it in the unified inbox.
- Show one inventory ledger movement.
- Show updated availability reach every channel.
- Optionally replay the order event and show that stock does not decrement again.

Message: SabBazaar runs the shop after onboarding; it is not only a listing generator.

### 5. Safety and control — 1 minute

- Open the activity timeline from AI proposal to connector result.
- Trigger an above-threshold price change or return request.
- Show that it waits for the merchant rather than executing automatically.

Message: routine work is autonomous; costly or sensitive decisions remain human-controlled.

### 6. Close — 45 seconds

Reinforce why SabBazaar belongs with Paytm: merchant relationship, counter presence, existing transaction context, and open-marketplace reach. Clearly state what is simulated and the path to real connectors.

## Failure fallback

| Failure | Fallback |
|---|---|
| Live model unavailable | Switch to deterministic cached model fixture |
| Speech unavailable/noisy venue | Use the prepared text command |
| Shopify job delayed/failed | Show the persisted failure, Retry where safe, and use the disclosed recorded proof only as fallback |
| Deployment unavailable | Run the local packaged topology |
| Upload/vision failure | Open a pre-seeded draft and explain preserved evidence |

Do not hide a real failure as a success. Use it to demonstrate recovery, or switch transparently to the labelled fallback.
