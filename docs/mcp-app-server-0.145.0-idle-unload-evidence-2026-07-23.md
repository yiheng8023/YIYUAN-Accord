# Codex app-server 0.145.0 idle-unload evidence

Date: 2026-07-23
Host: Codex CLI app-server 0.145.0 on Windows
Status: observed single-host 30-minute Sentinel idle unload and new-thread
recovery

## Outcome

One isolated, no-model-turn run executed the documented 30-minute idle path.
After the last subscription to an ephemeral thread was removed, the runner
sent no requests during the idle window. At about 30 minutes it jointly
observed:

- `thread/closed` for the bound thread;
- the bound Sentinel's natural `instance-stop` event; and
- disappearance of the Sentinel's exact Windows process identity.

A new ephemeral thread then called the same configured MCP and received a
different Sentinel instance. This is evidence for one host, one version, one
local Sentinel, and one run. It is not a public task-level lease API and is not
task-end immediate release.

## Exact identity and timing

The first Sentinel was bound by returned `instanceId`, PID, creation time,
image path, and parent PID:

| Field | Observation |
|---|---|
| thread | `019f8e92-6526-7621-8969-05f0eae8e634` |
| instance | `d402dd0b-9487-4ee7-b226-2f440eda53b7` |
| PID | `68856` |
| parent app-server PID | `44164` |
| requested observation | 1,920 seconds |
| observed idle duration | 1,800,765 ms |
| natural instance stop | `2026-07-23T19:13:07.652605+08:00` |
| thread closed | `2026-07-23T19:13:07.6881+08:00` |
| exact identity absent | `2026-07-23T19:13:07.688134+08:00` |

`thread/closed` was not used alone. The result required the natural Sentinel
stop event and exact identity disappearance during the idle window. A cleanup
marker written after the probe is recorded separately and is not counted as
idle-unload evidence.

The three events are temporally adjacent, not a causal proof. This run does
not establish whether `thread/closed` caused the Sentinel exit, whether the
Sentinel exit caused `thread/closed`, or whether the last unsubscribe was the
only internal cause.

## Recovery

The recovery thread
`019f8ead-e072-75b3-bc7b-dcc60c96dad2` successfully made a direct tool call
through a new Sentinel instance
`4e6b20a5-c4a3-4884-9a87-260bb5e2a42c` at PID `69492`.

This proves only new-thread recovery for this isolated run. Same-thread hot
recovery and active-turn refresh were not tested.

## Resource observation

The exact first Sentinel child had:

- 20,189,184 bytes working set;
- 14,016,512 bytes private usage; and
- 1,718,750 units of 100-ns CPU time at the initial snapshot.

Its exact process count changed from one to zero at idle unload. The runner did
not capture an app-server resource snapshot at the end of the idle window, and
the recovery Sentinel again used about 20.2 MB working set and 13.8 MB private
usage. Therefore this single run does not prove stable resource savings or a
total-host resource benefit. A repeat comparison is not justified unless a
concrete workload makes that decision relevant.

## Isolation and cleanup

The probe used an empty, explicit `CODEX_HOME`, copied no current config,
account, auth, or Plugin state, and did not call status discovery. It sent no
model turn. The isolated app-server nevertheless logged one unauthenticated
Responses WebSocket attempt that returned 401; no packet-level monitor was
used, so absence of network traffic is not claimed.

The runner closed its owned native app-server normally with return code `0`; no
forced handle kill was needed. Both recorded Sentinel exact identities were
absent afterward. The terminated app-server's Windows process object remained
partially queryable through the owned handle, so the record says its original
exact identity no longer matched rather than claiming that its numeric PID was
unqueryable. No PID-only signal, process-name scan, or process-name termination
was used.

## Raw evidence

- root:
  `C:/Projects/agent-autonomy-harness/.tmp/mcp-idle-observation-20260723`
- normalized result: 24,206 bytes,
  SHA-256 `6f468fb66b4fdd01616b04d228bd3039a2933573776da422e0d64b95b97ffa94`
- Sentinel event log: 2,643 bytes,
  SHA-256 `a883775d1645a47f61b07845673bf3f4efed9e16a4b7fcc62cd00a569617a5b9`
- machine record:
  `registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json`

The temporary root is retained as cleanup debt, not product payload.

## Claim boundary

This run does not establish:

- same-thread hot enable/disable, task-end immediate release, or a public
  lease/reference-count interface;
- that every MCP server or host unloads after 30 minutes;
- stable resource savings or total-host resource benefit;
- crash recovery, cancellation safety, or concurrent-subscriber safety;
- absence of network traffic;
- Codex Desktop, Plugin MCP, Claude, or other-host parity.

The subtractive result is to retain the native behavior as a bounded fallback
and not build a supervisor, proxy, or lifecycle manager from this observation.
