# Connector package

Planned connector protocol, normalized result/error types, contract-test helpers, and the first real Shopify development-store adapter. Other channel adapters are deferred.

Adapters translate at the edge and do not own canonical commerce state. Only the worker/application layer executes mutation methods. See `docs/architecture/connector-contract.md`.
