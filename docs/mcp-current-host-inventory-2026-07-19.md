# MCP Current-Host Inventory — 2026-07-19

Status: `MCP-01` observed on one Codex Desktop/local host; partial inventory;
no lifecycle actuation
Structured record:
[`mcp-current-host-inventory-2026-07-19.json`](../registry/mcp-current-host-inventory-2026-07-19.json)

## Bound question

What can the current host prove about configured, visible, initialized,
callable, authenticated, and process-attributable MCP states without changing
configuration, accessing accounts, or starting/stopping a server?

The capability gap is task-scoped lifecycle evidence: the repository has dated
startup-control metadata, but not a current host state that can support safe
enable/disable, lease, idle-release, or resource-savings claims.

## Authority and data boundary

Allowed:

- read `codex mcp` help and list output;
- count current runtime tool definitions by MCP namespace;
- read PID, parent PID, process name, working set, private memory, and CPU time
  after one bounded native approval;
- call one local, account-free `node_repl` arithmetic probe.

Not allowed or performed:

- reading process command lines, environment variables, secrets, tokens, or
  account payloads;
- MCP add/remove, enable/disable, login/logout, or configuration writes;
- process start, stop, kill, unload, or restart;
- external account calls or broad candidate discovery.

## Observations

### CLI configuration

`codex-cli 0.144.6` exposes `mcp list`, `get`, `add`, `remove`, `login`, and
`logout`. The read-only `codex mcp list` result was:

```text
No MCP servers configured yet.
```

This proves zero standalone servers in the CLI user-configuration view for the
observation. It does not describe the complete Codex Desktop Plugin/App/runtime
tool surface.

### Desktop tool projection

The current runtime metadata exposed 487 total tool definitions. Of those, 457
used MCP server naming across 12 namespaces:

| Namespace | Tool definitions |
| --- | ---: |
| `codegraph` | 1 |
| `codex_apps` | 361 |
| `codex_security` | 11 |
| `context7` | 2 |
| `creative_production_mcp` | 1 |
| `dataAnalyticsWidgets` | 5 |
| `github` | 44 |
| `neo4j_graph` | 3 |
| `node_repl` | 3 |
| `openai_api_key_local_confirmation` | 1 |
| `playwright` | 24 |
| `sites_design_picker` | 1 |

This is a tool-definition projection, not a health or authentication census.
It also demonstrates that `codex mcp list` is not a complete Desktop inventory.

### Bounded callability

One local `node_repl` MCP call evaluated `6 * 7` and returned `42`. This is
`observed-single-host` callability evidence for that one local namespace and
probe only. No other projected MCP was invoked.

### Process attribution

The first process-tree query was denied by the current sandbox. A bounded
read-only elevation was approved for `ProcessId`, `ParentProcessId`, and
`Name` only. The result contained two `codex.exe` rows and descendants named
`cmd.exe`, `codex-code-mode-host.exe`, `conhost.exe`, `node.exe`,
`node_repl.exe`, and `pwsh.exe`.

Without command-line or stronger host-owned identity evidence, generic Node
processes cannot be mapped safely to a specific MCP. Therefore PID ownership,
lease ownership, and safe stop eligibility remain unresolved. The probe did not
expand into command-line inspection because that could expose unrelated or
sensitive arguments.

### Point-in-time resource snapshot

A later bounded read-only snapshot recursively selected every descendant of
the two observed `codex.exe` roots. It found 107 processes with a combined
5,052,542,976-byte working set and 3,702,562,816 private-memory bytes. The main
counts were 65 `node.exe`, 30 `cmd.exe`, five `node_repl.exe`, two `codex.exe`,
two `conhost.exe`, two `pwsh.exe`, and one `codex-code-mode-host.exe`.

This is a one-point Codex descendant-forest aggregate. It is not an MCP-only,
per-server, per-task, startup, idle, or steady-state baseline. No command line,
environment variable, executable path, credential, or volatile PID list was
stored. The large Node share makes lifecycle resource measurement materially
worth testing, but it does not identify which process belongs to which MCP or
prove that any memory is safely releasable.

## State classification

| Surface | Configured | Enabled/visible | Initialized | Callable | Authenticated |
| --- | --- | --- | --- | --- | --- |
| CLI standalone MCP configuration | observed none | not applicable | not applicable | not applicable | not inspected |
| Desktop MCP-named projection | unknown | 457 definitions visible | unknown except `node_repl` | `node_repl` probe only | not inspected |
| Codex descendant processes | not derivable | not derivable | generic runtime descendants observed | not derivable | not inspected |

Do not collapse these columns into a single “installed” or “active” state.

## Supported claims

1. The CLI standalone MCP configuration reported zero configured servers.
2. The Desktop runtime projected 457 MCP-named definitions across 12
   namespaces, so CLI configuration output is not the Desktop capability
   inventory.
3. One local `node_repl` tool was callable for a bounded arithmetic probe.
4. PID, parent PID, and generic executable names were insufficient to establish
   specific MCP process ownership or safe release.
5. One point-in-time Codex descendant forest contained 107 processes using
   about 5.05 GB working set and 3.70 GB private memory in aggregate.

## Unsupported claims

This evidence does not prove that:

- all 457 definitions are initialized, healthy, connected, authenticated, or
  callable;
- the 12 namespaces are permanent or ecosystem-complete;
- tools map one-to-one to processes;
- any observed Node process can be safely stopped;
- mid-session enable/disable, unload, restart, leases, reference counts, idle
  release, crash recovery, or task-end release exists;
- resource savings occurred;
- the aggregate memory belongs only to MCPs or to one task;
- the point-in-time total is a stable startup, idle, or steady-state baseline;
- another host/account/version has the same state.

## Routing result and next gate

Native/runtime inventory was sufficient for `MCP-01`; no external candidate,
installation, custom controller, or retired Manager reactivation is justified.
The next stronger probe is a disposable startup-profile comparison with
explicit pre/post tool definitions, process attribution, latency, task result,
approval prompts, and restoration evidence. It must precede any lifecycle
actuation or resource-savings claim.
