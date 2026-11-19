"""Build the local Claude Code package or regenerate the Codex lifecycle Skill."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
CURRENT = "plugins/yiyuan-accord-codex"
ENTRY = "deliver-demand-driven-outcome"
PACKAGE = "yiyuan-accord"
MARKETPLACE = "yiyuan-accord-development"
HOOK_SOURCE = "plugins/yiyuan-accord-claude-code/runtime/accord-hook.cjs"
LIFECYCLE_SKILL = "skills/manage-plugin-lifecycle/SKILL.md"
LIFECYCLE_SOURCE = "product/skill-sources/manage-plugin-lifecycle.md"
CODEX_LIFECYCLE_SOURCE = "product/skill-sources/manage-plugin-lifecycle.codex.md"
SKILLS = (ENTRY, "coordinate-capabilities", "maintain-task-continuity",
          "verify-and-close-outcome")
FOUNDATION = (f"skills/{ENTRY}/references/meta-guidance.md",
              f"skills/{ENTRY}/references/meta-guidance.zh-CN.md")

CLAUDE_ENTRY = """Claude Code's native Hook supplies brief coordination guidance. Reuse the
meta-guidance already present in this task. When it is missing, read the bundled
[English translation](references/meta-guidance.md) before applying these duties.
The [Chinese source](references/meta-guidance.zh-CN.md) travels with it. Use this
foundation within the host's instruction hierarchy and the user's authority."""

NATIVE_CAPABILITIES = """# Claude Code capabilities

Use the available Skill and Agent tools, the native plugin view, and the session’s
effective tool requirements as sources. Respect user-only Skill invocation and
managed or disabled components.

