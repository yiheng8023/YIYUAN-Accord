# Current Matt semantic-authority composition static admission — 2026-07-28

## Result

The current Matt semantic-authority composition passes exact source, MIT
license, dependency-inventory, and static no-network/no-executable review for a
future disposable projection. It is not yet admitted for execution and is not
eligible for CC Switch installation or replacement.

The observed revision is
`ed37663cc5fbef691ddfecd080dff42f7e7e350d`. Exact identity comes from Git
blobs read with `git cat-file`, not the Windows checkout.

## Full dependency closure

The treatment is eight files, not three:

- `grill-with-docs/SKILL.md` and its OpenAI interface metadata;
- `domain-modeling/SKILL.md`, `CONTEXT-FORMAT.md`, `ADR-FORMAT.md`, and its
  OpenAI interface metadata;
- `grilling/SKILL.md` and its OpenAI interface metadata.

The thin entry explicitly composes `/grilling` with `/domain-modeling`.
`domain-modeling` in turn links the two relative format documents. Omitting
either the named Skills or the relative files would make the treatment
dependency-incomplete.

## Static and authority review

The eight files contain Markdown and YAML only. No script, executable,
dependency installation, network access, credential request, destructive
command, MCP, App, or account dependency was found. `grilling` explicitly
leaves decisions to the human and waits for confirmation before acting.

This is not a no-side-effect treatment. `domain-modeling` instructs the Agent
to create or update glossary and ADR files. A live trial therefore needs an
exact disposable mutable-file boundary. The entry also disables implicit
invocation, while the composition relies on the host resolving slash-named
Skills. Static review cannot prove that delivery path.

The literal `CONTEXT.md` and `docs/adr/` layout belongs to the candidate
treatment. The Harness acceptance contract continues to permit an equivalent
portable authority carrier; it does not promote Matt's filenames into a
universal standard.

## Windows raw-byte hazard

System Git configuration has `core.autocrlf=true`, while the upstream files
have no explicit text or EOL attribute. The checkout converted all inspected
LF files to CRLF. For example, `domain-modeling/SKILL.md` changed from 3427 raw
bytes to 3501 worktree bytes and therefore had a different SHA256.

Source pinning and projection must use Git blob/raw bytes. A worktree hash on
this host is not the upstream raw identity and must not silently replace it.
The exact temporary clone was removed after the raw identities and review
evidence were captured; it is not retained as product payload.

## Remaining gate

The next step is a disposable source-pinned projection containing all eight raw
files. It must prove:

- exact raw hashes and relative layout;
- task-scoped exposure of all three Skill identities;
- explicit selection of the non-implicit entry;
- whether named dependency and relative-file delivery is observed or remains
  unknown;
- no global, CC Switch, or consumer-directory mutation.

Only after that preflight may the live comparison seek separate execution
authority. Exposure will still not prove loader invocation, instruction
delivery, causation, or value.

## Post-admission exposure checkpoint

The later exact-revision retry materialized all eight raw files and the license
through the dedicated builder, and the Codex Desktop `0.145.0` no-turn probe
observed exactly the three required repository Skill identities under an
unselected-versus-selected control. The durable report is
[`audits/human-ai-collaboration-semantic-authority-current-matt-no-model-exposure-2026-07-28/REPORT.json`](../../audits/human-ai-collaboration-semantic-authority-current-matt-no-model-exposure-2026-07-28/REPORT.json).

This postscript does not rewrite the static-admission decision at observation
time. It records that the separate dependency-complete exposure gate later
passed without a thread, turn, model request, CC Switch change, global
configuration change, or installed-Skill change. Loader invocation, named
composition resolution, relative-file delivery, behavioral value, and live-run
authority remain open.

The machine-readable record is
[`registry/human-ai-collaboration-semantic-authority-current-matt-static-admission-2026-07-28.json`](../../registry/human-ai-collaboration-semantic-authority-current-matt-static-admission-2026-07-28.json).
