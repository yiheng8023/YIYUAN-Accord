# Harness Decision-Packet Core PoC — 2026-08-08

## Result

One structured `GEN-RESEARCH-01` request now produces a deterministic,
source-bound packet for an Agent or Harness consumer. The reviewed fixture
retains all six route classes, current authority and original-evidence digests,
evidence ceilings, explicit unknowns, the governed `N/C/H` fallback,
all-false authorization gates, and all-false claim limits. `selectedRoute`
remains `null`.

Fourteen independent mutations fail closed with their expected typed errors:
unknown scenario, semantic-authority drift, original-evidence absence or digest
drift, route removal, unassessed or residual-route promotion, portfolio or
task-time selection, claim or fallback promotion, deprecated-routing
restoration, historical-authority override, and portable-core CC Switch
dependency promotion.

Run the non-executing interface with:

```powershell
python -B scripts/build_harness_decision_packet.py tests/fixtures/harness-decision-request-gen-research-01.json
```

## Evidence boundary

This is pure, zero-model mechanism evidence. The PoC executed zero models,
candidates, Plugins, managers, accounts, consumers, installs, enablements, and
publications. It did not parse a natural-language request, invoke or deliver a
candidate, select a live route, install or enable a capability, connect an
account, mutate CC Switch or a consumer, publish, or release.

Consequently it proves no natural-language interpretation, invocation,
instruction delivery, behavior, value, portability, production readiness,
release eligibility, or residual repository-authored gap. The
`acceptance.decision-ready-consumer-projection` criterion remains `partial` and
the canonical acceptance inventory remains 46 verified / 15 partial / 0
planned.

Machine-readable evidence is
[`registry/harness-decision-packet-core-poc-2026-08-08.json`](../../registry/harness-decision-packet-core-poc-2026-08-08.json).
