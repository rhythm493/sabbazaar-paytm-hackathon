# Claude project guidance

`AGENTS.md` is the canonical contributor and coding-agent guide. Read it before making changes, followed by the relevant files under `docs/`.

Key reminders:

- Build vertical slices through the modular monolith; do not split the prototype into microservices.
- Agents produce typed proposed actions and never invoke connectors directly.
- Keep the canonical commerce model independent of marketplace payload formats.
- Require approval for risky actions and record an audit event for every state transition.
- Add tests and update documentation with implementation changes.
- Do not claim that simulated Paytm or marketplace integrations are live.
- Append a concise, factual entry to `SESSION_LOG.md` after substantial work; do not record secrets or raw chain-of-thought.

Project commands are not defined yet. Once tooling is initialized, record the authoritative commands in `AGENTS.md` and `CONTRIBUTING.md` rather than guessing them here.
