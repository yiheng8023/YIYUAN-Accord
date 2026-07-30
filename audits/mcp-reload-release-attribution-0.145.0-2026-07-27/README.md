# MCP reload-release attribution audit

This directory retains the raw Codex CLI app-server `0.145.0` observations for
the reload-to-old-runtime-release attribution probe.

- `run-01.json` is excluded because its request payload inherited the prior
  experiment identifier.
- `formal-01.json` through `formal-03.json` are excluded because they predate
  raw-report self-binding of the exact probe and Sentinel hashes.
- `evidence-01.json` through `evidence-03.json` are the three formal,
  independently isolated repetitions.

Each included repetition kept app-server and the original thread alive for a
five-second attribution window after disabling the Sentinel and receiving a
reload response. No new thread, unsubscribe, teardown, harness marker, or PID
signal occurred inside that window.

The raw reports contain local temporary paths, PIDs, instance identifiers,
process samples, app-server stderr, and file-name inventories. They contain no
copied authentication values. The app-server attempted an unauthenticated
Responses websocket and received HTTP 401 in every included repetition; this
is recorded rather than rewritten as a no-network claim.

These files are authoritative host evidence, not disposable `.tmp` output.
Deletion or migration requires a separate cleanup decision.
