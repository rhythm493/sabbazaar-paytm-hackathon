# Session log

Keep this file concise. It is an index of consequential work, decisions, verification, and next actions—not a chat transcript. Do not include secrets, private data, or raw chain-of-thought.

## 2026-11-15 — Official Shopify SDK and development products

### Goal

Minimize Shopify integration bug surface by using Shopify's supported Python primitives, then populate the development store through the approval-protected publish flow.

### Decisions
- Use the official `shopifyapp` package for client-credentials exchange and Admin GraphQL requests.
- The SDK expects the shop base name while `.env` keeps the full `.myshopify.com` domain; the connector normalizes it internally.
- Keep `SHOPIFY_ACCESS_TOKEN` as a static fallback; client ID/secret remain preferred for the Dev Dashboard app.
- Keep the fake connector as the default test path; the live development store is separate from CI/tests.

### Verification
- Offline integration test passed after the SDK migration.
- `SHOPIFY_API_VERSION=2026-10` read-only query succeeded.
- Five products were created as Shopify **Drafts** through the recorded approval flow: Kanjivaram Silk Saree, Mysore Silk Dupatta, Brass Diya Set, Organic Turmeric Powder 500g, and Cotton Handloom Napkin Set.
- `publishablePublish` remains deferred; none of these drafts are implied to be Online Store-live.

## 2026-11-15 — Shopify Dev Dashboard authentication

### Goal

Support current Dev Dashboard custom-app authentication without committing credentials.

### Decisions

- `SHOPIFY_CLIENT_ID` and `SHOPIFY_CLIENT_SECRET` are the preferred local credentials; the API exchanges them with Shopify's client credentials grant and caches the short-lived Admin API token in memory.
- `SHOPIFY_ACCESS_TOKEN` remains available as a static/legacy token fallback.
- No token or client secret is tracked in the repository.
- Live Shopify remains opt-in; no product will be published without explicit approval from the merchant and a user-triggered action.

### Verification

- Offline tests must continue to use the fake connector.

## 2026-11-15 — SQLite and Shopify development slice


### Goal

Initialize the narrow local vertical slice from approved product draft to Shopify development-store publication.

### Decisions

- Keep a shared connector package called in-process by FastAPI for the six-hour prototype.
- Use SQLAlchemy 2.0 with Alembic and local SQLite.
- Use synchronous Admin GraphQL `productSet` to create a draft product and one priced variant.
- Require recorded merchant approval before Shopify publication; retries reuse local listings/external IDs.
- Defer inventory, orders, webhooks, and `publishablePublish` until the product golden path is stable.

### Files changed

- Added `sabbazaar_contracts`, `sabbazaar_commerce`, `sabbazaar_connectors`, and the FastAPI entry point.
- Added Alembic migration, seed script, fake-connector integration test, and local SQLite workflow.
- Added responsive React merchant dashboard for draft creation, approval, Shopify publication, result link, and activity timeline.

### Verification

- `uv sync` completed.
- `uv run --env-file .env alembic upgrade head` applied to local `sabbazaar.db`.
- `uv run --env-file .env python scripts/seed_demo.py` seeded one synthetic product.
- `uv run pytest` passed (1 test; offline fake connector).
- `npm install` and `npm run build` passed for `apps/web`.
- API health/products/activity verified locally; live Shopify was not called.

### Next action

Supply local Shopify development-store environment variables, run opt-in live smoke, and verify `productSet` against the development store.


## 2026-11-15 — Scope decisions for the six-hour sprint

### Goal

Incorporate the team decisions and reprioritize documentation for delivery in 6 hours.

### Decisions

- Harsimar owns AI/agents; Kedar owns merchant application; Ridam owns commerce/connectors.
- Vision and general LLM calls use the OpenAI-compatible Goedel Machines endpoint at `https://api.goedelmachines.com/v1`, with model and credentials supplied locally.
- Sarvam AI is used for speech.
- Deployment is local-only.
- Persistence is SQLite.
- Frontend is responsive React web.
- Shopify is the first real marketplace integration, using the team development account.
- Automatic price-change threshold is adjustable by the merchant in the UI.
- Business-model and pilot numbers are deferred.
- ONDC, Amazon, Meesho, and Google integrations are not critical-path for the six-hour prototype.

### Verification

- Documentation-only update; no credentials or live calls were added.

### Next action

Initialize the vertical-slice codebase and connect Shopify with opt-in smoke checks.

## 2026-11-15 — Architecture and repository scaffold

### Goal

Turn the presentation into an implementable plan for a three-person team and create clear repository boundaries.

### Decisions

- Use three ownership tracks: AI/agents, merchant application, and commerce/connectors.
- Use a modular monolith plus a background worker rather than microservices.
- Put policy and approval checks between agents and connectors.
- Use one canonical commerce model.
- Use simulated adapters only where external access is unavailable; Shopify became the first planned real integration on 2026-11-15.

### Files changed

- Added root project, contributor, and agent guidance.
- Added architecture, product, planning, ADR, operations, and module-boundary documentation.
- Added tracked scaffolding for planned apps, packages, and tests.

### Verification

- Documentation links and repository structure checked locally.
- No application code or runtime dependencies were introduced.

### Next action

Resolve the open decisions, initialize development tooling, and build the upload-to-single-channel vertical slice.

## 2026-11-15 — Deck conversion and repository initialization

### Goal

Preserve the SabBazaar presentation as project source material.

### Result

- Converted the 10-page PDF text to `SabBazaar.md`.
- Created the public GitHub repository under `rhythm493`.
