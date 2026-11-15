# Test suites

Planned test categories:

```text
tests/
  unit/          Domain, policy, mapping, and UI unit tests
  contract/      Shared connector contract suite
  integration/   API, database, outbox, and worker behavior
  e2e/           Merchant golden paths
  agent_evals/   Fixed structured-output and safety fixtures
  fixtures/      Synthetic images, bills, channel payloads, and model outputs
```

Default tests must run without live LLM, speech, Paytm, or marketplace access. Live evaluations are opt-in and clearly marked.
