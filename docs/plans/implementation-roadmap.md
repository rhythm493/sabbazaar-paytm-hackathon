# Six-hour implementation plan

Assume the clock starts at roughly now and the team works in parallel. This supersedes the original 10-day baseline. Cut scope aggressively; integrate continuously.

## Hour 0:00–0:30 — joint contract freeze

All three people:

- Confirm Shopify dev-store app credentials are available locally, without pasting secrets into chat/source.
- Agree on `Product`, `Approval`/`PublishAction`, `ConnectorJob`, and minimal `AuditEvent`.
- Agree on the UI routes and API endpoints:
  - `POST /v1/catalogue/draft-from-image` (or seeded fixture)
  - `PATCH /v1/products/{id}`
  - `POST /v1/products/{id}/approve`
  - `POST /v1/products/{id}/publish`
  - `GET /v1/activity`
- Agree on environment variables; keep keys in `.env` only.
- Assign DRIs: Harsimar (AI), Kedar (app), Ridam (commerce/connectors).

**Exit:** each stream can build against a typed local contract.

## Hour 0:30–1:30 — foundations

### Harsimar

- Goedel Machines OpenAI-compatible client at `https://api.goedelmachines.com/v1`.
- Structured draft schema and one deterministic product fixture.
- Sarvam speech adapter or a thin recorded/text fallback.
- Return `{ title, description, price_inr?, category, tags, missing_fields, confidence, evidence }`.

### Kedar

- React app shell and API client.
- One dashboard route with upload/select fixture, draft editor, approve/publish buttons, result/activity panels.
- Hardcode no secrets; render states honestly.

### Ridam

- FastAPI + SQLite schema and minimal seed data.
- Shopify client with Admin API product creation.
- Environment config: `SHOPIFY_SHOP_DOMAIN`, `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_API_VERSION`, plus optional `SHOPIFY_LOCATION_ID`.
- `publication` job endpoint with idempotency behavior; run in-process initially if worker setup threatens the demo.

**Exit:** a product draft can be created from the fixture without Shopify.

## Hour 1:30–2:45 — golden path

- Harsimar streams product draft output from image or fallback fixture.
- Kedar renders/edit draft and collects approval.
- Ridam persists approval and publishes to Shopify.
- Add audit entries at `draft_created`, `merchant_approved`, `shopify_publish_requested`, `shopify_published/failed`.

**Exit:** clicking through the UI results in one Shopify product, or a clearly labelled failure state with the exact Shopify error.

## Hour 2:45–3:30 — integration stabilization

- Use one known product fixture and one known clean Shopify-create request.
- Fix CORS, model parsing, currency, `status: active|draft`, and image handling.
- Prefer Shopify product as **draft** first; switch to active only if the demo requires it.
- Show activity timeline from persisted events, not client memory.

**Exit:** golden path succeeds twice in a row locally.

## Hour 3:30–4:30 — secondary proof

Only after two consecutive successes:

1. **Price approval control** in UI with adjustable threshold; above threshold requires approval.
2. **Inventory/orders** if Shopify Admin API availability is confirmed; otherwise show clear future roadmap.
3. **Speech** via Sarvam or recorded command; text remains the fallback.

## Hour 4:30–5:15 — demo hardening

- Seed/reset command or reset instructions.
- Error states and retry button.
- Keep app local-only; document ports and startup commands after they are verified.
- Remove test secrets and confirm `.env` is ignored.
- Capture backup screenshots/video of successful Shopify product creation.
- Update `SESSION_LOG.md`.

## Hour 5:15–6:00 — rehearsal and pitch

- Run demo from a clean reset three times.
- Prepare fallback sequence: fixture draft → approve → cached Shopify success screen/video if network/token fails.
- Keep the story honest: Shopify development store only, other channels future, no Paytm production access.

## Parallel work assignments

| Hour | Harsimar | Kedar | Ridam |
|---|---|---|---|
| 0:00–0:30 | Draft schema | UX wireframe/routes | Shopify auth check |
| 0:30–1:30 | Model adapter | React shell | SQLite/API/Shopify client |
| 1:30–2:45 | Draft generation | Editor/approval UX | Publish + persistence/audit |
| 2:45–3:30 | Fix structured output | Integrate/fix UX | Fix Shopify/CORS/idempotency |
| 3:30–4:30 | Speech/price policy | Threshold slider | Orders/inventory only if safe |
| 4:30–5:15 | Evaluation fixture | Polish/error states | Reset/health/docs |
| 5:15–6:00 | Demo fallback | Rehearsal | Logs/recovery |

## Immediate stop-work rules

- If Shopify auth is not working by hour 1:30, stop expanding the integration, call it a planned real connector, and make the fixture/harness demo while preserving the client code.
- If model/speech is unstable after hour 4:00, use deterministic drafts and text commands.
- Do not rewrite architecture during the sprint.
- Do not add tests that require network at default.
