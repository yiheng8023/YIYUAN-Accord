#!/usr/bin/env python3
"""List Codex Skill roots without creating a thread or requesting a model.

This probe is intentionally narrower than the task-scoped exposure probes. It
sends only ``initialize``, ``initialized``, and ``skills/list`` to one
short-lived app-server process. Its purpose is to observe whether same-name
Skills from ``~/.agents/skills`` and the CC Switch-managed Codex projection are
both listed. Listing is not loader invocation, instruction delivery, behavior,
or precedence evidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterable

try:
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        PLUGIN_FEATURES,
        _git_status_digest,
        build_command,
        canonical_sha256,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
except ImportError:  # Direct script execution.
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        PLUGIN_FEATURES,
        _git_status_digest,
        build_command,
        canonical_sha256,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )


PROBE_ID = "codex-app-server-skill-root-collision-v1"
DEFAULT_NAMES = (
    "ask-matt",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "grilling",
    "implement",
    "research",
    "resolving-merge-conflicts",
    "to-spec",
    "to-tickets",
    "wayfinder",
    "writing-great-skills",
)
MANAGER_SYMLINK_CONTROL_NAMES = (
    "grill-me",
    "grill-with-docs",
    "handoff",
    "improve-codebase-architecture",
    "prototype",
    "setup-matt-pocock-skills",
    "tdd",
    "teach",
    "triage",
)


def _normalized(path: str | Path) -> str:
    return str(path).replace("\\", "/").rstrip("/").lower()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observe_tree(root: Path) -> dict[str, Any]:
    """Return a content/link manifest without following directory symlinks."""

    root = root.expanduser().resolve(strict=False)
    if not root.exists() and not root.is_symlink():
        return {
            "exists": False,
            "path": root.as_posix(),
            "entryCount": 0,
            "manifestSha256": None,
        }

    entries: list[dict[str, Any]] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            for entry in sorted(iterator, key=lambda item: item.name.lower()):
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                if entry.is_symlink():
                    entries.append(
                        {
                            "path": relative,
                            "type": "symlink",
                            "target": _normalized(os.readlink(path)),
                        }
                    )
                elif entry.is_dir(follow_symlinks=False):
                    entries.append({"path": relative, "type": "directory"})
                    visit(path)
                elif entry.is_file(follow_symlinks=False):
                    entries.append(
                        {
                            "path": relative,
                            "type": "file",
                            "bytes": entry.stat(follow_symlinks=False).st_size,
                            "sha256": _sha256_file(path),
                        }
                    )
                else:
                    entries.append({"path": relative, "type": "other"})

    if root.is_symlink():
        entries.append(
            {"path": ".", "type": "symlink", "target": _normalized(os.readlink(root))}
        )
    else:
        visit(root)
    return {
        "exists": True,
        "path": root.as_posix(),
        "entryCount": len(entries),
        "manifestSha256": canonical_sha256(entries),
    }


def build_readonly_inventory_command(
    executable: str,
    *,
    plugin_features_to_disable: tuple[str, ...] = PLUGIN_FEATURES,
) -> list[str]:
    command = build_command(
        executable,
        plugin_features_to_disable=plugin_features_to_disable,
    )
    # Replace the effective static MCP table for this process. Per-server
    # ``enabled=false`` still asks the current CLI to parse every configured
    # transport first, which can fail before app-server initialization when an
    # older transport shape remains in the user's config.
    command.extend(("-c", "mcp_servers={}"))
    return command


def classify_collision_rows(
    skills: list[dict[str, Any]],
    names: Iterable[str],
    *,
    home: Path,
) -> list[dict[str, Any]]:
    # Keep caller-supplied Windows paths lexical when this pure classifier is
    # exercised on a POSIX host.  ``Path.resolve`` would otherwise reinterpret
    # ``C:/...`` beneath the current POSIX directory and make identical paths
    # compare unequal.  Live probes already pass an absolute native home.
    home = home.expanduser()
    results: list[dict[str, Any]] = []
    for name in names:
        common = _normalized(home / ".agents" / "skills" / name / "SKILL.md")
        codex = _normalized(home / ".codex" / "skills" / name / "SKILL.md")
        cc = _normalized(home / ".cc-switch" / "skills" / name / "SKILL.md")
        matches = [row for row in skills if row.get("name") == name]
        paths = sorted({_normalized(str(row.get("path", ""))) for row in matches})
        common_listed = common in paths
        dedicated_listed = codex in paths or cc in paths
        if common_listed and dedicated_listed:
            classification = "both-listed"
        elif common_listed:
            classification = "common-only"
        elif dedicated_listed:
            classification = "codex-only"
        elif not matches:
            classification = "neither"
        else:
            classification = "deduplicated-ambiguous"
        results.append(
            {
                "name": name,
                "listingClassification": classification,
                "commonRootListed": common_listed,
                "dedicatedConsumerListed": dedicated_listed,
                "listedRows": [
                    {
                        "path": str(row["path"]).replace("\\", "/"),
                        "scope": row["scope"],
                        "enabled": row["enabled"],
                    }
                    for row in sorted(
                        matches,
                        key=lambda value: _normalized(str(value.get("path", ""))),
                    )
                ],
                "provesInstructionDeliveryPrecedence": False,
            }
        )
    return results


def summarize_expected_cohort(
    skills: list[dict[str, Any]],
    *,
    expected_names: Iterable[str],
    disabled_names: Iterable[str] = (),
    absent_names: Iterable[str] = (),
    home: Path,
) -> dict[str, Any]:
    """Check one manager cohort on the no-model ``skills/list`` surface."""

    # This is a pure comparison seam and must preserve the path flavour in the
    # supplied inventory rather than resolving it through the test host.
    home = home.expanduser()
    expected = tuple(dict.fromkeys(expected_names))
    disabled = set(disabled_names)
    absent = tuple(dict.fromkeys(absent_names))
    rows_by_name: dict[str, list[dict[str, Any]]] = {}
    for row in skills:
        rows_by_name.setdefault(str(row.get("name", "")), []).append(row)

    failures: list[str] = []
    observed: list[dict[str, Any]] = []
    for name in expected:
        rows = rows_by_name.get(name, [])
        canonical = _normalized(
            home / ".cc-switch" / "skills" / name / "SKILL.md"
        )
        paths = [_normalized(str(row.get("path", ""))) for row in rows]
        expected_enabled = name not in disabled
        row_enabled = [row.get("enabled") is True for row in rows]
        listed_once = len(rows) == 1
        canonical_path = listed_once and paths == [canonical]
        enablement_match = listed_once and row_enabled == [expected_enabled]
        if not listed_once:
            failures.append(f"expected-name-not-listed-once:{name}")
        if not canonical_path:
            failures.append(f"noncanonical-path:{name}")
        if not enablement_match:
            failures.append(f"enablement-mismatch:{name}")
        observed.append(
            {
                "name": name,
                "listedRowCount": len(rows),
                "paths": paths,
                "expectedEnabled": expected_enabled,
                "observedEnabled": [row.get("enabled") for row in rows],
                "canonicalCcRoot": canonical_path,
            }
        )

    absent_rows: dict[str, int] = {}
    for name in absent:
        count = len(rows_by_name.get(name, []))
        absent_rows[name] = count
        if count:
            failures.append(f"absent-name-listed:{name}")

    return {
        "expectedNames": list(expected),
        "disabledNames": sorted(disabled),
        "absentNames": list(absent),
        "observedRows": observed,
        "absentNameRowCounts": absent_rows,
        "allExpectedNamesListedOnce": all(
            row["listedRowCount"] == 1 for row in observed
        ),
        "allPathsCanonicalCcRoot": all(
            row["canonicalCcRoot"] for row in observed
        ),
        "enablementMatches": all(
            row["observedEnabled"] == [row["expectedEnabled"]]
            for row in observed
        ),
        "allAbsentNamesMissing": all(count == 0 for count in absent_rows.values()),
        "failures": failures,
    }


class RecordingSession(AppServerSession):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sent_messages: list[dict[str, Any]] = []

    def send(self, message: dict[str, Any]) -> None:
        self.sent_messages.append(json.loads(json.dumps(message)))
        super().send(message)


def _surface_observations(cwd: Path, home: Path) -> dict[str, Any]:
    return {
        "codexConfig": file_observation(home / ".codex" / "config.toml"),
        "ccSettings": file_observation(home / ".cc-switch" / "settings.json"),
        "ccDatabase": file_observation(home / ".cc-switch" / "cc-switch.db"),
        "ccSkillRoot": observe_tree(home / ".cc-switch" / "skills"),
        "commonSkillRoot": observe_tree(home / ".agents" / "skills"),
        "codexSkillRoot": observe_tree(home / ".codex" / "skills"),
        "repositoryStatus": _git_status_digest(cwd),
    }


def _request_boundary(messages: list[dict[str, Any]]) -> dict[str, Any]:
    methods = [str(message.get("method")) for message in messages]
    return {
        "sentMethods": methods,
        "threadStartCount": methods.count("thread/start"),
        "turnStartCount": methods.count("turn/start"),
        "modelRequestCount": sum(
            1
            for message in messages
            if isinstance(message.get("params"), dict)
            and "model" in message["params"]
        ),
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    requests = report.get("requestBoundary", {})
    if requests.get("sentMethods") != ["initialize", "initialized", "skills/list"]:
        failures.append("hard-fail-request-sequence")
    if requests.get("threadStartCount") != 0:
        failures.append("hard-fail-thread-created")
    if requests.get("turnStartCount") != 0:
        failures.append("hard-fail-turn-created")
    if requests.get("modelRequestCount") != 0:
        failures.append("hard-fail-model-requested")

    mutation = report.get("mutationBoundary", {})
    if mutation.get("allObservedSurfacesStable") is not True:
        failures.append("hard-fail-observed-surface-drift")
    for key in ("globalConfigWritten", "managerWritten", "consumerRootsWritten"):
        if mutation.get(key) is not False:
            failures.append(f"hard-fail-{key}")

    claims = report.get("claimBoundary", {})
    if claims.get("provesListingPathIdentity") is not True:
        failures.append("fail-listing-path-identity")
    for key in (
        "provesInstructionDeliveryPrecedence",
        "provesSkillLoaderInvocation",
        "provesSkillBehavior",
        "provesManagerUpdateSafety",
    ):
        if claims.get(key) is not False:
            failures.append("hard-fail-claim-boundary")
            break
    cohort = report.get("cohortExposure")
    if cohort is not None and cohort.get("failures"):
        failures.append("hard-fail-cohort-exposure")
    return failures


def run_probe(
    cwd: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
    names: Iterable[str] = DEFAULT_NAMES,
    home: Path | None = None,
    expected_names: Iterable[str] | None = None,
    disabled_names: Iterable[str] = (),
    absent_names: Iterable[str] = (),
) -> dict[str, Any]:
    cwd = cwd.resolve()
    home = (home or Path.home()).expanduser().resolve(strict=False)
    executable = resolve_codex_executable(codex_executable)
    before = _surface_observations(cwd, home)
    command = build_readonly_inventory_command(executable)
    session = RecordingSession(command, cwd, timeout_seconds)
    try:
        initialized = initialize(session)
        skills = request_skills(session, cwd, request_id=1)
        session.close()
    except BaseException:
        session.abort()
        raise
    after = _surface_observations(cwd, home)
    stable = before == after
    report = {
        "schema": 1,
        "id": PROBE_ID,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "host": {
            "codexCliVersion": initialized.get("userAgent"),
            "platformFamily": initialized.get("platformFamily"),
            "platformOs": initialized.get("platformOs"),
        },
        "repository": {"path": cwd.as_posix()},
        "inventory": inventory_summary(skills),
        "collisionRows": classify_collision_rows(skills, names, home=home),
        "managerSymlinkControlRows": classify_collision_rows(
            skills,
            MANAGER_SYMLINK_CONTROL_NAMES,
            home=home,
        ),
        "requestBoundary": _request_boundary(session.sent_messages),
        "processBoundary": {
            "returnCode": session.process.returncode,
            "pluginFeaturesDisabled": list(PLUGIN_FEATURES),
            "staticMcpTableOverriddenEmpty": True,
            "globalConfigOverrideUsed": False,
            "skillsConfigOverrideUsed": False,
        },
        "stderrClassification": classify_stderr(session.stderr_lines),
        "mutationBoundary": {
            "before": before,
            "after": after,
            "allObservedSurfacesStable": stable,
            "globalConfigWritten": False,
            "managerWritten": False,
            "consumerRootsWritten": False,
            "rawConfigRecorded": False,
            "rawSettingsRecorded": False,
            "rawDatabaseRecorded": False,
        },
        "claimBoundary": {
            "provesListingPathIdentity": True,
            "provesInstructionDeliveryPrecedence": False,
            "provesSkillLoaderInvocation": False,
            "provesSkillBehavior": False,
            "provesManagerUpdateSafety": False,
            "provesCrossHostPortability": False,
        },
    }
    if expected_names is not None:
        report["cohortExposure"] = summarize_expected_cohort(
            skills,
            expected_names=expected_names,
            disabled_names=disabled_names,
            absent_names=absent_names,
            home=home,
        )
    report["failures"] = validate_report(report)
    report["status"] = "pass" if not report["failures"] else "fail"
    report["reportSha256"] = canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_probe(
        args.cwd,
        codex_executable=args.codex_executable,
        timeout_seconds=args.timeout_seconds,
    )
    if args.output:
        write_report(args.output, report)
    else:
        content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        print(content, end="")
    return 0 if report["status"] == "pass" else 1


def write_report(path: Path, report: dict[str, Any]) -> None:
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
