# Applications

Runtime entry points live here. Shared domain, agent, connector, and contract logic belongs under `packages/`.

- `web/`: React merchant experience
- `api/`: FastAPI HTTP/control-plane composition
- `worker/`: background job runner and connector execution

The API and worker are separate processes built from the same modular Python backend, not independent microservices.
