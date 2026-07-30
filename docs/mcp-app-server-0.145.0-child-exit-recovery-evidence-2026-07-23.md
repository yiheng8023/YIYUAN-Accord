# Codex app-server 0.145.0 child-exit recovery evidence

Date: 2026-07-23
Status: observed two-run partial new-thread recovery only
Machine record:
[`../registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json`](../registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json)

## Result first

Two isolated Windows runs injected an abrupt exit into one local stdio MCP
child while a second MCP alias remained active. In both runs:

- the victim recorded the token-gated `crash-requested` event and exited
  without a natural `instance-stop`;
- the exact victim identity disappeared;
- the native app-server survived as the same exact process;
- the control MCP remained callable as the same exact instance in the original
  thread;
- the victim's next call in that same thread failed;
- a newly created ephemeral thread recovered the victim through a new exact
  instance.

The result is `partial-new-thread-recovery-only`, not same-thread automatic
recovery. The bounded operational fallback is a new thread or restart boundary.

## Isolation and fault

Each run used:

- one native app-server with an empty explicit `CODEX_HOME`;
- one ephemeral read-only thread before the fault;
- independent `lifecycle_control` and `lifecycle_victim` Sentinel aliases;
- no model turn, status discovery, reload, current configuration, current
  authentication, Plugin, App, or account state;
- a random one-process token that enabled `crash` only on the victim;
- exact PID, creation time, image path, and parent PID binding;
- owned app-server process handles and private cleanup markers only.

The injected fault was `os._exit(86)` before a tool response. It was not an OS
crash signal, hang, OOM, network failure, host crash, wrapper crash, Plugin
failure, or lease-controller failure.

## Repeated observations

| Run | Crash response | Same-thread victim call | New-thread victim call | App-server cleanup |
| --- | --- | --- | --- | --- |
| 01 | `Transport closed` | `Transport closed` | new exact instance succeeded | return code `0`, no handle kill |
| 02 | tool timeout after `5s` | tool timeout after `5s` | new exact instance succeeded | return code `1`, owned-handle kill required |

Both runs preserved the original app-server identity through the fault and
post-fault calls. Both preserved the original control identity in the first
thread. Both finished with all bound Sentinel identities and the app-server
identity absent.

Creating the fallback thread also initialized a second control instance and a
second victim instance in both runs. The old victim was absent and only one
victim identity was live when measured, but the result does not prove general
duplicate freedom or one process per configured server. The run-02 shutdown
difference also prohibits a stable graceful-cleanup claim.

## What this supports

For this Windows host, Codex app-server `0.145.0`, and the repository-local
Sentinel:

- abrupt local stdio child exit was detected as a failed tool call;
- one MCP child's exit did not restart the app-server or the already-bound
  control MCP in the original thread;
- same-thread next-call recovery did not occur in either run;
- new-thread next-call recovery did occur in both runs;
- cleanup used exact identities and owned handles without PID-only signaling or
  process-name termination.

This is evidence for a bounded failure fallback. It is not evidence for a new
supervisor, proxy, manager, or automatic task-scoped MCP controller.

## Claim limits

These runs do not prove:

- proactive or immediate automatic restart;
- same-thread hot enable/disable, reload completion, or task-end release;
- OS crash, OOM, hang, network, half-open transport, host, wrapper, Plugin, or
  lease-controller recovery;
- concurrent or in-flight call isolation;
- lease or reference-count correctness;
- restoration of prior enabled/disabled state;
- stable resource benefit or stable graceful shutdown;
- duplicate freedom beyond logged and exactly bound instances;
- no network traffic or no credential use;
- Desktop, Claude, other MCP implementations, or cross-host parity;
- universal MCP crash recovery or fault isolation.

No packet-level network monitor was used. The application logs contained no URL
line in these two runs, which is not a no-network claim.

## Cleanup debt and next gate

The two probe roots remain under:

- `.tmp/mcp-child-exit-recovery-20260723-run01`;
- `.tmp/mcp-child-exit-recovery-20260723-run02`.

They are retained as bounded raw evidence until the program-wide cleanup gate
or a separately authorized evidence migration. This record does not authorize
their deletion.

Use a new-thread/startup fallback after this failure class. Test hang, timeout,
or active-turn recovery only for a concrete workload whose value cannot be met
by that fallback; do not add a generic recovery controller to close an open
evidence question.
