# Codex Desktop Official Control-Surface Access Preflight

Date: 2026-07-31

Status: local official protocol confirmed; current Desktop attachment and
owner-bearing telemetry unavailable; no runtime actuation

## Outcome

The current `codex-cli 0.146.0` already defines most of the primitives needed
for a bounded Agent resource loop. The remaining observed gap is not a missing
protocol definition. It is the lack of a supported path from the current
Codex Desktop task surface to the owner-bearing read APIs of the same live
app-server instance.

This distinction prevents two opposite errors:

- declaring that Codex has no resource-management building blocks;
- treating a separately started app-server or a persisted task listing as
  control over the Desktop runtime the user is looking at.

## Local exact-version schema probe

The installed CLI generated its experimental app-server JSON schema into an
isolated repository temporary root. It produced 349 files and 3,343,741 bytes.
The relevant files were hashed before cleanup.

The Node process set was unchanged across generation:

| Observation | Value |
| --- | ---: |
| Node processes before | 72 |
| Node processes after | 72 |
| Added Node process IDs | 0 |
| Removed Node process IDs | 0 |

The generated root and its empty `.tmp` parent were then removed. No app-server
connection, model turn, thread transition, MCP transition, or global
configuration change occurred.

## Official primitives present in the installed CLI

The generated schema confirms:

- `thread/loaded/list` returns the thread IDs currently loaded in memory;
- `mcpServerStatus/list` accepts an optional `threadId`;
- `mcpServer/startupStatus/updated` carries a nullable `threadId`;
- `thread/tokenUsage/updated` carries a thread ID and model context window;
- compaction has both an event and `thread/compact/start`;
- `thread/backgroundTerminals/list` requires a thread ID and may report
  `osPid`, RSS, and CPU;
- thread-scoped background terminals have clean and terminate methods.

These are not one universal resource surface. In particular:

- background-terminal telemetry is not MCP-process telemetry;
- MCP status does not expose process RSS, CPU, lease count, or subscriber
  count;
- an owner-bearing startup notification is not a durable current-owner query;
- an actuator method is not authorization to call it.

## Current Desktop exposure

The current Codex App tools can list tasks and read the current task. They
reported the current task as active and its turn as in progress. They did not
expose token usage, background terminals, MCP owner or lease, or the exact
`thread/loaded/list` method.

The current host also showed:

- no attached app terminal for this task;
- no default `~/.codex/app-server-control` directory;
- `codex app-server proxy` exists, but no observed control socket;
- managed app-server daemon lifecycle is explicitly unsupported on Windows;
- the Codex runtime had established and close-wait TCP connections but no
  observed TCP listener.

The absence of a TCP listener does not prove that Desktop has no private IPC.
It proves only that this task did not observe a supported attach path through
the available socket, daemon, TCP, or App-tool surfaces.

## Upstream corroboration

OpenAI repository issue `#25914` describes the same boundary: a client may see
stored thread history without being able to bind it safely to the current
loaded Desktop turn. The issue explicitly rejects guessing from session files,
timestamps, or UI labels.

Issues `#14137` and `#35676` separately retain subscriber/unload and
subscriber-presence gaps. They corroborate that loaded, subscribed, persisted,
active, and controllable are distinct lifecycle states. They do not prove the
cause of the six process cohorts observed on this host.

## Decision

The evidence now supports:

- official protocol definition gap: false;
- current Desktop owner-telemetry access gap: observed;
- current Desktop actuator access gap: observed;
- official primitive reuse before a self-authored controller: required.

It does not support:

- safe owner attribution;
- release attribution;
- autonomous runtime action;
- a self-authored controller;
- a Desktop adapter implementation without a new authority decision.

## Next gate

Prefer a supported Desktop bridge that exposes the existing official
read-only owner, token, MCP-status, and background-terminal surfaces for the
current app-server instance.

If no such bridge is exposed, the next executable experiment is an isolated,
same-version, no-model app-server lifecycle trial. That trial would start a new
runtime and could create MCP state, so it requires separate authorization and
must not be presented as control over the existing Desktop task.
