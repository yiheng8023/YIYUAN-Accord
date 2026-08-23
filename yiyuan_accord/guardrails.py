from hashlib import sha256
import json
from pathlib import Path
import os
import re
import subprocess

from .identity import _exact, _nonempty_string, _safe_https_locator, _string_list
_AUTH_FIELDS = set((
    "state candidateRevision namedHuman authorizedAt claimCeilingAccepted "
    "publicationAuthorized releaseAuthorized"
).split())
PROCEDURE_FIELDS = "orderedGates candidateVerificationSystems assetPolicy surfaceMarkers rule".split()
CANDIDATE_SYSTEMS = set((
    "github-actions-ubuntu-latest github-actions-windows-latest "
    "github-actions-macos-latest codex-cloud"
).split())
RELEASE_SURFACES = (
    "AGENTS.md CONTEXT.md README.md README.zh-CN.md .github/workflows/validate.yml "
    "docs/architecture.md CONTRIBUTING.md docs/operations/CONTINUATION.md"
).split()
_COMMENT_NORMALIZED_WORKFLOW_SHA256 = (
    "b0938e16c68a347bc04690df990c9f4b740d9bb781d19b2ba3d3a8d3b8319948"
)
GATE_FIELDS = "id dependsOn acceptanceIds completionOperand condition".split()
GATE_SEQUENCE = (
    ("repository-candidate", None),
    ("exact-local-verification-and-review", "exactLocalVerificationAndReview"),
    ("exact-candidate-hosted-verification", "exactCandidateHostedVerification"),
    ("exact-human-release-authorization", "namedHumanReleaseAuthorization"),
    ("exact-tagged-public-release", "exactTaggedPublicRelease"),
    ("release-verification-and-cleanup", "releaseVerificationAndCleanup"),
)
EXTERNAL_COMPLETION_OPERANDS = tuple(
    operand for _, operand in GATE_SEQUENCE if operand
)
AUTHORIZATION_FIELDS = _AUTH_FIELDS | {"mode"}
MANIFEST_FIELDS = {
    "codex": set(
        "name version description author homepage repository license keywords skills interface".split()
    ),
    "claude-code": set(
        "$schema name version description author homepage repository license keywords skills".split()
    ),
}
CODEX_INTERFACE_FIELDS = set((
    "displayName shortDescription longDescription developerName category capabilities "
    "websiteURL defaultPrompt"
).split())
CODEX_METADATA_FIELDS = {
    "interface": set("display_name short_description default_prompt".split()),
    "policy": {"allow_implicit_invocation"},
}
_PROJECTION_FIELDS = set((
    "id packageId packageVersion packageSha256 manifest contract skill metadataFiles "
    "maxSkillBytes requiredSkillMarkers forbiddenPaths"
).split())
def repository_relative_path(root, locator):
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


def forbidden_path_present(path):
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return True


def known_task_residue(root):
    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        return ["<unreadable-root>"]
    residue = []
    residue_directories = {"__pycache__", ".tmp", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    for current, directories, files in os.walk(resolved_root, followlinks=False):
        base = Path(current)
        for name in tuple(directories):
            path = base / name
            relative = path.relative_to(resolved_root).as_posix()
            if name in residue_directories:
                residue.append(relative)
            if name == ".git" or name in residue_directories or path.is_symlink():
                directories.remove(name)
        for name in files:
            lowered_name = name.lower()
            if (
                lowered_name in {"error.log", ".coverage"}
                or lowered_name.endswith((".pyc", ".pyo"))
            ):
                residue.append((base / name).relative_to(resolved_root).as_posix())
    return sorted(residue)


def clean_git_checkout(root):
    try:
        top_level = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        ).strip()
        if Path(top_level).resolve(strict=True) != root.resolve(strict=True):
            return False
        status = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ],
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False
    return not status


def package_sha256(root, locators):
    digest = sha256()
    for locator in sorted(locators):
        digest.update(locator.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256((root / locator).read_bytes()).digest())
    return digest.hexdigest()


def codex_metadata_errors(path, skill_name):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"adapter codex metadata is unreadable: {exc}"]
    sections, current = {}, None
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
    decoded = {}
    for field in CODEX_METADATA_FIELDS["interface"]:
        try:
            value = json.loads(sections["interface"][field])
        except json.JSONDecodeError:
            return [f"adapter codex metadata interface.{field} is invalid"]
        if not isinstance(value, str) or not value.strip():
            return [f"adapter codex metadata interface.{field} is invalid"]
        decoded[field] = value
    if f"${skill_name}" not in decoded["default_prompt"]:
        return ["adapter codex metadata does not reference its Skill name"]
    if sections["policy"]["allow_implicit_invocation"] != "true":
        return ["adapter codex metadata implicit invocation policy is invalid"]
    return []


