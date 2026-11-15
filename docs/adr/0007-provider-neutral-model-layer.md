# ADR 0007: Provider-neutral model layer via LangChain `init_chat_model`

- Status: Accepted
- Date: 2026-11-15
- Amends: resolved decision D3 (Goedel Machines as the LLM endpoint)

## Context

The team wants to use a free model tier during the hackathon and keep the option to switch
providers without code changes. Google ADK, Vercel AI SDK (TypeScript) and Vercel AI Gateway
(billing, extra hop) were considered and rejected. LangGraph is the orchestration framework.

## Decision

- Models are built with LangChain `init_chat_model`, selected by configuration:
  `MODEL_PROVIDER`, `MODEL_NAME`, `MODEL_API_KEY`, optional `MODEL_BASE_URL`.
- Default provider is `google_genai` with a free Google AI Studio key.
- The Goedel Machines endpoint remains available as an OpenAI-compatible option
  (`MODEL_PROVIDER=openai`, `MODEL_BASE_URL=https://api.goedelmachines.com/v1`).
- Extraction uses structured output into the `BillExtraction` schema with bounded retries.
- `MODEL_ENABLED=false` (or missing model credentials) uses recorded fixture extractions,
  labelled `fallback_used=true` in API responses.

## Consequences

- Switching providers is an `.env` change plus the provider's small LangChain package.
- One provider package (`langchain-google-genai`) is a default dependency; others are added
  only when used.
- Default tests never call a model.
