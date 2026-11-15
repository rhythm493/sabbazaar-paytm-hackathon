# Local development plan

Application tooling has not been initialized yet. This document records the intended topology and the checklist the first implementation change must satisfy; it does not invent commands that do not exist.

## Intended processes

- `web`: React/TypeScript development server
- `api`: FastAPI HTTP process
- `worker`: Python process consuming PostgreSQL outbox jobs
- `db`: PostgreSQL
- `object storage`: local volume initially or an S3-compatible service if required by deployment

## Initialization checklist

- Pin Python and Node versions.
- Choose and document Python and JavaScript package managers.
- Add root commands or a task runner for setup, lint, type-check, test, migration, seed, reset, and run.
- Add database migrations and an isolated test database strategy.
- Keep model and speech providers optional; deterministic fakes must work without API keys.
- Add connector simulators and synthetic fixtures only.
- Add health endpoints and startup dependency checks.
- Update `AGENTS.md`, `CONTRIBUTING.md`, and this document with verified commands.

## Environment configuration

Copy `.env.example` to `.env` only after the code defines the required variables. Never commit `.env` or real credentials. Production-like secrets must be supplied by the deployment platform, not image layers or source files.

## Expected one-command developer outcome

Once initialized, a new contributor should be able to:

1. Install pinned dependencies.
2. Start PostgreSQL and required local services.
3. Apply migrations.
4. Seed the synthetic Meena's Sarees scenario.
5. Start web, API, and worker.
6. Run all offline/default tests.

Exact commands must be tested on a clean checkout before being documented as working.
