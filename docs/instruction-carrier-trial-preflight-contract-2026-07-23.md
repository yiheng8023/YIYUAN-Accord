# CTX-07 instruction-carrier trial preflight packet

Date: 2026-07-23
Status: verified local packet contract; no host run
Machine record: [`../registry/instruction-carrier-trial-preflight-contract-2026-07-23.json`](../registry/instruction-carrier-trial-preflight-contract-2026-07-23.json)

## Purpose

This read-only builder closes an operational gap before a future CTX-07 live
trial. It binds the exact carrier bytes, target host condition, identity
templates, and a public task packet to a separate private oracle. It does not
create a task, call a model, read a host instruction surface, or observe a
loader event.

The existing [`evaluate_instruction_carrier_adherence.py`](../scripts/evaluate_instruction_carrier_adherence.py)
remains the canonical semantic scorer. This builder neither replaces that
scorer nor duplicates the continuation packet used by `HND-FRESH-01`.

## Preflight gate

`loaderEvidenceCapture` has exactly three values:

- `available`: a named host/parent adapter has a way to record the exact
  task-bound `host-instruction-loader-event` required by the canonical scorer;
- `unavailable` or `unknown`: the packet is
  `blocked-missing-host-loader-observability`.

`available` is permission to prepare a separately authorized live attempt, not
proof that a carrier was discovered or loaded. Filesystem presence, a startup
list, and an Agent self-report remain non-evidence. Every preflight result is
explicitly false for live-host proof, weak-Agent acceptance, and cross-host
parity.

## Public/private separation

The public packet carries stable carrier identity, carrier SHA-256, requested host/version/model/reasoning
condition, three-run identity templates, output schema, and no-write authority
limits. The private oracle carries the expected carrier-rule outcomes and limit
text. Packet and oracle each receive a stable SHA-256; the CLI emits only the
public envelope and oracle digest, never the private oracle body. The validator rejects a
changed public packet, mismatched carrier binding, altered oracle digest, or an
oracle copied into the public packet. Therefore the public packet does not
contain the private oracle body, while the private oracle remains directly
consumable by the canonical scorer. These digests are integrity and
drift-detection values relative to supplied bytes, not source authentication,
carrier authority, or proof of any host observation.

## Run boundary

A real run still requires separate user/host authority. It must instantiate
distinct run, host-run, thread, and task IDs, capture the exact loader event
for the instantiated task and carrier digest, and then pass the raw response
plus parent evidence to the existing CTX-07 evaluator. The builder's small
binding validator rejects a loader event with another task ID or carrier digest;
the canonical scorer remains responsible for the full evidence decision. This
contract does not authorize host configuration changes, carrier mutation, thread
creation, or cross-host comparison.

## Local checks

The focused test covers available, unavailable, and unknown preflight states;
public-packet tampering; carrier binding; task-ID template binding; private
oracle exposure; non-available capture promotion; and preflight evidence-count
promotion. These checks are local contract evidence only.
