# Session log

Keep this file concise. It is an index of consequential work, decisions, verification, and next actions—not a chat transcript. Do not include secrets, private data, or raw chain-of-thought.

## 2026-11-15 — Bill intake backend (branch `feature/bill-intake-backend`)

### Goal

Backend flow: bill upload -> LLM extraction -> match existing/new books -> owner questions -> preview -> confirm -> canonical stock/catalogue update and channel jobs.

### Decisions

- LangGraph workflow with `interrupt()` for owner questions; graph stops at the preview and confirmation runs in a commerce service (ADR 0003).
- Model layer via LangChain `init_chat_model`, default free Gemini key (ADR 0007).
- Ridam owns OAuth and the ORM/SQLite persistence; this branch ships repository protocols with an in-memory implementation and the Shopify operations adapter.
- Design: `docs/superpowers/specs/2026-11-15-bill-intake-design.md`; plan: `docs/superpowers/plans/2026-11-15-bill-intake-backend.md`.

### Verification

- `uv run pytest`: 59 passed (unit rules, connector contract incl. Shopify GraphQL via mock transport, LangGraph interrupt/resume, API integration). `uv run ruff check .` clean.
- Live smoke on uvicorn with `CHANNEL_MODE=fake`, `MODEL_ENABLED=false`: sample bill -> 4 questions -> preview -> confirm -> 6 simulated channel jobs succeeded, 36 audit events.
- Whole-branch review fixes: preview loaded inside the confirm lock; interrupted confirm resumes idempotently; jobs never stuck in `running`; ambiguous Shopify publish is never auto-retried; no file paths in errors.
- Not verified: live Gemini extraction and live Shopify dev-store calls (no credentials in this session).

### Merge with main (2026-11-15)

- Merged `origin/main` (Ridam's SQLAlchemy/Alembic Shopify publish slice, Kedar's React app) into this branch.
- Bill-intake code moved into the uv workspace packages: `sabbazaar_contracts`, `sabbazaar_commerce` (`intake/`, `audit_log`, in-memory repos), `sabbazaar_connectors` (`shopify_ops/`, `fake`, `registry`), new `sabbazaar_agents`; routes mounted on `apps/api/main.py` via `apps/api/bill_intake`.
- Bill-intake book list is `GET /v1/books` (Ridam's `GET /v1/products` unchanged). Shopify operations reuse the client-credentials token exchange.
- Verified: 60 tests pass; merged API boots; read-only Shopify health check connected to the dev store.
- Known gap: no authentication on any endpoint (local prototype, per MVP scope).

### Next action

Map bill-intake repositories onto Ridam's ORM (needs ISBN, inventory ledger and ingestion tables); wire Ridam's ORM repositories and OAuth credentials provider; run an opt-in live Shopify smoke against the dev store; frontend integration.
## 2026-11-15 — Merchant Web Application (apps/web) scaffold and core flows

### Goal

Implement the complete merchant dashboard for Kedar's workstream, enabling catalogue drafting, review/edit, approval, publication to channels, audit activity tracking, and price threshold configuration.

### Decisions

- Built using React 19, TypeScript 5.8, TailwindCSS 3.4, Vite 6, React Router DOM 7, and Lucide React icons.
- Includes a full offline/demo mode toggle with realistic Indian commerce fixtures (`MOCK_STORE`, `MOCK_PRODUCTS`, `MOCK_ACTIVITY`, `MOCK_LISTINGS`) for zero-dependency non-technical judge evaluation.
- Implemented optimistic and real API paths for `ProductUpload` (dropzone + fixture trigger), `DraftEditor` (missing field warnings, AI evidence display, edit/save, approve), `PublishPanel` (channel selector with Shopify enabled and ONDC/Meesho labeled soon), `PublicationStatus` (real-time pollable listing status with retry), `ActivityTimeline` (event feed with relative timestamps), and `PriceThresholdControl` (slider for ±% AI threshold).
- All API types align with canonical contracts defined in `packages/contracts` and `docs/architecture/api-and-events.md`.

### Files changed

- `apps/web/package.json`
- `apps/web/tsconfig.json`
- `apps/web/vite.config.ts`
- `apps/web/tailwind.config.js`
- `apps/web/postcss.config.js`
- `apps/web/index.html`
- `apps/web/src/index.css`
- `apps/web/src/main.tsx`
- `apps/web/src/App.tsx`
- `apps/web/src/types/contracts.ts`
- `apps/web/src/api/client.ts`
- `apps/web/src/api/mockData.ts`
- `apps/web/src/components/StatusBadge.tsx`
- `apps/web/src/components/Spinner.tsx`
- `apps/web/src/components/Alert.tsx`
- `apps/web/src/components/Header.tsx`
- `apps/web/src/components/ProductUpload.tsx`
- `apps/web/src/components/DraftEditor.tsx`
- `apps/web/src/components/PublishPanel.tsx`
- `apps/web/src/components/PublicationStatus.tsx`
- `apps/web/src/components/ActivityTimeline.tsx`
- `apps/web/src/components/PriceThresholdControl.tsx`
- `apps/web/src/pages/Dashboard.tsx`

### Verification

- Installed dependencies via npm (161 packages, 0 vulnerabilities).
- Verified TypeScript compilation: `npx tsc --noEmit` exited 0 with no errors.
- Verified production build: `npm run build` completed successfully, producing clean static assets under `dist/`.

### Next action

- Wire directly to Ridam's live FastAPI endpoints (`/v1/products`, `/v1/products/{id}/approve`, `/v1/products/{id}/publish`, `/v1/activity`).

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
