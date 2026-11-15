# SabBazaar

**One AI teammate that takes an offline shop online on every marketplace, and runs it there.**

SabBazaar is Team Big Ben's prototype for the Paytm Build for India AI Hackathon, Track 3: Autonomous AI Teammates. It helps a small shop create a catalogue from product photos or bills, publish channel-specific listings, manage orders, and keep inventory synchronized from one merchant experience.

> This repository is currently at the architecture and project-scaffolding stage. Marketplace and Paytm integrations in the hackathon prototype are simulated; no Paytm production data is used.

## MVP demonstration

The first complete vertical slice will show:

1. A merchant uploads product photos or a bill.
2. The Catalogue Builder creates structured product drafts.
3. The merchant reviews and approves the catalogue.
4. SabBazaar publishes through ONDC, Amazon, Meesho, and Google Business simulators.
5. A simulated channel order enters the unified inbox.
6. The inventory ledger changes exactly once and stock is synchronized to every channel.
7. Proposed actions, approvals, connector attempts, and results appear in an audit timeline.

## Architecture

SabBazaar is planned as a **modular monolith plus a background worker**:

- React and TypeScript merchant application
- Python FastAPI control plane
- LangGraph-based bounded agent workflows
- PostgreSQL canonical catalogue, commerce state, audit log, and transactional outbox
- A worker that executes connector jobs
- A common connector contract with four marketplace simulators

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
- [Implementation roadmap](docs/plans/implementation-roadmap.md)
- [Team ownership](docs/plans/team-ownership.md)
- [Open decisions and risks](docs/plans/open-decisions-and-risks.md)
- [Agent instructions](AGENTS.md)

## Team

Team Big Ben: Harsimar, Kedar, and Rythm.

Role assignment is intentionally left open until each member's strengths and availability are confirmed. The three workstreams are AI/agents, merchant experience, and commerce/connectors.

## Project status

- [x] Pitch deck and Markdown source
- [x] Architecture, MVP, delivery, and safety baseline
- [x] Repository boundaries and contribution instructions
- [ ] Working development environment
- [ ] First upload-to-publication vertical slice
- [ ] Multi-channel order and stock synchronization
- [ ] Deployed and rehearsed hackathon demo
