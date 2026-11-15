# AGENTS.md

This file is the canonical instruction set for coding agents and contributors working in this repository.

## Start here

Read, in order:

1. `README.md`
2. `docs/product/mvp-scope.md`
3. `docs/architecture/overview.md`
4. The architecture document for the area being changed
5. Relevant ADRs under `docs/adr/`

## Product objective

Build a reliable hackathon prototype in which a small merchant can create a canonical catalogue, approve publication, publish products to Shopify, receive normalized orders when configured, and keep stock changes explicit and audited.

Optimize for a deterministic end-to-end demonstration, not production breadth.

## Non-negotiable architecture rules

1. **Agents do not call marketplace connectors directly.** Agents emit typed proposed actions. The policy and approval layer turns approved actions into durable connector jobs.
2. **The canonical commerce model is the source of truth.** Marketplace listings are channel projections, not independent products.
3. **Every externally visible mutation is idempotent and audited.** Include an idempotency key, actor, timestamps, input summary, result, and error status.
4. **Risky actions require merchant approval.** Returns, refunds, disputes, legal/KYC submissions, and price changes outside the configured threshold cannot run automatically.
5. **Do not invent missing merchant facts.** Low-confidence or incomplete AI output must become a question or approval task.
6. **Keep the prototype honest.** Clearly label simulated connectors and test data. Never imply access to live Paytm data or marketplace certification.
7. **Preserve module boundaries.** Share contracts through `packages/contracts`; do not create circular imports between apps and packages.

## Repository boundaries

- `apps/web`: merchant UI, browser voice capture/simulation, API client, and presentation state
- `apps/api`: HTTP transport, authentication context, request validation, and service composition
- `apps/worker`: durable job acquisition, connector execution, retries, and result persistence
- `packages/agents`: agent graphs, model adapters, prompts, structured output, and evaluation cases
- `packages/commerce`: domain entities, business policies, catalogue, orders, inventory ledger, approvals, and application services
- `packages/connectors`: connector protocol, normalized errors/results, Shopify, and explicitly labelled development-channel fixtures
- `packages/contracts`: API/event schemas that cross boundaries
- `tests`: cross-module tests and shared fixtures

Business rules belong in domain/application services, not React components, HTTP route handlers, prompts, or connector adapters.

## Planned technology

- Python 3.12+
- FastAPI and Pydantic
- LangGraph behind a provider-neutral model interface
- SQLite for local development and the six-hour demo
- React and TypeScript responsive web
- SQLite-backed job state; a separate worker is preferred, with an in-process runner allowed for the six-hour prototype if it preserves idempotency and visible status

Do not introduce another datastore, queue, framework, or service without documenting the reason in an ADR.

## Development workflow

1. Work in the smallest vertical slice that produces observable value.
2. In the six-hour sprint, change only contracts required by the critical path and record deferred contracts explicitly; do not design speculative abstractions.
3. Add tests with the change.
4. Update affected architecture/product documentation in the same change.
5. Record consequential architecture choices as ADRs.
6. Add a concise entry to `SESSION_LOG.md` for substantial changes.
7. Do not commit or push unless the user explicitly requests it.

Do not delete or overwrite unfamiliar work. Inspect it first and ask when ownership or intent is unclear.

## Test expectations

The eventual project commands will be recorded here as tooling is initialized. Until then, follow these required test levels:

- Domain and policy changes: unit tests
- Connector changes: shared connector contract suite
- Agent changes: schema validation and fixed evaluation fixtures
- API changes: request/response integration tests
- Golden-path changes: end-to-end test or deterministic demo verification
- Event consumers: duplicate-delivery/idempotency test

Never make external LLM, speech, Shopify, or marketplace calls in the default test suite. Use fixtures/fakes, with opt-in live tests clearly marked. Shopify development-store smoke checks are opt-in and must not modify unrelated store data.

## Security and data handling

- Never commit credentials, access tokens, production payloads, customer data, or private prompts.
- Keep secrets in environment variables and document names in `.env.example` only.
- Treat uploaded images, bills, PAN/GST/bank details, and chat content as sensitive.
- Log identifiers and safe summaries rather than complete sensitive payloads.
- Do not expose raw chain-of-thought. Store concise action rationales and evidence references instead.
- Validate files, webhook signatures where applicable, and all model-generated structures.

## Definition of done

A change is complete when:

- Acceptance criteria are met.
- Relevant tests pass.
- Failures are observable and recoverable.
- External mutations are idempotent and audited.
- Documentation and session log are current.
- The change does not weaken safety rules or prototype honesty.
