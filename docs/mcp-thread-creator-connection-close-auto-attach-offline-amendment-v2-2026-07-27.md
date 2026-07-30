# MCP creator-close auto-attach offline amendment v2

Date: 2026-07-27

Status:
`offline-v2-amendment-deterministically-validated-not-live-authorized`

## Outcome

The admission decision `offline-amendment-required-before-live` has been
implemented as a new v2 protocol and an offline-injectable probe. The
historical protocol and probe remain unchanged at:

- `8A110058AAC75DDC54E2B3795F6F6BE12004E4CDE0262045BEA79D112D157326`
- `66CF7066B68D92139653C5E41AD74CAA64D00273C662A2899E396501974C2CF6`

This is a new revision, not a rewrite of retained history.

## V2 acquisition sequence

1. Connection B initializes and completes its `config/read` barrier.
2. Connection A initializes.
3. A sends `thread/start` for one `ephemeral=false`, `sandbox=read-only`
   thread.
4. A directly calls Sentinel identity on the new thread.
5. B directly calls Sentinel identity using that same thread ID.
6. The probe requires the same Sentinel PID and instance ID.
7. Rollout materialization is recorded once as `diagnostic-only`; absence
   cannot block setup.
8. Window evidence is sealed before B's direct post-window Sentinel call.

Connection B sends no `thread/resume`. The deterministic transport tests bind
the exact RPC order, same-thread and same-Sentinel identity, evidence ordering,
and failure cleanup. Failure closes both injected transports and invokes the
bounded Sentinel cleanup callback.

## What was validated

The v2 probe has no app-server launcher and accepts only injected transports.
Sixteen offline scenarios cover:

- B's barrier before A's `thread/start`;
- read-only, non-ephemeral thread creation;
- direct B calls with zero resume or model-turn requests;
- rollout absence as diagnostic evidence;
- same-thread and same-exact-Sentinel binding;
- seal-before-observer-post-window ordering;
- both-transport and bounded-Sentinel cleanup after failures;
- continued observer and Sentinel cleanup when another cleanup action fails;
- fail-closed validator mutations for setup order, forbidden RPCs, authority,
  formal-run count, and claims.

Offline simulation is not live evidence. Formal live run count and formal pair
report count remain zero.

## Authority and claim boundary

This record permits offline source validation and deterministic in-memory fake
transport tests only. It does not authorize app-server startup, loopback
transport, model/account use, external network access, configuration mutation,
installation, or live protocol execution.

It proves no second subscription, independent owner, lease/reference count,
task-end semantics, final release, resource benefit, cross-host parity,
cross-version parity, self-authored controller need, or live readiness. Any
future live trial requires a separate explicit authorization decision.