def manifest_shape_errors(
    adapter_id, manifest, identity, product_id, declared_prompt,
):
    errors = []
    prefix = f"adapter {adapter_id}"
    expected_fields = MANIFEST_FIELDS.get(adapter_id, set())
    if not _exact(manifest, expected_fields):
        errors.append(f"{prefix} manifest has unsupported fields or omissions")
    if any(not _nonempty_string(manifest.get(field)) for field in (
        "name", "version", "description", "homepage", "repository", "license", "skills",
    )):
        errors.append(f"{prefix} manifest required text is invalid")
    if manifest.get("skills") != "./skills/":
        errors.append(f"{prefix} manifest skills locator is invalid")
    if manifest.get("author") != {"name": f"{identity.get('displayName')} contributors"}:
        errors.append(f"{prefix} manifest author is not canonical")
    if manifest.get("license") != "Apache-2.0":
        errors.append(f"{prefix} manifest license is invalid")
    keywords = manifest.get("keywords")
    if (
        not isinstance(keywords, list) or not keywords
        or any(not _nonempty_string(item) for item in keywords)
        or product_id not in keywords or len(keywords) != len(set(keywords))
    ):
        errors.append(f"{prefix} manifest keywords are invalid")
    if adapter_id == "codex":
        interface = manifest.get("interface")
        if not _exact(interface, CODEX_INTERFACE_FIELDS):
            errors.append("adapter codex manifest interface fields are invalid")
        elif (
            any(not _nonempty_string(interface.get(field)) for field in (
                "displayName", "shortDescription", "longDescription", "developerName",
                "category", "websiteURL",
            ))
            or interface.get("displayName") != f"{identity.get('displayName')} for Codex"
            or interface.get("developerName") != f"{identity.get('displayName')} contributors"
            or interface.get("websiteURL") != identity.get("repository")
            or interface.get("capabilities") != ["Interactive", "Read"]
            or interface.get("defaultPrompt") != declared_prompt
            or not _string_list(declared_prompt)
            or any(len(value) > 128 for value in declared_prompt)
        ):
            errors.append("adapter codex manifest interface contract is invalid")
    elif adapter_id == "claude-code" and manifest.get("$schema") != (
        "https://json.schemastore.org/claude-code-plugin-manifest.json"
    ):
        errors.append("adapter claude-code manifest schema is invalid")
    return errors


def marketplace_errors(
    adapter_id, marketplace, manifest_name, expected_path,
):
    errors = []
    prefix = f"adapter {adapter_id}"
    entries = marketplace.get("plugins")
    if (
        not _exact(marketplace, {"name", "interface", "plugins"})
        or not _exact(marketplace.get("interface"), {"displayName"})
    ):
        errors.append(f"{prefix} marketplace shape is invalid")
    if not isinstance(entries, list) or len(entries) != 1:
        errors.append(f"{prefix} marketplace entry is not unique")
        return errors
    entry = entries[0]
    if not isinstance(entry, dict) or entry.get("name") != manifest_name:
        return errors + [f"{prefix} marketplace entry is not unique"]
    if not _exact(entry, {"name", "source", "policy", "category"}):
        errors.append(f"{prefix} marketplace entry shape is invalid")
    if entry.get("source") != {"source": "local", "path": expected_path}:
        errors.append(f"{prefix} marketplace source is invalid")
    if entry.get("policy") != {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }:
        errors.append(
            f"{prefix} marketplace policy must be AVAILABLE/ON_INSTALL"
        )
    return errors


def plugin_file_locators(root, plugin_root):
    resolved_root = root.resolve(strict=True)
    files = []
    for path in plugin_root.rglob("*"):
        if path.is_file() or path.is_symlink():
            files.append(path.relative_to(resolved_root).as_posix())
    return sorted(files)


