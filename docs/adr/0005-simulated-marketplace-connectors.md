# ADR 0005: Use simulated marketplace connectors for the prototype

- Status: Accepted
- Date: 2026-11-15

## Context

The pitch states that marketplace connections are simulated and no live Paytm production data is used. Real seller APIs require credentials, onboarding, certification, test accounts, and platform-specific lead time that can jeopardize the hackathon demo.

## Decision

Implement ONDC, Amazon, Meesho, and Google Business simulators behind the same connector contract intended for future real adapters. Support realistic validation, latency, retries, idempotency, and inbound order fixtures. Clearly label simulation in UI, logs, documentation, and the presentation.

## Consequences

- The team can demonstrate product behavior deterministically.
- Connector architecture and failure handling remain testable.
- The prototype cannot claim marketplace certification or production readiness.
- A real adapter can be added later without changing agent/domain boundaries.
- If organizers require a real integration, it must be separately scoped and cannot silently replace this decision.
