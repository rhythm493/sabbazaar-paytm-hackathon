# Session log

Keep this file concise. It is an index of consequential work, decisions, verification, and next actions—not a chat transcript. Do not include secrets, private data, or raw chain-of-thought.

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

- Coordinate with Ridam on running `apps/api` (FastAPI) and testing end-to-end integration via the `/v1` proxy in Vite.


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
