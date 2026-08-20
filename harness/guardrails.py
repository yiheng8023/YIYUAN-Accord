from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import os
import re
import subprocess
from typing import Any, Callable
from urllib.parse import urlsplit
_AUTHORITY_DECISION_FIELDS = {
    "state", "candidateRevision", "namedHuman", "authorizedAt",
    "claimCeilingAccepted", "publicationAuthorized", "releaseAuthorized",
}
RELEASE_PROCEDURE_FIELDS = {"orderedGates", "rule"}
RELEASE_GATE_FIELDS = {
    "id", "dependsOn", "acceptanceIds", "completionOperand", "condition",
}
RELEASE_GATE_SEQUENCE = (
    ("repository-candidate", None),
    ("exact-candidate-hosted-verification", "exactCandidateHostedVerification"),
    ("exact-human-release-authorization", "namedHumanReleaseAuthorization"),
    ("exact-tagged-public-release", "exactTaggedPublicRelease"),
    ("release-verification-and-cleanup", "releaseVerificationAndCleanup"),
)
REPOSITORY_AUTHORIZATION_FIELDS = _AUTHORITY_DECISION_FIELDS | {"mode"}
MANIFEST_FIELDS = {
    "codex": {
        "name", "version", "description", "author", "homepage", "repository",
        "license", "keywords", "skills", "interface",
    },
    "claude-code": {
        "$schema", "name", "version", "description", "author", "homepage",
        "repository", "license", "keywords", "skills",
    },
}
CODEX_INTERFACE_FIELDS = {
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "capabilities",
    "websiteURL",
    "defaultPrompt",
}
CODEX_METADATA_FIELDS = {
    "interface": {"display_name", "short_description", "default_prompt"},
    "policy": {"allow_implicit_invocation"},
}


def repository_relative_path(root: Path, locator: Any) -> Path | None:
    if not isinstance(locator, str) or not locator or "\\" in locator:
        return None
    relative = Path(locator)
    if (
        relative.is_absolute()
        or relative.drive
        or not relative.parts
        or ".." in relative.parts
    ):
        return None
    try:
        resolved_root = root.resolve(strict=True)
        candidate = resolved_root / relative
        resolved = candidate.resolve(strict=False)
    except OSError:
        return None
    if not resolved.is_relative_to(resolved_root):
        return None
    probe = resolved_root
    for part in relative.parts:
        probe /= part
        if probe.is_symlink():
            return None
        if not probe.exists():
            break
    return candidate


def forbidden_path_present(path: Path) -> bool:
    try:
        if path.is_file() or path.is_symlink():
            return True
        return path.is_dir() and any(
            item.is_file() or item.is_symlink() for item in path.rglob("*")
        )
    except OSError:
        return True


def known_task_residue(root: Path) -> list[str]:
    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        return ["<unreadable-root>"]
    residue: list[str] = []
    for current, directories, files in os.walk(resolved_root, followlinks=False):
        base = Path(current)
        retained_directories: list[str] = []
        for name in directories:
            path = base / name
            relative = path.relative_to(resolved_root).as_posix()
            parts = Path(relative).parts
            if "__pycache__" in parts or ".tmp" in parts:
                residue.append(relative)
            if name != ".git" and not path.is_symlink():
                retained_directories.append(name)
        directories[:] = retained_directories
        for name in files:
            path = base / name
            relative = path.relative_to(resolved_root).as_posix()
            parts = Path(relative).parts
            lowered_name = name.lower()
            if (
                lowered_name == "error.log"
                or lowered_name.endswith((".pyc", ".pyo"))
                or "__pycache__" in parts
                or ".tmp" in parts
            ):
                residue.append(relative)
    return sorted(set(residue))


def clean_git_checkout(root: Path) -> bool:
    try:
        top_level = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        if Path(top_level).resolve(strict=True) != root.resolve(strict=True):
            return False
        status = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False
    return not status


def package_sha256(root: Path, locators: list[str]) -> str:
    digest = sha256()
    for locator in sorted(locators):
        digest.update(locator.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256((root / locator).read_bytes()).digest())
    return digest.hexdigest()


