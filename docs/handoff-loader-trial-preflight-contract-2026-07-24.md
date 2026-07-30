# HND-FRESH-01 handoff loader-observability preflight

Date: 2026-07-24
Status: verified local preflight; fail-closed because no capture-capability
record is admitted
Machine record: [`../registry/handoff-loader-trial-preflight-contract-2026-07-24.json`](../registry/handoff-loader-trial-preflight-contract-2026-07-24.json)

## Purpose

`HND-FRESH-01` is a live view of `ABL-CTX-HANDOFF-01` Arm C, not an independent
continuation scorer. This read-only preflight binds only repository-recorded
source-backed `handoff` identity, tree, file manifest, and full canonical
protocol SHA-256 to a prospective host loader-event capture path. The protocol
path is fixed to the repository's canonical Batch-01 protocol; a caller cannot
substitute a compatible-looking protocol. It reads that protocol, not the live CC
Switch payload, account state, task history, or any private data.

The canonical Arm-C evaluator remains
[`evaluate_skill_ablation_batch_01_protocol.py`](../scripts/evaluate_skill_ablation_batch_01_protocol.py).
It alone evaluates invocation, loaded root/bytes, temporary artifact, receiver
outcome, repository envelope, and repetition.

## Gate and packet boundary

`loaderEvidenceCapture=available` requires a named/versioned loader-capture
adapter plus an evidence ID resolved from the canonical repository contract.
The admitted record must exactly match host identity/version and adapter
identity/version, bind a capture surface and artifact SHA-256, and retain false
claims for invocation, fresh-session behavior, receiver outcome, automatic
thread creation, and actual model/reasoning. A caller-provided `host://`
reference and shape-valid SHA-256 are not admission evidence. The canonical
registry currently contains zero admitted records, so every production
`available` request fails closed. Even a future admitted record does not prove
a loader event or invocation. `unavailable` and `unknown` are both
`blocked-missing-handoff-loader-observability`; neither may carry adapter
capability evidence to promote its state.

The CLI prints only a public packet and the private-oracle digest. The private
oracle remains parent-side and records the canonical protocol digest, capture
registry digest, selected payload binding, and evaluator reference. Validation
re-reads both fixed canonical records and exactly compares public and private
bindings. Packet and oracle SHA-256 values detect content drift relative to
their supplied bytes; they do not authenticate source provenance, host state,
or loader invocation.

Every preflight flag is false for loader invocation, fresh-session proof,
weak-Agent acceptance, and cross-host parity. Filesystem presence, startup-list
visibility, and Agent self-report are explicitly non-evidence.

## Follow-on bounded capability probe

The 2026-07-28
[Codex CLI 0.145.0 explicit-cue/control probe](handoff-loader-cli-0.145.0-capability-probe-2026-07-28.md)
observed a `Suggested Skills` section only in the `$handoff` arm. That is
behavior association, not an admitted capture capability, task-bound loader
event, or invocation proof. The host reported Skills context-budget omission
and did not bind the `handoff` identity or digest to the task, so this
preflight remains fail-closed.

## Authority and next gate

This preflight does not create a producer or receiver task, write a temporary
handoff artifact, inspect the live CC Switch root, mutate configuration, or
change the repository. A real capture interface must first be observed and
separately admitted; registry admission still only prepares a separately
authorized Arm-C run. That run must use the existing canonical evaluator and
meet its exact payload, artifact, receiver, model, host, and three-run
repetition requirements.
