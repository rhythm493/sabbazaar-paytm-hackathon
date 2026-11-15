# SabBazaar

**One AI teammate that takes an offline shop online on every marketplace, and runs it there.**

SabBazaar is Team Big Ben's prototype for the Paytm Build for India AI Hackathon, Track 3: Autonomous AI Teammates. It helps a small shop create a catalogue from product photos or bills, publish channel-specific listings, manage orders, and keep inventory synchronized from one merchant experience.

> This repository is currently at the architecture and project-scaffolding stage. The first real external integration is Shopify through the team's development account. Paytm and other marketplaces are deferred or explicitly labelled simulations; no Paytm production data is used.

## MVP demonstration

The first complete vertical slice will show:

1. A merchant uploads product photos or a bill.
2. The Catalogue Builder creates structured product drafts.
3. The merchant reviews and approves the catalogue.
4. SabBazaar publishes to Shopify through the real development-store connector.
5. A Shopify order enters the unified inbox when the configured app and webhook flow are available.
6. The inventory ledger changes exactly once and stock is synchronized to every channel.
7. Proposed actions, approvals, connector attempts, and results appear in an audit timeline.

## Architecture

SabBazaar is planned as a **modular monolith plus a background worker**:

- React and TypeScript merchant application
- Python FastAPI control plane
- LangGraph-based bounded agent workflows
- SQLite local canonical catalogue, commerce state, audit log, and job state
- A worker that executes connector jobs
- A shared connector contract, with Shopify as the first real adapter

Agents never call marketplace adapters directly. They propose structured actions; the policy layer validates and, where required, asks the merchant to approve them before the worker executes a connector command.

See [Architecture overview](docs/architecture/overview.md) for the system diagram and boundaries.

## Repository map

```text
apps/
  web/                 React merchant dashboard and voice simulator
  api/                 FastAPI control plane
  worker/              Durable connector job execution
packages/
  agents/              LangGraph workflows, prompts, tools, and evaluations
  commerce/            Canonical catalogue, orders, inventory, and policies
  connectors/          Connector interface and channel adapters
  contracts/           Shared API and event schemas
docs/
  architecture/        System design and contracts
  product/             MVP scope, flows, and demo script
  plans/               Roadmap, ownership, decisions, and risks
  adr/                 Architecture decision records
  operations/          Development and demo operations
tests/                  Unit, contract, integration, end-to-end, and agent evaluations
```

Directories contain boundary documents now and will receive implementation code as each vertical slice begins.

## Documentation

- [Original presentation converted to Markdown](SabBazaar.md)
- [Documentation index](docs/README.md)
- [MVP scope](docs/product/mvp-scope.md)
- [User flows and acceptance criteria](docs/product/user-flows-and-acceptance.md)
- [Six-hour implementation plan](docs/plans/implementation-roadmap.md)
- [Team ownership](docs/plans/team-ownership.md)
- [Open decisions and risks](docs/plans/open-decisions-and-risks.md)
- [Agent instructions](AGENTS.md)

## Team

Team Big Ben: Harsimar, Kedar, and Ridam.

- Harsimar — AI and agents
- Kedar — merchant application
- Ridam — commerce and connectors

Work must integrate continuously because the delivery window is 6 hours.

## Project status

- [x] Pitch deck and Markdown source
- [x] Architecture, MVP, delivery, and safety baseline
- [x] Repository boundaries and contribution instructions
- [x] Working local API/web environment
- [ ] Six-hour vertical slice: upload, catalogue draft, approval, Shopify publication, activity trail
- [ ] Deployed and rehearsed hackathon demo

## Local quickstart

```bash
cp .env.example .env
uv sync
uv run --env-file .env alembic upgrade head
uv run --env-file .env python scripts/seed_demo.py
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

In another terminal:

```bash
cd apps/web
npm install
npm run dev
```

Then open `http://localhost:5173`. For a Dev Dashboard custom app, leave `SHOPIFY_ACCESS_TOKEN` blank and set `SHOPIFY_CLIENT_ID`/`SHOPIFY_CLIENT_SECRET`; the API exchanges them for a short-lived Admin API token automatically. See [Local development](docs/operations/local-development.md) for verification commands.
