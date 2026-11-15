# Shared packages

This directory contains reusable modules with enforced boundaries:

- `agents/`: probabilistic workflows and model interfaces
- `commerce/`: deterministic domain/application logic
- `connectors/`: channel interfaces, mappings, and simulators
- `contracts/`: schemas crossing process/module boundaries

Packages must not import runtime entry points from `apps/`.
