# Deployment and observability

## Prototype topology

The intended deployment consists of:

1. Static/Node-served React web application
2. FastAPI API process
3. Python worker process built from the same backend codebase
4. PostgreSQL database
5. Object storage or a documented local-volume fallback for uploaded demo assets

No message broker is required initially. The API writes business state and an outbox job in one PostgreSQL transaction. Workers claim jobs with row locking (for example, `FOR UPDATE SKIP LOCKED`), use bounded retries, and persist results.

The final hosting target is open. Deployment-specific files should be added only after the available platform/credits are confirmed.

## Environments

- `test`: deterministic fakes, isolated database, no external calls
- `development`: local database, connector simulators, model fake by default with opt-in live provider
- `demo`: seeded merchant and catalogue, simulated connectors, explicit reset command, optional live model with fallback

Production is outside the hackathon MVP.

## Health checks

- Liveness: process event loop responds.
- Readiness: database/migrations are available; worker readiness also checks job acquisition.
- Connector status: simulator/channel account health is shown separately and must not make the whole API unready.
- Model/speech provider status: optional dependency status, with fallback availability.

## Structured logs

Every log entry should include where applicable:

- Service/process name
- Environment
- Correlation and causation IDs
- Merchant/store IDs (non-sensitive identifiers)
- Agent run/action/job IDs
- Event type and state transition
- Duration and normalized outcome/error code

Do not log credentials, uploaded document contents, full buyer messages, bank/KYC data, or raw chain-of-thought.

## Metrics

Track at minimum:

- HTTP request count/latency/error rate
- Agent run count, duration, schema failures, escalations, and optional token/cost totals
- Approval wait time and outcomes
- Outbox depth and oldest pending age
- Connector success/retry/terminal failure count by channel and operation
- Order deduplication count
- Inventory synchronization latency and failures

For the MVP, structured logs and a simple internal status page may provide enough visibility. Do not add a large monitoring stack unless the deployment platform supplies it or a real need appears.

## Reliability and recovery

- Migrations run explicitly before readiness.
- Jobs use leases/heartbeats or recover safely from abandoned `running` state.
- Job payloads reference canonical records rather than embedding sensitive full documents.
- The demo has seed, reset, and health-check commands.
- A known-good fixture mode and recorded demo are available if network/model services fail.
- Database backup/restore is not a full production feature, but demo seed data lives in version control as synthetic fixtures.
