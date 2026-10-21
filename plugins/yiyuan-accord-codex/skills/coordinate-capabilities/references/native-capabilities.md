# Native capability discovery and Skill input

Read for native inventory or deliberate coordination of an installed Skill.
Use the current task's authority, manager, enabled choices and source restrictions.
This interface supplies metadata and a prepared input; the coordinator still owns
workflow fit, target control, execution, verification and resource closure.

## Discover and prepare

When available, call `coordinate_task_execution` with the actual receipt `cwd`:

- `action: "inventory"` obtains that workspace's native Skill metadata without
  starting a model turn. Treat load errors as incomplete discovery. Inspect the
  selected managed source, including its `SKILL.md` and policy, before dispatch.
- `action: "prepare-skill"` takes `skillRequest` containing `originalRequest`,
  `delegation: {sourceRef, scope}` and `selection: {name, path,
  expectedSha256, expectedPolicySha256}`. Use the exact enabled native path;
  the hashes bind the reviewed Skill and policy (`null` denotes absent policy).
  Preserve the actual request and delegation, rather than inventing a human
  request naming the Skill. A reference identifies evidence, not permission.

The source policy can suppress native implicit matching while leaving an
explicit path usable. Under the user's delegated selection authority, Accord
can choose that supported path. Source-defined prohibitions, disabled components,
user exclusions and new trust/data/cost boundaries still apply. Policy parsing is
metadata only; inspect the body for restrictions the metadata cannot express.

The installed [helper](../../../runtime/codex-capabilities.cjs) provides the same
bounded preparation when the MCP action is unavailable. Run its `--help`, then
`inventory --cwd ABSOLUTE` or pipe the structured request to `prepare --cwd ABSOLUTE`.
An explicit `--codex` selects an absolute executable or installed JavaScript launcher;
it neither installs a CLI nor changes shared configuration. Retain the returned
owned-process state. Failed or unverified closure holds that route for recovery.

The returned `process.queryPhase` is the last attempted query stage, not proof
that the peer received it. Termination diagnostics retain only the helper exit
code, signal, error code and elapsed milliseconds in `terminationExitCode`,
`terminationSignal`, `terminationError` and `terminationElapsedMs`; absent
observations remain `null`. These fields do not prove native exit or descendant
closure. Evaluate the actual exit and close observations separately, preserving
an unverified result even if later fixture or operator cleanup succeeds.

## Execute through the actual target

Preparation returns `nativeInput` with a typed Skill item bound to the selected
path. Send it only through a supported, authorized native turn interface whose
target the coordinator owns. When `cli.available` is true, `cli.stdin` supports
the normal explicit Skill route in `codex exec`; it still needs the bounded task
instructions and suitable current model, permissions, deadline and cleanup.
Name ambiguity withholds this CLI form; use the exact native path or resolve the
source ambiguity before dispatch. Never broaden target access to make a test pass.

Verify that the native host actually loaded the selected source before dependent
work, inspect the useful result against original material, and record the
coordinator's adoption or rejection with reasons. Recheck source identity and
owned process closure. A formatted input, metadata receipt or target assertion is
insufficient. Keep manager-owned files and policy unchanged.

Discovery beyond installed capabilities remains a bounded comparison for a real
gap or plausible benefit. This local query is not an ecosystem search, enablement
or installation. The [official Skill policy](https://learn.chatgpt.com/docs/build-skills)
distinguishes implicit matching from explicit invocation; actual dispatch and
support remain bound to the current host version and task authority.
