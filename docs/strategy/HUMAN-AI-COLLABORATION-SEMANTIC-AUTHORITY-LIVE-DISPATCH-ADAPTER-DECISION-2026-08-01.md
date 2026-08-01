# SEM-03 Live-Dispatch Adapter Decision

Date: 2026-08-01
Status: `reviewed-offline-gate-preflight-no-dispatch`
Decision: `separate-thin-live-adapter-justified-not-implemented`

## Question

After the dedicated dry runtime adapter proved exact treatment materialization,
inventory isolation, and twelve unsent phase templates, should SEM-03 reuse the
shared weak-Agent runner, add a send switch to the dry adapter, or introduce a
separate live-dispatch adapter?

This review authorizes only repository decision, validator, and test writes. It
does not authorize a model request, candidate instruction execution, a live
authority receipt, CC Switch or global configuration mutation, or a Skill/Hook.

## Frozen evidence

The repository source was reviewed at
`88d23974bf4c652b790f439cd7e2bd396b630a79`. The governed dry report remains
byte-bound at file SHA-256
`849a014057a8d8696da1a9afcfe77c0eea80e1b3541ab8791a82272e58578798`
and embedded report digest
`284122bab9c24d31308bd75868d7369f7cd47fc4eb49ad17af18f058add3386f`.
It sent twelve `initialize`/`skills/list` inventory requests and zero phase,
thread, turn, or model requests.

The current host reported `codex-cli 0.146.0`. A fresh official Codex manual
snapshot was retrieved on 2026-08-01 from the Codex App Server documentation;
the full fetched manual was 1,837,849 bytes at SHA-256
`f03e415eedbdfc2682e0e4b9d5e5b0b045d3b3a9568f5c01204f22df619c2cb4`.
The reviewed app-server surface supplies:

- `turn/interrupt`, followed by terminal `turn/completed` status;
- `model/rerouted`, which can expose service-side route replacement;
- `thread/tokenUsage/updated`, which can support parent-observed usage;
- `thread/unsubscribe`, whose final-subscriber unload has a documented
  30-minute inactivity grace period rather than immediate unloading.

The full official snapshot is not vendored. The registry stores the source
identity, retrieval time, full-manual digest, reviewed structured extraction,
applicability, and freshness limitation. Before any future live execution,
material Codex/manual drift requires a refetch and recheck.

## Facts, inference, and decision

Facts:

- the dry adapter is intentionally non-transmitting and is governed as such;
- the shared weak-Agent runner does not accept SEM-03 treatment identities and
  does not provide an independent loader or instruction-delivery event;
- the four phases require fresh threads, exact file scopes, parent injection of
  frozen human decisions before phase 2, and fail-closed route observation;
- unsubscribing is not an immediate resource-release guarantee.

Inference:

- adding a send flag to the dry adapter would mix no-dispatch evidence with a
  live side-effect boundary;
- directly using the shared runner would erase the SEM-03 treatment and phase
  contract;
- a long-lived app-server session would weaken phase isolation and immediate
  resource cleanup;
- the residual need is a thin host execution adapter, not evidence for a new
  Skill or Hook.

Decision:

Create a separate, deny-by-default live adapter only as a thin composition of
existing primitives. Do not implement or execute live transport in this
decision slice. An offline authority gate and simulated observation tests may
be implemented, but they must remain incapable of starting app-server without
a separately governed, per-run authority receipt.

## Required adapter contract

One run contains four phases and no more than four model requests. Every phase
uses a new app-server process and one ephemeral thread. The parent, not the
model, injects `HUMAN_DECISIONS.json` before phase 2 and verifies that it was
absent before phase 1.

The requested route is exactly `gpt-5.3-codex-spark` with `low` reasoning and
no provider fallback. Parent evidence must include the route returned by
`thread/start`, any `model/rerouted` event, token-usage updates, terminal turn
status, item and tool effects, pre/post public-tree delta, exact app-server
process exit, and temporary-root removal.

Any hard failure stops the next phase. An active timed-out or route-invalid
turn is interrupted first; if interruption or completion does not finish
within the bounded interval, the app-server process is aborted. The run is not
scored, and only governed redacted evidence may be retained.

Without an independent loader event, even a live run can establish only
bounded treatment association. It cannot by itself prove that Skill
instructions reached the model, behavioral causation, candidate superiority,
cross-host value, or a residual self-authored need.

## Offline authority-gate preflight

The pure offline gate is implemented at
[`scripts/build_human_ai_collaboration_semantic_authority_live_dispatch_gate.py`](../../scripts/build_human_ai_collaboration_semantic_authority_live_dispatch_gate.py).
It imports no app-server client, starts no process, and sends no request. With
no authority receipt, each of the three treatment plans is blocked with zero
authorized phases and zero model budget. Its only accepted receipt shape is a
test-simulation receipt that explicitly denies both process creation and model
dispatch. Simulated parent observations exercise pass and fail-closed stop
decisions without counting as live evidence. The report is staged in its
destination directory, flushed, and atomically replaced; a failed replacement
removes staging and leaves no partial governed report.

The governed three-treatment report is
[`audits/human-ai-collaboration-semantic-authority-live-dispatch-gate-preflight-2026-08-01/REPORT.json`](../../audits/human-ai-collaboration-semantic-authority-live-dispatch-gate-preflight-2026-08-01/REPORT.json),
at file SHA-256
`80083c3ccbd4b48741a6836cfda7d30eab92f307e4a45f8c3a0b1975b04f8f14`
and embedded digest
`5920ac58cf20a26bcca18844a660eaa126d854aa2abfea03839f1874507eaac2`.

## Current boundary

The offline authority gate and its simulated observation tests are now true.
The live adapter, live authority receipt, app-server execution, live host
trial, and dispatch readiness remain false. Model dispatch and candidate
instruction execution remain unauthorized. The machine-readable decision is
[`registry/human-ai-collaboration-semantic-authority-live-dispatch-adapter-decision-2026-08-01.json`](../../registry/human-ai-collaboration-semantic-authority-live-dispatch-adapter-decision-2026-08-01.json).
