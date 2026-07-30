# HND-FRESH-01 Codex CLI 0.145.0 capability probe

Date: 2026-07-28
Status: explicit-cue behavior association observed; exact loader event absent
Machine record:
[`../registry/handoff-loader-cli-0.145.0-capability-probe-2026-07-28.json`](../registry/handoff-loader-cli-0.145.0-capability-probe-2026-07-28.json)

## Result

Two fresh Codex CLI threads used `gpt-5.4-mini` with requested `low` reasoning
and the same bounded, temporary-file-only task class. The explicit arm began
with `$handoff`; the native control omitted that cue. The explicit artifact
contained the source-backed Skill's required `Suggested Skills` section, while
the control artifact did not. Their complete normalized content and SHA-256
digests are preserved in the machine record, and both temporary directories
were removed after capture.

This is a bounded behavior association. It is not exact invocation evidence.
The host emitted only Skills context-budget messages and did not emit a
task-bound loader event carrying the `handoff` identity, file-manifest digest,
or loaded source. In the explicit arm it also reported that two Skills were not
included in the model-visible list, so the probe cannot establish that
`handoff` itself was visible or that its body caused the output.

## Weak-floor route

The first requested weak-floor route, `gpt-5.3-codex-spark` with `low`
reasoning, failed because the model was at capacity and produced no artifact.
The fallback pair therefore measures only the requested
`gpt-5.4-mini`/`low` condition. Actual model and reasoning were not
independently verified.

## Authority and cleanup

Each successful probe was authorized to create one Markdown file only under
its exact `C:\tmp` directory. No repository, Git, configuration, Skill,
account, or network mutation was authorized. No repository probe artifact was
created. Both temporary output directories, including transient Codex
workspace mounts, were removed after their contents and hashes were recorded.

## Decision boundary

The formal preflight remains
`blocked-missing-handoff-loader-observability`. This probe does not admit
canonical Arm C, prove explicit or implicit loader invocation, prove
fresh-session receiver recovery, prove losslessness, prove weak-Agent
acceptance, or prove automatic thread creation. The next gate remains a
host- or parent-emitted task-bound loader event carrying the `handoff` identity
or digest; only then may the existing canonical three-repetition
producer/receiver trial be considered for admission.
