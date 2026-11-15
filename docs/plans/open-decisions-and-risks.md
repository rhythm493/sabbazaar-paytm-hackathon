# Decision log and risk register

Original open decisions are now resolved as of 2026-11-15. Remaining risks are delivery risks for the six-hour sprint.

## Resolved decisions

| ID | Decision | Status |
|---|---|---|
| D1 | Delivery window is **6 hours** | Resolved |
| D2 | Harsimar = AI/agents; Kedar = merchant app; Ridam = commerce/connectors | Resolved |
| D3 | Vision/general LLM uses OpenAI-compatible endpoint `https://api.goedelmachines.com/v1` | Resolved |
| D4 | Sarvam AI is used for speech | Resolved |
| D5 | Local-only deployment; SQLite for persistence | Resolved |
| D6 | Responsive React web application | Resolved |
| D7 | First real integration is Shopify using the team's development account | Resolved |
| D8 | Automatic price-change threshold is adjustable by the merchant in the UI | Resolved |
| D9 | Business-model and pilot numbers not needed right now | Resolved/deferred |
| D10 | Repository license remains undecided | Open; not blocking the six-hour demo |

Required environment variable names are documented in `.env.example`; actual values remain local.

## Delivery risks

| Risk | Probability | Impact | Mitigation / trigger |
|---|---|---|---|
| Shopify credentials or Admin API permissions are wrong | Medium | Critical | Hour 0 auth smoke test using a no-op/read-only query; switch to pre-recorded honest failure path if unresolved by 1:30 |
| Shopify product creation validation fails | High | High | Use one minimal known-good fixture: title, body HTML, vendor, product type, tags, status draft |
| Goedel endpoint/model unstable | Medium | High | Deterministic structured fixture fallback by hour 2; text fallback for speech |
| Sarvam latency or venue noise | High | Medium | Recorded command/text input; speech is a demo enhancement, not core proof |
| Six-hour integration conflict | High | High | Rebase every 45 minutes; Kedar owns visible integration checkpoint |
| Scope creep to ONDC/Amazon/Meesho | High | High | Non-Shopify integrations roadmap-only; no work without cutting another item |
| Secrets committed | Low/Medium | Critical | `.env*` ignored; review `git diff --cached`; rotate any leaked secret immediately |
| Approval bypassed | Medium | High | Server-side approval check before connector mutation; test with direct API |
| Model invents catalogue facts | Medium | High | Missing-field prompt, manual edit control, deterministic fallback for demo |
| Demo network fails | Medium | High | Local app plus recorded Shopify screenshot/video; clearly label fallback |
| Six hours insufficient for full orders/inventory | High | Medium | Product publication and audit trail are completion; orders are stretch |

## Explicitly deferred

- Paytm Soundbox production integration
- ONDC, Amazon, Meesho, Google integrations
- Price-change default numeric value; the UI control exists, chosen per merchant
- Business/pilot numbers and pitch claims
- Repository license selection
- PostgreSQL, Redis/Celery, dedicated object storage, public hosting, native mobile

## Review cadence

Review this table at hours 1, 2, 4, and 5. A new risk must include an owner and mitigation; otherwise it is out of scope for this sprint.
