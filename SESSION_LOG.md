# Session log

Keep this file concise. It is an index of consequential work, decisions, verification, and next actions—not a chat transcript. Do not include secrets, private data, or raw chain-of-thought.

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