def codex_metadata_errors(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"adapter codex metadata is unreadable: {exc}"]
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        if "\t" in raw_line:
            return [f"adapter codex metadata line {line_number} uses a tab"]
        if not raw_line.startswith(" "):
            match = re.fullmatch(r"([a-z_][a-z0-9_]*):", raw_line)
            if match is None or match.group(1) in sections:
                return [f"adapter codex metadata line {line_number} is invalid"]
            current = match.group(1)
            sections[current] = {}
            continue
        match = re.fullmatch(r"  ([a-z_][a-z0-9_]*):\s+(.+)", raw_line)
        if match is None or current is None or match.group(1) in sections[current]:
            return [f"adapter codex metadata line {line_number} is invalid"]
        sections[current][match.group(1)] = match.group(2)
    if set(sections) != set(CODEX_METADATA_FIELDS):
        return ["adapter codex metadata top-level fields are invalid"]
    for section, expected_fields in CODEX_METADATA_FIELDS.items():
        values = sections[section]
        if set(values) != expected_fields:
            return [f"adapter codex metadata {section} fields are invalid"]
    for field in CODEX_METADATA_FIELDS["interface"]:
        try:
            value = json.loads(sections["interface"][field])
        except json.JSONDecodeError:
            return [f"adapter codex metadata interface.{field} is invalid"]
        if not isinstance(value, str) or not value.strip():
            return [f"adapter codex metadata interface.{field} is invalid"]
    if sections["policy"]["allow_implicit_invocation"] != "true":
        return ["adapter codex metadata implicit invocation policy is invalid"]
    return []


