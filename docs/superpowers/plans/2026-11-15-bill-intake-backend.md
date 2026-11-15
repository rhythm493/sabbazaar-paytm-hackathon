# Bill intake backend: implementation plan (short form)

> Owner asked for speed: short-form plan, native execution in one session, one whole-branch review at the end.

**Goal:** Bill upload → LLM extraction → match/classify → questions → preview → confirm → canonical apply + channel jobs (Shopify ops + fake), all audited.

**Spec:** `docs/superpowers/specs/2026-11-15-bill-intake-design.md`

**Stack:** Python ≥3.12 (uv), FastAPI, Pydantic v2, LangGraph (+ `langgraph-checkpoint-sqlite`), LangChain `init_chat_model` (+ `langchain-google-genai`), httpx, pytest.

## Global constraints

- Agents (`packages/agents`) never import `connectors`. Connector protocol + channel types live in `contracts`.
- No network in default tests (fake model, fake connector, `httpx.MockTransport` for Shopify).
- Shopify Admin GraphQL `2026-10`: `productSet(synchronous: true)`, `productVariantsBulkUpdate`, `inventorySetQuantities @idempotent(key:)` with `changeFromQuantity`, lookup via `productVariants(query: "sku:...")`. Products created `DRAFT`.
- Prices/MRP are `Decimal` INR; nothing price-like is set without bill or owner provenance.
- No commits unless the owner asks (AGENTS.md rule 7).

## Layout (hatch maps each folder to a top-level package)

| Package | Files |
|---|---|
| `contracts` | `bill.py` (ExtractedLine, BillExtraction), `ingestion.py` (statuses, WorkingLine, Question, Answer, Preview…), `channels.py` (ListingPayload, ExternalRef, ConnectorResult, ErrorCode, ChannelConnector Protocol) |
| `commerce` | `domain.py`, `repositories.py` (Protocols + `Repositories` bundle), `memory.py` (in-memory impl), `audit.py`, `isbn.py`, `intake/normalize.py`, `intake/matching.py`, `intake/requirements.py`, `intake/questions.py`, `intake/preview.py`, `intake/apply.py` |
| `connectors` | `registry.py`, `fake.py`, `shopify/credentials.py`, `shopify/client.py`, `shopify/connector.py` |
| `agents` | `models.py`, `extraction.py`, `prompts.py`, `ingestion_graph.py` |
| `api` (apps/api) | `settings.py`, `container.py`, `main.py`, `errors.py`, `routes/ingestions.py`, `routes/catalog.py`, `routes/dev.py` |

## Tasks

1. **Scaffold** — `pyproject.toml`, `uv sync`, pytest/ruff config; record commands in AGENTS.md/CONTRIBUTING.md.
2. **Contracts** — schemas above.
3. **Commerce rules** — ISBN normalize (10→13, checksum), normalize (merge dup ISBN, invalid ISBN note, Decimal), classify (ISBN → restock; no ISBN + title ratio ≥ 0.9 → uncertain_match; missing title/qty → unreadable; else new), questions (selling price for new, price only if no selling price or MRP changed for restock, confirm_match, missing required per channel rules, unreadable → missing title/quantity with drop allowed), apply answers with validation, preview with hash + per-channel changes. Unit tests on the synthetic fixture.
4. **Connectors** — FakeConnector (idempotent keys, compare-and-set, failure injection) + contract tests; Shopify operations with MockTransport tests (error mapping, payload shape, reconcile-before-create, conflict).
5. **Agents** — `build_chat_model(settings)`, `LLMExtractor` (structured output, bounded retries, image/PDF blocks, untrusted-text prompt), `FixtureExtractor` (labelled fallback), LangGraph graph with `interrupt()` for questions and resume via `Command(resume=answers)`; tests with fake extractor + InMemorySaver.
6. **Apply + API** — ApplyService (approval bound to preview hash/version, ledger with unique source key, books create/update, jobs, run, retry, reject, per-ingestion lock); FastAPI routes per spec; background graph runs; upload validation (png/jpeg/webp/pdf ≤ 10 MB); content-hash dedupe; dev seed (fake mode links fake listings; Shopify mode read-only lookup); integration tests for golden path, dup upload, double confirm, stale version, invalid answers, channel failure + retry, reject, empty bill, Shopify not configured.
7. **Docs** — ADR 0007 (model layer), connector-contract + api docs, `.env.example`, `SESSION_LOG.md`, synthetic bill PNG/PDF generator, final review.

## Review focus

1. Invalid answer values (price "abc", ≤0, quantity 0) → 422, flow stays paused.
2. Answers for unknown question ids or after preview → 422/409.
3. Double/concurrent confirm → exactly one set of ledger entries and jobs.
4. Bill where all lines are dropped → empty preview, confirm completes with no jobs.
5. Shopify credentials missing → jobs fail `not_configured`, status `partially_failed`, never fake success.

## Spec deviations (recorded)

- LLM extraction failure after retries → ingestion `failed` with visible `extraction_failed` error and the upload preserved (owner can re-upload); a manual-entry question is deferred.
- Connector methods are synchronous (httpx sync client); the old contract doc's `async` sketch is updated.