def validate_projection_package(
    root, adapter_id, manifest_locator, contract_locator, skill_locator,
    metadata_locators,
):
    errors = []
    prefix = f"adapter {adapter_id}"
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
                errors.append(f"{prefix} metadata file is invalid: {locator}")
            elif adapter_id == "codex":
                errors.extend(codex_metadata_errors(path, Path(skill_locator).parent.name))
            else:
                errors.append(f"{prefix} does not admit metadata files")
    if not isinstance(manifest_locator, str):
        return None, errors
    plugin_root = repository_relative_path(
        root, Path(manifest_locator).parent.parent.as_posix()
    )
    if plugin_root is None or not plugin_root.is_dir():
        errors.append(f"{prefix} plugin root is invalid")
        return None, errors
    actual = plugin_file_locators(root, plugin_root)
    unexpected = sorted(set(actual) - set(declared))
    missing = sorted(set(declared) - set(actual))
    if unexpected:
        errors.append(
            f"{prefix} package contains undeclared files: {unexpected}"
        )
    if missing:
        errors.append(f"{prefix} package omits declared files: {missing}")
    try:
        digest = package_sha256(root, declared) if not missing else None
    except OSError:
        digest = None
        errors.append(f"{prefix} package identity is unavailable")
    return digest, errors


def validate_host_projection(
    root, projection, contract_ids, product_id, identity, errors, read_json,
    golden_tasks_file,
):
    initial_error_count = len(errors)
    adapter_id = projection.get("id")
    prefix = f"adapter {adapter_id}"
    expected_shape = _PROJECTION_FIELDS | (
        {"marketplace", "interfaceDefaultPrompt"} if adapter_id == "codex" else set()
    )
    if adapter_id not in {"codex", "claude-code"} or not _exact(projection, expected_shape):
        errors.append(f"{prefix} program projection shape is invalid")
    manifest_locator, marketplace_locator = projection.get("manifest"), projection.get("marketplace")
    contract_locator, skill_locator = projection.get("contract"), projection.get("skill")
    metadata = projection.get("metadataFiles")
    metadata_locators = metadata if isinstance(metadata, list) and all(
        isinstance(item, str) for item in metadata
    ) else []
    manifest = read_json(root, manifest_locator, errors) if isinstance(manifest_locator, str) else {}
    contract = read_json(root, contract_locator, errors) if isinstance(contract_locator, str) else {}
    skill_path = repository_relative_path(root, skill_locator)
    if skill_path is not None and not skill_path.is_file():
        skill_path = None
    expected_package = projection.get("packageId")
    expected_manifest = {
        "name": expected_package, "version": projection.get("packageVersion"),
        "homepage": identity.get("repository"), "repository": identity.get("repository"),
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            errors.append(f"{prefix} manifest {field} does not match declared identity")
    errors.extend(manifest_shape_errors(
        adapter_id, manifest, identity, product_id, projection.get("interfaceDefaultPrompt")
    ))
    if isinstance(marketplace_locator, str):
        marketplace = read_json(root, marketplace_locator, errors)
        if marketplace.get("name") != product_id or marketplace.get("interface") != {
            "displayName": identity.get("displayName")
        }:
            errors.append(f"{prefix} marketplace identity is not canonical")
        expected_path = (
            f"./{Path(manifest_locator).parent.parent.as_posix()}"
            if isinstance(manifest_locator, str) else None
        )
        errors.extend(marketplace_errors(
            adapter_id, marketplace, manifest.get("name"), expected_path
        ))
    expected_contract = {
        "schema": 1, "productId": product_id, "packageId": expected_package,
        "adapterId": adapter_id, "kernelIds": contract_ids["kernel"],
        "hostStandardIds": contract_ids["host"],
        "learnedFailureIds": contract_ids["lessons"],
        "goldenTasks": golden_tasks_file, "runtimeAdded": False,
        "requiresFixedHostVersion": False, "behaviorEvidenceState": "unverified",
    }
    if contract != expected_contract:
        errors.append(f"{prefix} contract does not match declared authority")
    behavior_state = contract.get("behaviorEvidenceState")

    skill_bytes = 0
    if skill_path is not None:
        skill_bytes = skill_path.stat().st_size
        max_bytes = projection.get("maxSkillBytes")
        if isinstance(max_bytes, int) and skill_bytes > max_bytes:
            errors.append(f"{prefix} Skill exceeds budget: {skill_bytes} > {max_bytes}")
        try:
            skill_text = skill_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{prefix} Skill is unreadable: {exc}")
            skill_text = ""
        parts = skill_text.split("---", 2)
        lines = parts[1].strip().splitlines() if len(parts) == 3 and not parts[0] else []
        pairs = [line.split(": ", 1) for line in lines if ": " in line]
        rows = dict(pairs)
        if (
            len(parts) != 3 or parts[0] or not parts[2].startswith("\n")
            or len(lines) != len(pairs) or len(rows) != len(lines)
            or set(rows) != {"name", "description"}
            or rows.get("name") != Path(skill_locator).parent.name
            or not _nonempty_string(rows.get("description"))
        ):
            errors.append(f"{prefix} Skill frontmatter identity is invalid")
        markers = projection.get("requiredSkillMarkers")
        for marker in markers if isinstance(markers, list) else []:
            if isinstance(marker, str) and marker not in skill_text:
                errors.append(f"{prefix} Skill omits marker {marker}")

    package_digest, package_errors = validate_projection_package(
        root, adapter_id, manifest_locator, contract_locator, skill_locator,
        metadata_locators,
    )
    errors.extend(package_errors)
    if package_digest != projection.get("packageSha256"):
        errors.append(f"{prefix} package digest is not approved by program")
    forbidden = projection.get("forbiddenPaths")
    for index, locator in enumerate(forbidden if isinstance(forbidden, list) else []):
        path = repository_relative_path(root, locator)
        if path is None:
            errors.append(
                f"{prefix} forbiddenPaths[{index}] is not a repository-relative path"
            )
        elif forbidden_path_present(path):
            errors.append(f"{prefix} forbidden path remains: {locator}")

    projection_identity = {}
    for field, locator in (
        ("manifestSha256", manifest_locator), ("marketplaceSha256", marketplace_locator),
        ("contractSha256", contract_locator), ("skillSha256", skill_locator),
    ):
        path = repository_relative_path(root, locator)
        if path is not None and path.is_file():
            projection_identity[field] = sha256(path.read_bytes()).hexdigest()
    if package_digest is not None:
        projection_identity["packageSha256"] = package_digest
    return {
        "id": adapter_id,
        "staticReady": len(errors) == initial_error_count,
        "behaviorEvidenceState": behavior_state,
        "skillBytes": skill_bytes,
        "manifest": manifest_locator,
        "marketplace": marketplace_locator,
        "contract": contract_locator,
        "skill": skill_locator,
        "metadataFiles": metadata_locators,
        "identity": projection_identity,
    }


def projection_observation_errors(
    observed, host_report, label, adapter_id,
):
    current = host_report.get("identity")
    if not isinstance(current, dict):
        return [f"{label} projection identity unavailable"]
    expected = {
        field: host_report[field]
        for field in ("manifest", "marketplace", "contract", "skill")
        if isinstance(host_report.get(field), str)
    } | current
    errors = []
    if observed.get("adapterId") != adapter_id:
        errors.append(f"{label} projection identity mismatch")
    for field, value in expected.items():
        if field not in observed:
            errors.append(f"{label} lacks current adapter {adapter_id} field {field}")
        elif observed[field] != value:
            errors.append(f"{label} {field} does not match current adapter {adapter_id}")
    return errors


def projection_evidence_binding_errors(
    root, acceptance, host_reports, read_json,
):
    errors = []
    criteria = acceptance.get("criteria")
    if not isinstance(criteria, list):
        return errors
    for criterion_index, criterion in enumerate(criteria):
        evidence = criterion.get("evidence") if isinstance(criterion, dict) else None
        if not isinstance(evidence, list):
            continue
        for evidence_index, item in enumerate(evidence):
            label = f"criteria[{criterion_index}].evidence[{evidence_index}]"
            if not isinstance(item, dict):
                continue
            locator = item.get("locator")
            observation = read_json(root, locator, []) if isinstance(locator, str) else {}
            if "bindsProjection" not in item:
                continue
            adapter_id = item.get("bindsProjection")
            if not isinstance(adapter_id, str) or not adapter_id.strip() or adapter_id not in host_reports:
                errors.append(f"{label}.bindsProjection is unknown")
                continue
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
    criterion_id, item, observation, task_mappings, label,
):
    errors = []
    if item.get("supportsCriterion") != criterion_id:
        errors.append(f"{label} does not support {criterion_id}")
        return False, errors
    decisions = observation.get("criterionDecisions")
    decision = decisions.get(criterion_id) if isinstance(decisions, dict) else None
    accepted = decision in {"accepted", "accepted-with-exclusion"}
    if decision not in {"accepted", "accepted-with-exclusion", "rejected"}:
        errors.append(f"{label} has no explicit {criterion_id} decision")
    claim = item.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        errors.append(f"{label} lacks a {criterion_id} evidence claim")
        accepted = False
    elif (
        not isinstance(observation.get("claimLimit"), dict)
        or claim != observation["claimLimit"].get("statement")
    ):
        errors.append(f"{label} claim must equal observation claimLimit.statement")
        accepted = False
    task_id = observation.get("taskId")
    if (
        isinstance(task_id, str)
        and task_id.strip()
        and criterion_id not in task_mappings.get(task_id, set())
    ):
        errors.append(f"{label} task {task_id} does not map to {criterion_id}")
    return accepted, errors


