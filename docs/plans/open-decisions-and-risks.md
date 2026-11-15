# Open decisions and risk register

## Decisions needed before implementation

| ID | Decision | Why it matters | Owner | Due |
|---|---|---|---|---|
| D1 | Hackathon deadline and available person-days | Determines whether 10-day baseline must be compressed | Team | Before Phase 0 ends |
| D2 | Named workstream assignment | Enables accountable parallel work | Team | Before Phase 0 ends |
| D3 | Model and vision provider/credits | Determines adapter, latency, limits, and fallback fixtures | AI lead | Before Phase 1 |
| D4 | Speech provider and required languages | Determines whether Sarvam/live speech is practical | AI + app leads | Before Phase 1 |
| D5 | Public deployment target/credits | Determines deployment files and object storage | Commerce lead | Before Phase 3 |
| D6 | Responsive web versus native mobile | Native app would materially increase scope; default recommendation is responsive web | Product/team | Before Phase 1 |
| D7 | Required real integration, if any | Deck currently promises simulated connectors; a live requirement changes risk | Team/organizers | Immediately |
| D8 | Automatic price-change threshold | Needed for policy demo and deck placeholder | Product/team | Before Phase 4 |
| D9 | Pilot/business numbers | Needed for final pitch, not core software | Team | Before final deck |
| D10 | Repository license | Public visibility does not grant reuse rights without a license | Repository owner | Before external contributions |

Recommended defaults if no contrary requirement appears: responsive web, all connectors simulated, provider-neutral model adapter with deterministic fake, and no numeric price threshold claim until agreed.

## Risk register

| Risk | Probability | Impact | Mitigation | Trigger/contingency |
|---|---|---|---|---|
| Real connector access/certification consumes schedule | High | High | Simulator-first shared contract | Keep real adapter off critical demo path |
| Live model fails or produces unstable result | Medium | High | Strict schemas, fixtures, cached/fake fallback | Switch transparently to deterministic mode |
| Three workstreams build incompatible contracts | Medium | High | Day-1 schema freeze and daily integration | Stop feature work and repair one contract source |
| Duplicate event decrements stock twice | Medium | High | Source event uniqueness and ledger transaction | Replay test is a release gate |
| Agent invents product facts | Medium | High | Evidence/confidence/missing fields and approval | Escalate or use manual correction |
| Dashboard becomes a generic admin interface | Medium | Medium | Design around Meena's golden path | Demo review by Day 3 |
| Infrastructure consumes hackathon time | Medium | Medium | Modular monolith, PostgreSQL outbox, minimal services | Defer optional infra/monitoring |
| Sensitive data leaks into logs | Low/Medium | High | Synthetic data, structured safe summaries, redaction review | Block demo/release until corrected |
| Voice fails in noisy venue | High | Medium | Prepared text input and deterministic audio fixture | Use text path during demo |
| Deployment/network fails | Medium | High | Local runnable topology and backup recording | Run locally or show recording transparently |
| Scope grows into lending/refunds/delivery | Medium | High | Explicit out-of-scope list and feature freeze | Move requests to roadmap |
| Numeric pitch claims remain placeholders | Medium | Medium | Assign D8/D9 owner and evidence check | Avoid unsupported numbers in final deck |

## Review cadence

Review decisions daily during Phase 0/1 and the risk table at each phase exit. Add newly discovered risks with an owner and a concrete mitigation; do not use this as an unowned concern list.
