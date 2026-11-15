# Demo runbook

Replace placeholders with verified commands once the application exists.

## Before presentation day

- Freeze feature work at least 24 hours before the demo.
- Tag/record the known-good commit.
- Verify the demo on the presentation machine and network.
- Prepare local and hosted routes, deterministic fixtures, screenshots, and a backup video.
- Confirm synthetic data contains no real personal, financial, or merchant information.

## Reset

1. Stop active demo interactions.
2. Run the verified reset command: `TBD`.
3. Apply/check migrations: `TBD`.
4. Seed Meena's Sarees: `TBD`.
5. Start services: `TBD`.
6. Confirm `SIMULATED` labels on all channels.

## Health check

- Web loads from a clean/private browser session.
- API liveness and readiness pass.
- Worker can claim a test/no-op job.
- Database migration version is current.
- All four connector simulators report ready.
- Model or deterministic fallback is ready.
- Speech or prepared text fallback is ready.
- Activity timeline starts from expected seed state.

## Rehearsal gate

Run the full script in `docs/product/demo-script.md` three consecutive times after reset. Record duration and any manual intervention. A failure resets the count after the cause is fixed.

## During an incident

1. State the issue honestly; do not present stale/simulated output as live behavior without labelling it.
2. Use visible retry/recovery if it strengthens the product story and fits the time budget.
3. Otherwise switch to the deterministic local fallback.
4. Use the backup recording only when interactive fallback is not viable.

## After the demo

- Preserve safe logs and correlation IDs for failures.
- Do not preserve uploaded audience/customer data.
- Record findings and follow-up actions in `SESSION_LOG.md`.