def _mapped_sequence(value, label, criterion_ids):
    if not isinstance(value, list) or not value or any(
        not isinstance(item, dict) for item in value
    ):
        return [], [], [f"{label} must be a non-empty object list"]
    errors, item_ids, coverage = [], [], set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item_id = item.get("id")
        if _nonempty_string(item_id):
            item_ids.append(item_id)
        else:
            errors.append(f"{item_label}.id must be non-empty")
        mapped = _string_list(item.get("acceptanceIds"))
        if not mapped or not set(mapped).issubset(criterion_ids):
            errors.append(f"{item_label}.acceptanceIds is invalid")
        else:
            coverage.update(mapped)
    if len(item_ids) != len(set(item_ids)):
        errors.append(f"{label} ids must be unique")
    if coverage != criterion_ids:
        errors.append(f"{label} must map every criterion")
    return value, item_ids, errors


def closeout_sequence_errors(
    work_item, criterion_ids,
):
    sequence, _, errors = _mapped_sequence(
        work_item.get("closeoutSequence"), "closeoutSequence", criterion_ids
    )
    states = []
    for index, stage in enumerate(sequence):
        stage_id = stage.get("id")
        state = stage.get("state")
        if state not in {"completed", "active", "pending"}:
            errors.append(f"closeoutSequence[{index}].state is invalid")
        else:
            states.append(state)
        stop = stage.get("stopCondition")
        if not isinstance(stop, str) or not stop.startswith(f"[{stage_id}] "):
            errors.append(f"closeoutSequence[{index}].stopCondition is not bound to its stage")
    terminal = work_item.get("state") == "completed"
    if terminal and any(state != "completed" for state in states):
        errors.append("completed work item closeoutSequence must be completed")
    elif not terminal and states.count("active") != 1:
        errors.append("active work item closeoutSequence must contain one active stage")
    ranks = {"completed": 0, "active": 1, "pending": 2}
    if states and [ranks[state] for state in states] != sorted(
        ranks[state] for state in states
    ):
        errors.append("work item closeoutSequence order is invalid")
    return errors