def manifest_shape_errors(adapter_id: Any, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    unsupported = sorted(set(manifest) - MANIFEST_FIELDS.get(adapter_id, set()))
    if unsupported:
        errors.append(
            f"adapter {adapter_id} manifest contains unsupported fields: {unsupported}"
        )
    if manifest.get("skills") != "./skills/":
        errors.append(f"adapter {adapter_id} manifest skills locator is invalid")
    if adapter_id == "codex":
        interface = manifest.get("interface")
        if not isinstance(interface, dict) or set(interface) != CODEX_INTERFACE_FIELDS:
            errors.append("adapter codex manifest interface fields are invalid")
        elif interface.get("capabilities") != ["Interactive", "Read"]:
            errors.append("adapter codex manifest capabilities are invalid")
    return errors


def marketplace_errors(
    adapter_id: Any,
    marketplace: dict[str, Any],
    manifest_name: Any,
    expected_path: Any,
) -> list[str]:
    errors: list[str] = []
    entries = marketplace.get("plugins")
    if (
        set(marketplace) != {"name", "interface", "plugins"}
        or not isinstance(marketplace.get("interface"), dict)
        or set(marketplace["interface"]) != {"displayName"}
    ):
        errors.append(f"adapter {adapter_id} marketplace shape is invalid")
    if not isinstance(entries, list) or len(entries) != 1:
        errors.append(f"adapter {adapter_id} marketplace entry is not unique")
        return errors
    entry = entries[0]
    if not isinstance(entry, dict) or entry.get("name") != manifest_name:
        return errors + [f"adapter {adapter_id} marketplace entry is not unique"]
    if set(entry) != {"name", "source", "policy", "category"}:
        errors.append(f"adapter {adapter_id} marketplace entry shape is invalid")
    if entry.get("source") != {"source": "local", "path": expected_path}:
        errors.append(f"adapter {adapter_id} marketplace source is invalid")
    if entry.get("policy") != {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }:
        errors.append(
            f"adapter {adapter_id} marketplace policy must be AVAILABLE/ON_INSTALL"
        )
    return errors


def plugin_file_locators(root: Path, plugin_root: Path) -> list[str]:
    resolved_root = root.resolve(strict=True)
    files: list[str] = []
    for path in plugin_root.rglob("*"):
        if path.is_file() or path.is_symlink():
            files.append(path.relative_to(resolved_root).as_posix())
    return sorted(files)


def validate_projection_package(
    root: Path,
    adapter_id: Any,
    manifest_locator: Any,
    contract_locator: Any,
    skill_locator: Any,
    metadata_locators: list[str],
) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    declared = [
        locator
        for locator in (manifest_locator, contract_locator, skill_locator, *metadata_locators)
        if isinstance(locator, str)
    ]
    if isinstance(skill_locator, str):
        metadata_parent = Path(skill_locator).parent / "agents"
        for locator in metadata_locators:
            path = repository_relative_path(root, locator)
            if (
                Path(locator).parent != metadata_parent
                or Path(locator).name != "openai.yaml"
                or path is None
                or not path.is_file()
            ):
                errors.append(f"adapter {adapter_id} metadata file is invalid: {locator}")
            elif adapter_id == "codex":
                errors.extend(codex_metadata_errors(path))
            else:
                errors.append(f"adapter {adapter_id} does not admit metadata files")
    if not isinstance(manifest_locator, str):
        return None, errors
    plugin_root = repository_relative_path(
        root, Path(manifest_locator).parent.parent.as_posix()
    )
    if plugin_root is None or not plugin_root.is_dir():
        errors.append(f"adapter {adapter_id} plugin root is invalid")
        return None, errors
    actual = plugin_file_locators(root, plugin_root)
    unexpected = sorted(set(actual) - set(declared))
    missing = sorted(set(declared) - set(actual))
    if unexpected:
        errors.append(
            f"adapter {adapter_id} package contains undeclared files: {unexpected}"
        )
    if missing:
        errors.append(f"adapter {adapter_id} package omits declared files: {missing}")
    try:
        digest = package_sha256(root, declared) if not missing else None
    except OSError:
        digest = None
        errors.append(f"adapter {adapter_id} package identity is unavailable")
    return digest, errors


def projection_observation_errors(
    observed: dict[str, Any],
    host_report: dict[str, Any],
    label: str,
    adapter_id: str,
) -> list[str]:
    errors: list[str] = []
    if observed.get("adapterId") != adapter_id:
        errors.append(f"{label} projection identity mismatch")
    incomplete = False
    for field in ("manifest", "marketplace", "contract", "skill"):
        expected = host_report.get(field)
        if isinstance(expected, str) and field not in observed:
            incomplete = True
        elif observed.get(field) != expected:
            errors.append(
                f"{label} {field} locator does not match current adapter {adapter_id}"
            )
    current = host_report.get("identity")
    if not isinstance(current, dict):
        return errors + [f"{label} current projection identity unavailable"]
    for field in (
        "skillSha256",
        "manifestSha256",
        "marketplaceSha256",
        "contractSha256",
        "packageSha256",
    ):
        if field in current and field not in observed:
            incomplete = True
        elif observed.get(field) != current.get(field):
            errors.append(
                f"{label} {field} does not match current adapter {adapter_id}"
            )
    if incomplete:
        errors.append(
            f"{label} projection identity fields do not match current adapter {adapter_id}"
        )
    return errors


def projection_evidence_binding_errors(
    root: Path,
    acceptance: dict[str, Any],
    host_reports: dict[str, Any],
    read_json: Callable[[Path, str, list[str]], dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    criteria = acceptance.get("criteria")
    if not isinstance(criteria, list):
        return errors
    for criterion_index, criterion in enumerate(criteria):
        evidence = criterion.get("evidence") if isinstance(criterion, dict) else None
        if not isinstance(evidence, list):
            continue
        for evidence_index, item in enumerate(evidence):
            if not isinstance(item, dict) or "bindsProjection" not in item:
                continue
            label = f"criteria[{criterion_index}].evidence[{evidence_index}]"
            adapter_id = item.get("bindsProjection")
            if not isinstance(adapter_id, str) or not adapter_id.strip() or adapter_id not in host_reports:
                errors.append(f"{label}.bindsProjection is unknown")
                continue
            locator = item.get("locator")
            if not isinstance(locator, str):
                continue
            observation = read_json(root, locator, [])
            observed = observation.get("projection")
            if not isinstance(observed, dict):
                observed = observation.get("projectionIdentity")
            if not isinstance(observed, dict):
                errors.append(f"{label} lacks projection identity")
                continue
            errors.extend(
                projection_observation_errors(
                    observed, host_reports[adapter_id], label, adapter_id
                )
            )
    return errors


def criterion_observation_decision(
    criterion_id: Any,
    item: dict[str, Any],
    observation: dict[str, Any],
    task_mappings: dict[str, set[str]],
    label: str,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if item.get("supportsCriterion") != criterion_id:
        errors.append(f"{label} does not explicitly support {criterion_id}")
        return False, errors
    decisions = observation.get("acceptanceDecisions")
    accepted = isinstance(decisions, dict) and decisions.get(criterion_id) == "accepted"
    if not accepted:
        errors.append(f"{label} has no accepted {criterion_id} decision")
    criterion_evidence = observation.get("criterionEvidence")
    detail = (
        criterion_evidence.get(criterion_id)
        if isinstance(criterion_evidence, dict)
        else None
    )
    if (
        not isinstance(detail, dict)
        or detail.get("decision") != "accepted"
        or not isinstance(detail.get("claim"), str)
        or not detail["claim"].strip()
    ):
        errors.append(f"{label} lacks direct {criterion_id} criterion evidence")
        accepted = False
    task_id = observation.get("taskId")
    if (
        isinstance(task_id, str)
        and task_id.strip()
        and criterion_id not in task_mappings.get(task_id, set())
    ):
        errors.append(f"{label} task {task_id} does not map to {criterion_id}")
    return accepted, errors


def closeout_sequence_errors(
    work_item: dict[str, Any], criterion_ids: set[str]
) -> list[str]:
    sequence = work_item.get("closeoutSequence")
    if not isinstance(sequence, list) or not sequence or any(
        not isinstance(stage, dict) for stage in sequence
    ):
        return ["active work item closeoutSequence must be a non-empty object list"]
    errors: list[str] = []
    stage_ids: list[str] = []
    states: list[str] = []
    coverage: set[str] = set()
    for index, stage in enumerate(sequence):
        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or not stage_id.strip():
            errors.append(f"closeoutSequence[{index}].id must be non-empty")
        else:
            stage_ids.append(stage_id)
        state = stage.get("state")
        if state not in {"completed", "active", "pending"}:
            errors.append(f"closeoutSequence[{index}].state is invalid")
        else:
            states.append(state)
        mapped = stage.get("acceptanceIds")
        if (
            not isinstance(mapped, list)
            or not mapped
            or any(not isinstance(item, str) or item not in criterion_ids for item in mapped)
        ):
            errors.append(f"closeoutSequence[{index}].acceptanceIds is invalid")
        else:
            coverage.update(mapped)
        if not isinstance(stage.get("stopCondition"), str) or not stage[
            "stopCondition"
        ].strip():
            errors.append(f"closeoutSequence[{index}].stopCondition must be non-empty")
    if len(stage_ids) != len(set(stage_ids)):
        errors.append("active work item closeoutSequence ids must be unique")
    if states.count("active") != 1:
        errors.append("active work item closeoutSequence must contain one active stage")
    ranks = {"completed": 0, "active": 1, "pending": 2}
    if states and [ranks[state] for state in states] != sorted(
        ranks[state] for state in states
    ):
        errors.append("active work item closeoutSequence order is invalid")
    if coverage != criterion_ids:
        errors.append("active work item closeoutSequence must map every criterion")
    return errors


def release_procedure_errors(
    procedure: Any, criterion_ids: set[str], goal_prompt: Any
) -> list[str]:
    if not isinstance(procedure, dict) or set(procedure) != RELEASE_PROCEDURE_FIELDS:
        return ["program.releaseProcedure is invalid"]
    if not isinstance(procedure.get("rule"), str) or not procedure["rule"].strip():
        return ["program.releaseProcedure.rule must be non-empty"]
    gates = procedure.get("orderedGates")
    if not isinstance(gates, list) or len(gates) != len(RELEASE_GATE_SEQUENCE) or any(
        not isinstance(gate, dict) or set(gate) != RELEASE_GATE_FIELDS
        for gate in gates
    ):
        return ["program.releaseProcedure.orderedGates is invalid"]
    errors: list[str] = []
    coverage: set[str] = set()
    for index, gate in enumerate(gates):
        label = f"releaseProcedure.orderedGates[{index}]"
        gate_id = gate.get("id")
        expected_id, expected_operand = RELEASE_GATE_SEQUENCE[index]
        if not isinstance(gate_id, str) or not gate_id.strip():
            errors.append(f"{label}.id must be non-empty")
        if gate_id != expected_id or gate.get("completionOperand") != expected_operand:
            errors.append(f"{label} does not match the required release gate sequence")
        expected_dependency = [] if index == 0 else [gates[index - 1].get("id")]
        if gate.get("dependsOn") != expected_dependency:
            errors.append(f"{label}.dependsOn must name only the previous gate")
        mapped = gate.get("acceptanceIds")
        if (
            not isinstance(mapped, list)
            or not mapped
            or any(not isinstance(item, str) or item not in criterion_ids for item in mapped)
        ):
            errors.append(f"{label}.acceptanceIds is invalid")
        else:
            coverage.update(mapped)
        if not isinstance(gate.get("condition"), str) or not gate["condition"].strip():
            errors.append(f"{label}.condition must be non-empty")
    if coverage != criterion_ids:
        errors.append("program.releaseProcedure must map every criterion")
    if not isinstance(goal_prompt, dict) or goal_prompt.get("releaseGateIds") != [
        gate_id for gate_id, _ in RELEASE_GATE_SEQUENCE
    ]:
        errors.append("program.goalModePrompt.releaseGateIds must match releaseProcedure")
    return errors


def repository_release_authorization_errors(authorization: Any) -> list[str]:
    if not isinstance(authorization, dict):
        return ["acceptance.releaseAuthorization must be an object"]
    if authorization.get("state") == "authorized":
        return ["repository releaseAuthorization cannot grant human authority"]
    if authorization.get("state") not in {
        "unrequested",
        "request-prepared",
        "declined",
    }:
        return ["acceptance.releaseAuthorization.state is invalid"]
    if (
        set(authorization) != REPOSITORY_AUTHORIZATION_FIELDS
        or authorization.get("mode") != "task-time-human-authority"
    ):
        return ["acceptance.releaseAuthorization mode or fields are invalid"]
    if any(
        authorization.get(field) is not None
        for field in ("candidateRevision", "namedHuman", "authorizedAt")
    ) or any(
        authorization.get(field) is not False
        for field in (
            "claimCeilingAccepted",
            "publicationAuthorized",
            "releaseAuthorized",
        )
    ):
        return ["repository releaseAuthorization contains authority data"]
    return []


def _safe_https_locator(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def external_release_contract_errors(root: Path, acceptance: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidate = acceptance.get("candidateVerification")
    systems = candidate.get("requiredSystems") if isinstance(candidate, dict) else None
    if (
        not isinstance(candidate, dict)
        or set(candidate) != {"mode", "requiredSystems", "rule"}
        or candidate.get("mode") != "task-time-live-observation"
        or not isinstance(systems, dict)
        or not systems
        or any(
            not isinstance(system, str)
            or not system.strip()
            or not _safe_https_locator(locator)
            for system, locator in systems.items()
        )
        or not isinstance(candidate.get("rule"), str)
        or not candidate["rule"].strip()
    ):
        errors.append("acceptance.candidateVerification policy is invalid")
    errors.extend(
        repository_release_authorization_errors(acceptance.get("releaseAuthorization"))
    )
    public = acceptance.get("publicRelease")
    public_fields = {
        "mode", "tag", "releaseLocator", "releaseApi", "tagApi",
        "releaseNotes", "assetPolicy", "rule",
    }
    if (
        not isinstance(public, dict)
        or set(public) != public_fields
        or public.get("mode") != "task-time-live-github-observation"
        or not isinstance(public.get("tag"), str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", public["tag"])
        is None
        or any(
            not _safe_https_locator(public.get(field))
            for field in ("releaseLocator", "releaseApi", "tagApi")
        )
        or not isinstance(public.get("releaseNotes"), str)
        or not isinstance(public.get("assetPolicy"), str)
        or not public["assetPolicy"].strip()
        or not isinstance(public.get("rule"), str)
        or not public["rule"].strip()
    ):
        errors.append("acceptance.publicRelease policy is invalid")
    ceiling = acceptance.get("claimCeiling")
    claims: list[str] = []
    if isinstance(ceiling, dict):
        for field in ("finiteReleaseClaims", "notImplied"):
            values = ceiling.get(field)
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value for value in values
            ):
                errors.append(f"acceptance.claimCeiling.{field} is invalid")
            else:
                claims.extend(values)
    else:
        errors.append("acceptance.claimCeiling is invalid")
    notes = repository_relative_path(
        root, public.get("releaseNotes") if isinstance(public, dict) else None
    )
    try:
        if notes is None or notes.is_symlink() or not notes.is_file():
            raise OSError("release notes are not an owned regular file")
        text = notes.read_text(encoding="utf-8")
        if any(f"`{claim}`" not in text for claim in claims):
            errors.append("release notes do not expose the complete claim ceiling")
    except (OSError, UnicodeError) as exc:
        errors.append(f"release notes are invalid: {exc}")
    return errors
