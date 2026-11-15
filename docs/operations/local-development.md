# Local development

Application tooling is initialized. Verified locally on 2026-11-15:

- Python 3.13, `uv`, and Node/npm are available.
- Python dependencies install with `uv sync`.
- Alembic migration applies to local SQLite.
- Default integration test passes without Shopify network access.
- Web production build passes with `npm run build`.

## Intended processes

- `web`: React/TypeScript development server on port 5173
- `api`: FastAPI HTTP process on port 8000
- `db`: local SQLite, no database service
- `worker`: not started for the six-hour Shopify-first build; Shopify jobs run in-process behind persisted job state

## Setup

```bash
cp .env.example .env
uv sync
uv run --env-file .env alembic upgrade head
uv run --env-file .env python scripts/seed_demo.py
```

Keep `.env` local. For a Dev Dashboard custom app, set `SHOPIFY_SHOP_DOMAIN`, `SHOPIFY_CLIENT_ID`, and `SHOPIFY_CLIENT_SECRET`; the backend uses Shopify's client credentials grant to obtain and cache a short-lived Admin API token. A static `SHOPIFY_ACCESS_TOKEN` may be used instead. Never commit credentials.

## Run

Terminal 1:

```bash
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

Terminal 2:

```bash
cd apps/web
npm install
npm run dev
```

Then open `http://localhost:5173`.

## Verify

```bash
uv run pytest
cd apps/web && npm run build
```

The default test suite uses a fake Shopify connector. Live Shopify publication is opt-in through local credentials and is not part of automated tests yet.

## Environment configuration

See `.env.example`. `SHOPIFY_CONNECTOR=shopify` calls Shopify; `SHOPIFY_CONNECTOR=fake` is for deterministic local demos. `DATABASE_URL` defaults to `sqlite:///./sabbazaar.db`.