def release_procedure_errors(root, procedure, criterion_ids, prompt, goal_digest):
    if not _exact(procedure, PROCEDURE_FIELDS):
        return ["program.releaseProcedure is invalid"]
    if not isinstance(procedure.get("rule"), str) or not procedure["rule"].strip():
        return ["program.releaseProcedure.rule must be non-empty"]
    systems = procedure.get("candidateVerificationSystems")
    if (
        not isinstance(systems, dict)
        or set(systems) != CANDIDATE_SYSTEMS
        or any(not isinstance(name, str) or not name or not _safe_https_locator(locator)
               for name, locator in systems.items())
    ):
        return ["program.releaseProcedure.candidateVerificationSystems is invalid"]
    if procedure.get("assetPolicy") != "no-attached-assets":
        return ["program.releaseProcedure.assetPolicy must be no-attached-assets"]
    surfaces = procedure.get("surfaceMarkers")
    if not _exact(surfaces, RELEASE_SURFACES):
        return ["program.releaseProcedure.surfaceMarkers is invalid"]
    for locator, markers in surfaces.items():
        try:
            raw = repository_relative_path(root, locator).read_text(encoding="utf-8")
        except (AttributeError, OSError, UnicodeError):
            raw = ""
        text = " ".join(raw.split())
        if (not _string_list(markers) or any(
            " ".join(marker.split()) not in text for marker in markers
        ) or locator == ".github/workflows/validate.yml" and sha256(
            re.sub(r"\s+#.*$", "", raw, flags=re.M).encode()
        ).hexdigest() != _COMMENT_NORMALIZED_WORKFLOW_SHA256):
            return [f"derived surface markers or structure are invalid in {locator}"]
    gates = procedure.get("orderedGates")
    if not isinstance(gates, list) or len(gates) != len(GATE_SEQUENCE) or any(
        not _exact(gate, GATE_FIELDS) for gate in gates
    ):
        return ["program.releaseProcedure.orderedGates is invalid"]
    gates, _, errors = _mapped_sequence(gates, "releaseProcedure.orderedGates", criterion_ids)
    for index, gate in enumerate(gates):
        label = f"releaseProcedure.orderedGates[{index}]"
        gate_id = gate.get("id")
        expected_id, expected_operand = GATE_SEQUENCE[index]
        if gate_id != expected_id or gate.get("completionOperand") != expected_operand:
            errors.append(f"{label} does not match the required release gate sequence")
        expected_dependency = [] if index == 0 else [gates[index - 1].get("id")]
        if gate.get("dependsOn") != expected_dependency:
            errors.append(f"{label}.dependsOn must name only the previous gate")
        if not isinstance(gate.get("condition"), str) or not gate["condition"].strip():
            errors.append(f"{label}.condition must be non-empty")
    prompt = prompt if isinstance(prompt, dict) else {}
    if prompt.get("releaseGateIds") != [
        gate_id for gate_id, _ in GATE_SEQUENCE
    ]:
        errors.append("program.goalModePrompt.releaseGateIds must match releaseProcedure")
    objective = prompt.get("objective", "")
    if (
        not isinstance(objective, str)
        or not isinstance(goal_digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", goal_digest)
        or sha256(objective.encode("utf-8")).hexdigest() != goal_digest
    ):
        errors.append("program.goalModePrompt objective is not the canonical projection")
    work_order = " → ".join(prompt.get("workStageIds", []))
    release_order = " → ".join(gate_id for gate_id, _ in GATE_SEQUENCE)
    if not work_order or work_order not in objective or release_order not in objective:
        errors.append("program.goalModePrompt objective does not preserve release gate order")
    return errors


def repository_release_authorization_errors(authorization):
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
    if not _exact(authorization, AUTHORIZATION_FIELDS) or authorization.get(
        "mode"
    ) != "task-time-human-authority":
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


def external_release_contract_errors(root, acceptance):
    errors = []
    candidate = acceptance.get("candidateVerification")
    systems = candidate.get("requiredSystems") if isinstance(candidate, dict) else None
    if (
        not _exact(candidate, {"mode", "requiredSystems", "rule"})
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
        "releaseNotes", "releaseNotesSha256", "assetPolicy", "rule",
    }
    if (
        not _exact(public, public_fields)
        or public.get("mode") != "task-time-live-github-observation"
        or not isinstance(public.get("tag"), str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", public["tag"])
        is None
        or any(
            not _safe_https_locator(public.get(field))
            for field in ("releaseLocator", "releaseApi", "tagApi")
        )
        or not isinstance(public.get("releaseNotes"), str)
        or public.get("assetPolicy") != "no-attached-assets"
        or not isinstance(public.get("releaseNotesSha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", public["releaseNotesSha256"]) is None
        or not isinstance(public.get("rule"), str)
        or not public["rule"].strip()
    ):
        errors.append("acceptance.publicRelease policy is invalid")
    ceiling = acceptance.get("claimCeiling")
    claims, groups, retained = [], [], []
    if _exact(ceiling, {
        "finiteReleaseClaims", "notImplied", "retainedBehaviorExclusions",
    }):
        for field in ("finiteReleaseClaims", "notImplied"):
            values = _string_list(ceiling.get(field))
            if not values:
                errors.append(f"acceptance.claimCeiling.{field} is invalid")
            else:
                groups.append(values)
                claims.extend(values)
        retained = ceiling.get("retainedBehaviorExclusions")
        if _string_list(retained) is None or retained != sorted(retained):
            errors.append("acceptance.claimCeiling.retainedBehaviorExclusions is invalid")
        if len(groups) == 2 and set(groups[0]) & set(groups[1]):
            errors.append("acceptance.claimCeiling claims and exclusions overlap")
    else:
        errors.append("acceptance.claimCeiling is invalid")
    notes = repository_relative_path(
        root, public.get("releaseNotes") if isinstance(public, dict) else None
    )
    try:
        if notes is None or notes.is_symlink() or not notes.is_file():
            raise OSError("release notes are not an owned regular file")
        text = notes.read_text(encoding="utf-8")
        if sha256(notes.read_bytes()).hexdigest() != public.get("releaseNotesSha256"):
            errors.append("release notes digest does not match public release contract")
        if any(f"`{claim}`" not in text for claim in claims):
            errors.append("release notes do not expose the complete claim ceiling")
        marker = f"`retainedBehaviorExclusions={json.dumps(retained, separators=(',', ':'))}`"
        if marker not in text:
            errors.append("release notes do not expose retained behavior exclusions")
    except (OSError, UnicodeError) as exc:
        errors.append(f"release notes are invalid: {exc}")
    return errors
