# Local deployment and observability

## Runtime

The event demo is local-only:

- Web: React development server
- API: FastAPI process
- Optional worker: Python process, or in-process job runner for the six-hour sprint
- Database: SQLite file, preferably outside committed source or ignored by Git
- External: Goedel Machines, Sarvam, and Shopify development store

No production deployment, object store, queue, or Kubernetes manifest is part of the MVP.

## Local configuration

Copy `.env.example` locally and populate values through environment tooling. `.env` must remain untracked. Never paste Shopify, model, or Sarvam credentials into tickets, docs, source, screenshots, or chat.

Required variables once implementation exists:

- `APP_ENV`
- `DATABASE_URL` or `SQLITE_PATH`
- `MODEL_BASE_URL=https://api.goedelmachines.com/v1`
- `MODEL_NAME`
- `MODEL_API_KEY`
- `SARVAM_API_KEY`
- `SHOPIFY_SHOP_DOMAIN`
- `SHOPIFY_ACCESS_TOKEN`
- `SHOPIFY_API_VERSION`
- optional feature/demo flags such as `MODEL_ENABLED`, `SPEECH_ENABLED`, `RUN_LIVE_SHOPIFY_SMOKE`

Do not document actual dev-account values in this repository, even if the token is temporary.

## Health checks

- API liveness/readiness: process and SQLite database available
- Shopify: authenticated read-only check, never a write in health
- Model/speech: reported optional dependencies with fallback status
- Demo controls: reset and fixture availability

Health output can show whether each dependency is configured; it must not reveal values.

## Minimal observability

Write JSON or structured logs with:

- `correlation_id`
- `store_id` / `product_id` / `action_id`
- `operation`
- `result`
- safe failure code
- duration

Do not log uploaded image contents, full buyer messages, access tokens, full model prompts, bank/KYC data, or raw chain-of-thought.

For the six-hour demo, an activity endpoint backed by SQLite is enough. Metrics stacks are out of scope.

## Failure policy

- Model unavailable: switch to deterministic catalogue fixture.
- Speech unavailable/noisy: use prepared text/recorded command.
- Shopify auth/validation unavailable: show blocked/error result and use disclosed recorded proof; do not claim a new product was published.
- SQLite lock/error: stop writes, preserve evidence, restart seed/reset.
- Any failed approval/persistence means no Shopify mutation.
