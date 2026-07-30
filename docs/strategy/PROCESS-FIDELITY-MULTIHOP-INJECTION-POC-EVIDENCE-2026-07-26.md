# Process-fidelity multi-hop injection PoC evidence — 2026-07-26

Status: verified deterministic synthetic PoC; no live Agent or host-process
claim.

## Question and boundary

Can the matrix's process-loss metrics distinguish preservation, detectable
loss with source-backed recovery, undetected amplification, and an opaque
transformation edge?

This PoC freezes six invariants and their weights, then evaluates four
synthetic paths across compression, delegation, aggregation or review, and
recovery. It does not call a model, create a thread, observe automatic
compression, or test a Skill or Hook.

## Observed cases

| Case | Bounded outcome | Key observation |
| --- | --- | --- |
| Control | `control-preserved` | All six invariants and their provenance survive three edges. |
| Detected injection | `loss-detected-source-restored` | The omitted non-goal plus unauthorized commit assumption is detected after one hop; amplification stays `1.0`; the final synthetic recovery packet exact-matches the frozen source anchor. |
| Undetected injection | `hard-fail-undetected-amplification` | A later unsupported remote-green assumption raises weighted delta from `9` to `13`, so amplification is `13/9`. |
| Opaque edge | `opaque-stop` | The opaque edge stops evaluation instead of being treated as faithful. |

The detected case intentionally records a maximum weighted omission score of
`4/27`, one authority drift, four-edge anchor-to-final-packet distance, and
rollback success rate `1.0`. Those intermediate failures remain visible even
though the final packet matches the anchor.

## Interpretation

The result verifies that the deterministic evaluator and its fail-closed
classification can represent retained and added downstream delta
amplification plus exact final-packet recovery matching. It does not implement
or observe a three-edge replay, and it does not yet measure a cumulative
cross-hop loss budget. It provides a reusable metric contract for later live
trials.

It does not prove live Agent behavior, automatic host compression,
fresh-thread continuation, cross-host portability, lossless end-to-end
collaboration, or universal thresholds. It does not rank Matt Pocock,
Superpowers, the current repository Skills, AGENTS/rules, or Hooks, and it does
not justify a self-authored runtime capability.

The machine evidence is
[`registry/process-fidelity-multihop-injection-poc-evidence-2026-07-26.json`](../../registry/process-fidelity-multihop-injection-poc-evidence-2026-07-26.json).