For authorized delegation, check the current Agent tool and subagent definition
for model and effort. Choose them per subtask when both the dispatch interface
and the configured provider support them. Check context inheritance separately.
Record unsupported choices, environment overrides and observable substitutions.
[Skills](https://code.claude.com/docs/en/skills) · [Subagents](https://code.claude.com/docs/en/sub-agents)
"""

CONTINUITY = """## Restore the current task

Use Claude Code’s native history and continuation for the same task. Match the
actual session and workspace before reusing earlier facts. Preserve the current
goal, new user instructions, accepted results, pauses, permissions and outstanding
effects. A resume or compaction event calls for reconciliation. Use explicit
evidence of permission and ownership before acting.

Treat interruption as a request to stop. Check the tool’s actual terminal and
target state before retrying. When the result is uncertain, retain the uncertainty
and proceed only with independent work. A completed task leaves room for a normal
new request. Resume, a new task and a copied-history fork have different effects.

For authorized cross-entry continuation, use the host’s supported path with the
actual entry and configuration. Verify that the old writer stopped before allowing
another process to write. Use the host’s session and context observations where
available. Keep unfinished responsibilities with enough source evidence to recover.
[CLI resume](https://code.claude.com/docs/en/cli-reference) · [Desktop continuation](https://code.claude.com/docs/en/desktop#coming-from-the-cli)

"""

CLAUDE_LIFECYCLE = """
## Claude Code entry conditions

Use the installed CLI’s `--plugin-dir` for an isolated session. For local Desktop
Code, start with its native plugin management and check the actual Code engine,
provider, plugin scope and effective Hook policy. Use scoped setup and removal
controls within the user’s authority. Observe enabled state, actual events and
usable output before concluding adoption.
[CLI flags](https://code.claude.com/docs/en/cli-reference) · [Desktop plugin management](https://code.claude.com/docs/en/desktop#install-plugins)
"""


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def split_guidance(data, heading):
    text = data.decode("utf-8").replace("\r\n", "\n")
    if text.count("\n" + heading) != 1:
        raise ValueError(f"Current Skill structure changed around {heading}")
    return text.split("\n" + heading, 1)


def compose_lifecycle(common, setup_mechanism, host_guidance):
    placeholder = b"{{setup_mechanism}}"
    if common.count(placeholder) != 1:
        raise ValueError("Expected one setup mechanism in the shared lifecycle Skill source")
    shared = common.replace(b"\r\n", b"\n").replace(placeholder, setup_mechanism)
    appendix = host_guidance.replace(b"\r\n", b"\n")
    return shared.rstrip() + b"\n\n" + appendix.lstrip()


def build_codex_lifecycle(output):
    """Write the Codex lifecycle projection to a new file."""
    output = Path(output).absolute()
    content = compose_lifecycle(
        (ROOT / LIFECYCLE_SOURCE).read_bytes(),
        b"Accord's Node commands or state MCP",
        (ROOT / CODEX_LIFECYCLE_SOURCE).read_bytes(),
    )
    with output.open("xb") as stream:
        stream.write(content)
    return output


def build(output):
    """Write a new local marketplace and package. Return the package path."""
    output = Path(output).absolute()
    source_paths = ["scripts/build_claude_plugin.py", f"{CURRENT}/.codex-plugin/plugin.json",
                    HOOK_SOURCE, LIFECYCLE_SOURCE, "LICENSE", "NOTICE"]
    source_paths.extend(f"{CURRENT}/skills/{skill}/SKILL.md" for skill in SKILLS)
    source_paths.extend(f"{CURRENT}/{name}" for name in FOUNDATION)
    sources = {name: (ROOT / name).read_bytes() for name in source_paths}

    metadata = json.loads(sources[f"{CURRENT}/.codex-plugin/plugin.json"])
    version = metadata["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("Expected a current Accord version")
    manifest = {key: metadata[key] for key in
                ("description", "author", "homepage", "repository", "license", "keywords")}
    manifest.update(name=PACKAGE, version=f"{version}-claude-dev.3", skills="./skills/")
    hook_command = 'node "${CLAUDE_PLUGIN_ROOT}/runtime/accord-hook.cjs"'
    command = {"type": "command", "command": hook_command, "timeout": 3}
    hooks = {
        "SessionStart": [{"matcher": "startup|resume|clear|compact|fork", "hooks": [command]}],
        "SubagentStart": [{"hooks": [command]}],
    }
    files = {
        ".claude-plugin/plugin.json": json_bytes(manifest),
        "hooks/hooks.json": json_bytes({"hooks": hooks}),
        "runtime/accord-hook.cjs": sources[HOOK_SOURCE],
        "LICENSE": sources["LICENSE"],
        "NOTICE": sources["NOTICE"],
        "README.md": (
            "# YIYUAN Accord development package\n\n"
            f"This Claude Code candidate uses Accord {version} guidance. It is intended for scoped verification.\n\n"
            "Use the plugin directory with `claude --plugin-dir` for a single CLI session. "
            "The package supplies Skills and adds coordination guidance at supported native entry events. "
            "Claude Code owns execution, interruption and session restoration. "
            "Validate the actual local Desktop Code entry before treating it as supported.\n"
        ).encode("utf-8"),
    }
    for skill in SKILLS:
        name = f"skills/{skill}/SKILL.md"
        files[name] = sources[f"{CURRENT}/{name}"]
    entry = f"skills/{ENTRY}/SKILL.md"
    title = "# Coordinate the current task"
    front_matter, body = split_guidance(files[entry], title)
    _, separator, duties = body.lstrip("\n").partition("\n\n")
    if not separator or not duties.startswith("Interpret each input"):
        raise ValueError("Current coordination Skill no longer has one opening paragraph before its duties")
    files[entry] = f"{front_matter}\n{title}\n\n{CLAUDE_ENTRY}\n\n{duties}".encode("utf-8")
    for name in FOUNDATION:
        files[name] = sources[f"{CURRENT}/{name}"]
    files["skills/coordinate-capabilities/references/native-capabilities.md"] = NATIVE_CAPABILITIES.encode("utf-8")

    continuity = "skills/maintain-task-continuity/SKILL.md"
    head, _ = split_guidance(files[continuity], "## Modes and saved task state")
    _, tail = split_guidance(files[continuity], "## Interruptions and changed surroundings")
    interruptions, _ = split_guidance(tail.encode("utf-8"), "## Context capacity and handoff")
    files[continuity] = (
        head + "\n\n" + CONTINUITY + "## Interruptions and changed surroundings" + interruptions.rstrip() + "\n"
    ).encode("utf-8")
    files[LIFECYCLE_SKILL] = compose_lifecycle(
        sources[LIFECYCLE_SOURCE], b"the plugin's entry Hook", CLAUDE_LIFECYCLE.encode("utf-8"),
    )

    package = output / "plugins" / PACKAGE
    catalog = {
        "name": MARKETPLACE,
        "description": "Local YIYUAN Accord development builds for Claude Code.",
        "owner": {"name": manifest["author"]["name"]},
        "plugins": [{"name": PACKAGE, "source": f"./plugins/{PACKAGE}", "description": manifest["description"]}],
    }
    catalog_bytes = json_bytes(catalog)
    written = {
        **{f"plugins/{PACKAGE}/{name}": data for name, data in files.items()},
        "build.json": json_bytes({
            "accordSourceVersion": version,
            "candidateVersion": manifest["version"],
            "sources": {name: sha256(data).hexdigest() for name, data in sources.items()},
            "marketplaceSha256": sha256(catalog_bytes).hexdigest(),
            "packageFiles": {name: sha256(data).hexdigest() for name, data in files.items()},
        }),
        ".claude-plugin/marketplace.json": catalog_bytes,
    }
    output.mkdir()
    try:
        with TemporaryDirectory(prefix=".build-", dir=output) as temporary:
            staging = Path(temporary)
            for name, data in written.items():
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            # The host can discover the marketplace only after the complete package is present.
            for name in ("plugins", "build.json", ".claude-plugin"):
                (staging / name).rename(output / name)
    except OSError as error:
        try:
            output.rmdir()
        except OSError:
            raise OSError(f"Build failed with output remaining at {output}: {error}") from error
        raise
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path, help="A new local Claude marketplace directory")
    destination.add_argument("--codex-lifecycle-output", type=Path, help="A new Codex lifecycle Skill file")
    args = parser.parse_args()
    try:
        if args.codex_lifecycle_output is not None:
            print(build_codex_lifecycle(args.codex_lifecycle_output))
        else:
            print(build(args.output))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
