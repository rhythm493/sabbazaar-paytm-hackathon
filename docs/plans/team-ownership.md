# Team ownership

Names and assignments supplied by the team:

| Member | Primary workstream | Secondary/reviewer role |
|---|---|---|
| Harsimar | AI and agents | Reviews contracts used by AI output |
| Kedar | Merchant application | Reviews merchant approval UX |
| Ridam | Commerce and connectors | Reviews API/event contracts and Shopify integration |

The original pitch spelling for the third team member is retained in source material; engineering documentation uses **Ridam** as supplied for assignment.

## Harsimar — AI and agents

Owns:

- Goedel Machines OpenAI-compatible vision/general LLM client
- Catalogue draft schema and validation
- Image/bill-to-draft workflow
- Sarvam speech adapter or recorded/text fallback
- Confidence, missing-field, and evidence handling
- Deterministic fixture for model failures
- No direct connector execution

Must deliver one valid draft path to Kedar/Ridam within the first 90 minutes.

## Kedar — merchant application

Owns:

- Responsive React dashboard
- Product draft review/editor
- Approval and publish controls
- Adjustable price-change threshold control
- Publication status and Shopify result link
- Activity timeline from API events
- Loading/error/empty states
- Text command fallback for speech

Must make the demo usable by a non-technical judge without setup narration.

## Ridam — commerce and connectors

Owns:

- FastAPI control plane and SQLite schema/seed
- Product/action/audit/job persistence
- Shopify development-store Admin API connector
- Environment configuration and startup verification
- Idempotency, approval-before-mutation, and honest failures
- Activity endpoint and minimal contract coordination

Must not commit or log Shopify credentials from the development account.

## Integration rule

Every 45 minutes, all three merge/rebase to latest `main` and run the golden path or show the exact blocker. Working separately for six hours is a failure mode.

## Conflict resolution

- Shopify cannot be skipped or replaced with a fake success. If access fails, the UI labels it blocked and the team shows the recorded proof only with explicit disclosure.
- Contract ambiguity defaults to the smallest field required by the golden path.
- Any new feature requires one existing feature to be cut or moved to roadmap.
- When the team disagrees on model/output behavior, use the deterministic fixture for the demo and defer model refinement.
