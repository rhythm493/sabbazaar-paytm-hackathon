# Contributing

## Before starting

1. Read `AGENTS.md` and the relevant architecture documents.
2. Confirm the issue belongs to the MVP in `docs/product/mvp-scope.md`.
3. Identify the owning workstream in `docs/plans/team-ownership.md`.
4. Agree on shared API/event schemas before parallel implementation begins.

## Change guidelines

- Prefer a small end-to-end slice over isolated layers that cannot be demonstrated.
- Use feature branches and focused pull requests once team development starts.
- Keep commits cohesive and use imperative commit subjects.
- Include tests, documentation, migrations, and fixtures required by the change.
- Do not include secrets or real merchant data.

## Pull request checklist

- [ ] Scope and acceptance criteria are linked or described.
- [ ] Architecture boundaries in `AGENTS.md` are respected.
- [ ] Tests cover success, failure, and duplicate-event behavior where relevant.
- [ ] UI states include loading, empty, error, and approval-required behavior.
- [ ] External mutations are idempotent and audited.
- [ ] Docs and `SESSION_LOG.md` are updated.
- [ ] Simulated behavior is clearly labelled.

The exact install, lint, test, migration, and run commands will be added after project tooling is initialized.
