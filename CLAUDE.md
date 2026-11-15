# Claude project guidance

`AGENTS.md` is the canonical contributor and coding-agent guide. Read it before making changes, followed by the relevant files under `docs/`.

Key reminders:

- Build the six-hour Shopify vertical slice through the modular monolith; avoid speculative microservices or abstractions.
- Agents produce typed proposed actions and never invoke connectors directly.
- Keep the canonical commerce model independent of marketplace payload formats.
- Require approval for risky actions and record an audit event for every state transition.
- Add tests and update documentation with implementation changes.
- Do not claim Paytm or non-Shopify marketplace integrations are live. Shopify is the only planned real integration for the event.
- Append a concise, factual entry to `SESSION_LOG.md` after substantial work; do not record secrets or raw chain-of-thought.

Project commands are not defined yet. Once tooling is initialized, record the authoritative commands in `AGENTS.md` and `CONTRIBUTING.md` rather than guessing them here.
