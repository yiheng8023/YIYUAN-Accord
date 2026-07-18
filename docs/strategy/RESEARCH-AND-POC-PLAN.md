# Research And Proof Plan

## Sequence

1. Bind concrete scenarios, authority boundaries, and observable acceptance.
2. Inventory native and runtime-owned capability for each target host.
3. Review official implementations and documentation.
4. Review maintained third-party Skills, Hooks, MCP tooling, Plugins, and Apps.
5. Compare coverage, safety, maintenance, overlap, and portability.
6. Compose existing capabilities where sufficient.
7. Implement only the residual gap supported by repeatable evidence.

The first research pass should be broad enough to avoid local tunnel vision but
must remain scenario-driven. A catalog entry is discovery evidence, not
execution authority or proof of suitability.

## PoC 1 — context lifecycle and continuation

Test transparent and opaque hosts separately: direct counters when exposed,
automatic-compression observations, heuristic fallback, handoff timing,
repository-anchored completeness, same-workspace thread creation when supported,
and one-click/manual fallback when it is not.

## PoC 2 — Git collaboration topology

Evaluate read-only truth recovery, branch versus worktree choice, safe creation,
merge and cleanup recommendations, native approval response, denial handling,
and protection of unrelated dirty work. Creation may become automatic where
reversible; merge, deletion, overwrite, and remote mutation remain governed by
host approval and repository policy.

## PoC 3 — MCP lifecycle

Determine whether each host supports startup-only control, safe mid-session
enable/disable, per-task leases or reference counts, idle release, concurrent
isolation, crash recovery, prior-state restoration, and measurable resource
savings. A Skill-only implementation is not assumed; possible carriers include
native APIs, Hooks, launch wrappers, adapters, supervisors, or MCP proxies.

## Initial acceptance signals

Measure user interventions, unnecessary approval prompts, task success,
handoff loss, context waste, idle MCP processes, startup latency, incorrect
topology actions, rollback reliability, and cross-host behavioral variance.
