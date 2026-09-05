"""Development-contract conformance, not a runtime or a behavior evaluator.

The post-release successor has its own semantics and unverified functional
obligations. Historical validation remains separate and is not promoted by
this check. These versioned checks bind their phase, not every future form.
"""

from pathlib import Path
from datetime import datetime
import re
from urllib.parse import urlsplit

from .identity import _bounded_git_bytes, _bounded_regular_bytes, _strict_json_object


DEVELOPMENT_FILE = "product/development.json"
PLAN_FILE = "docs/operations/PLAN-v3.2.md"
_PREDECESSOR = re.compile(
    r"([0-9a-f]{40}):product/program\.json#/maintenanceCycle/closeoutSnapshot"
)
_BASELINE_FILES = (
    "product/constitution.json", "product/program.json",
    "product/acceptance.json", "product/reshaping-guidance.json",
    "evals/golden-tasks.json",
)
_DUTY_FIELDS = set(
    "id name goldenTasks activationWhen requiredOutcome normalEntry "
    "failureOracle dependsOn assessment evidence".split()
)
_SUCCESS_STATES = {
    "responsibilities-accounted", "function-verified", "outcome-complete",
    "safely-stopped", "value-supported",
}
# Coverage of the approved source slice, not a universal or permanent catalogue.
_BASELINE_DUTIES = set(
    "goal-authority-correction environment-and-self-exposure research-learning-and-reuse "
    "relations-routing-and-form execution-configuration-and-code premise-and-consistency "
    "correction-and-evolution recovery-and-rollback context-and-task-continuity "
    "resources-and-cleanup package-lifecycle native-replacement-and-retirement "
    "verification-and-value".split()
)


def development_is_declared(root):
    root = Path(root)
    path = root / DEVELOPMENT_FILE
    instructions, state = _bounded_regular_bytes(root / "AGENTS.md")
    return (path.exists() or path.is_symlink()
            or state is None and DEVELOPMENT_FILE.encode() in instructions)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _strings(value, *, empty=False):
    return (isinstance(value, list) and (empty or bool(value))
            and all(_text(item) for item in value)
            and len(value) == len(set(value)))


def delivery_adapter_contract(adapter_id, package_id):
    """Describe this development package, not a mandatory product mechanism."""
    return {
        "schema": 2, "productId": "yiyuan-accord", "packageId": package_id,
        "adapterId": adapter_id, "entry": "host-skill",
        "ordinaryPrerequisites": [],
        "optionalContinuityHint": "session-start-invalidation",
        "optionalHintDependency": "host-path-node",
        "persistentProcessAdded": False, "persistentStateAdded": False,
        "requiresFixedHostVersion": False, "behaviorEvidenceState": "unverified",
    }


def _entry_surface_errors(entries):
    """Validate a revisable review inventory, never cross-entry admission."""
    if not isinstance(entries, dict):
        return ["entry surface review must be an object"]
    errors = []
    if not _text(entries.get("rule")):
        errors.append("entry surface review needs an attribution rule")
    try:
        captured = datetime.fromisoformat(entries.get("reviewedAt", "").replace("Z", "+00:00"))
        if captured.utcoffset() is None:
            raise ValueError("undated")
    except (ValueError, TypeError, AttributeError):
        errors.append("entry surface review needs a timezone-bound date")
    rows = entries.get("rows")
    if not isinstance(rows, list) or not rows:
        return errors + ["entry surface rows are missing"]
    domains = {"codex": {"learn.chatgpt.com", "developers.openai.com", "help.openai.com"},
               "claude-code": {"code.claude.com", "platform.claude.com",
                               "support.claude.com", "academy.claude.com"}}
    ids, hosts = set(), set()
    for row in rows:
        if not isinstance(row, dict) or not all(_text(row.get(field)) for field in (
                "id", "host", "name", "officialSource", "execution", "environment", "observation")):
            errors.append("entry surface must bind execution, environment, source and observation")
            continue
        if row["id"] in ids:
            errors.append("entry surface ids must be unique")
        ids.add(row["id"])
        hosts.add(row["host"])
        try:
            url = urlsplit(row["officialSource"])
            official = (url.scheme == "https" and url.hostname in domains.get(row["host"], set())
                        and url.username is None and url.password is None)
        except ValueError:
            official = False
        if not official:
            errors.append("entry surface needs the relevant official family source")
        if row.get("currentEffect") != "unverified":
            errors.append("shared engine, documentation or installation is not entry effect evidence")
    if hosts != set(domains):
        errors.append("entry review must cover the two bound families without adding vendors")
    return errors


def development_contract_errors(contract, golden_task_ids):
    """Check structure/coverage; prose and real effects still require review."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def section(name, text_fields=()):
        value = contract.get(name)
        if not isinstance(value, dict):
            errors.append(f"{name} must be an object")
            return {}
        for field in text_fields:
            require(_text(value.get(field)), f"{name}.{field} must be nonempty text")
        return value

    if not isinstance(contract, dict):
        return ["development contract must be an object"]
    schema = contract.get("schema")
    require(schema == "yiyuan-accord-development/v2",
            "unsupported development schema")
    require(contract.get("productId") == "yiyuan-accord", "product identity mismatch")
    phase = "whole-system-optimization-and-functional-closure"
    require(contract.get("phase") == phase
            and contract.get("status") == "in-development", "source-phase boundary mismatch")
    require(bool(_PREDECESSOR.fullmatch(contract.get("predecessorSnapshot", "")))
            if isinstance(contract.get("predecessorSnapshot"), str) else False,
            "predecessor must be an immutable closed-snapshot locator")
    require(_text(contract.get("baselineRole")), "baseline role must be explicit")
    boundary = section("changeBoundary", ("rule",))
    require(_strings(boundary.get("allowedPaths")), "source change boundary is missing")
    budget = boundary.get("complexityBudget")
    require(isinstance(budget, dict)
            and type(budget.get("maxProductCodeAndTestBytes")) is int
            and budget["maxProductCodeAndTestBytes"] > 0
            and type(budget.get("maxTrackedFiles")) is int
            and budget["maxTrackedFiles"] > 0
            and _text(budget.get("rationale")), "phase-local complexity rationale is missing")
    authority = section("authority", ("basis", "rule"))
    for field in ("scope", "notGranted"):
        require(_strings(authority.get(field)), f"authority.{field} must be explicit")
    scope = authority.get("scope")
    granted = {
        "source-semantics", "full-function-acceptance-mapping",
        "local-contract-validation", "matching-navigation-and-glossary",
    }
    granted.update({"whole-system-optimization", "existing-host-functional-closure", "next-version-development",
                    "controlled-existing-host-evaluation", "conditional-v3.2-release"})
    release = authority.get("conditionalRelease")
    require(isinstance(release, dict) and release.get("target") == "3.2.0"
            and release.get("decision") == "user-authorized-after-acceptance"
            and release.get("ready") is False
            and _strings(release.get("conditions")) and _text(release.get("rule"))
            and "all-in-scope-changes-committed-and-exact-candidate-pushed" in release["conditions"],
            "conditional publication authority is not present readiness")
    cycle = section("cycle", ("id", "scopeRule", "sourceDecision"))
    require(isinstance(cycle.get("targetVersion"), str)
            and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", cycle["targetVersion"]) is not None
            and cycle.get("versionState") == "development-target-not-published",
            "a development version target is not a published version")
    require(cycle.get("existingHosts") == ["codex", "claude-code"]
            and cycle.get("additionalHostAdaptation") == "deferred",
            "preserve existing hosts and defer additional adaptation")
    delivery = section("delivery", ("rule",))
    version = delivery.get("version")
    require(isinstance(version, str) and isinstance(cycle.get("targetVersion"), str)
            and re.fullmatch(re.escape(cycle["targetVersion"]) + r"-dev\.[1-9][0-9]*", version) is not None,
            "delivery must identify an unpublished development package")
    projections = delivery.get("hostProjections")
    require(isinstance(projections, list) and len(projections) == 2
            and all(isinstance(item, dict) and isinstance(item.get("id"), str)
                    and item.get("packageVersion") == version for item in projections)
            and {item["id"] for item in projections} == {"codex", "claude-code"},
            "current delivery must bind both existing host packages")
    optimization = section("systemOptimization", ("rule",))
    require(optimization.get("aggregation") == "all-applicable-floors-then-contextual-tradeoffs",
            "required system floors cannot be offset by an average score")
    axes = optimization.get("qualityAxes")
    required_axes = {
        "compliance-and-safety", "functional-coverage", "normal-entry-integration",
        "recovery-and-lifecycle", "change-adaptation", "evidence-integrity",
        "user-burden-and-interference", "maintainability-and-resource-cost",
    }
    require(isinstance(axes, list) and len(axes) == len(required_axes)
            and all(isinstance(axis, dict) and _text(axis.get("id"))
                    and _text(axis.get("floor"))
                    and axis.get("assessment") == "unverified" for axis in axes)
            and {axis.get("id") for axis in axes} == required_axes,
            "system quality coverage or unverified claim boundary is invalid")
    environment = section("environmentControl", (
        "productCommitment", "evaluationRule", "handlingRule", "selfUseBoundary", "driftRule",
    ))
    require(environment.get("cleanHostRequiredForProduct") is False
            and _strings(environment.get("factors")),
            "controlled evaluation cannot impose a clean-host product precondition")
    arms = environment.get("arms")
    require(isinstance(arms, list) and len(arms) == 3
            and all(isinstance(arm, dict) and _text(arm.get("id"))
                    and _text(arm.get("when")) and _text(arm.get("boundary")) for arm in arms)
            and {arm["id"] for arm in arms} == {
                "native-control", "deliverable-composition", "controlled-interference",
            }, "evaluation attribution and adaptive operation must remain distinct")
    require(_strings(scope) and set(scope) == granted,
            "phase approval cannot grant additional execution scope")

    source = section("source", ("purpose", "hypothesis", "bootstrapBoundary", "boundCommitment"))
    invariants = source.get("globalInvariants")
    require(isinstance(invariants, list) and len(invariants) == 1
            and isinstance(invariants[0], dict)
            and invariants[0].get("id") == "compliance"
            and invariants[0].get("scope") == "global"
            and _text(invariants[0].get("meaning")),
            "only the compliance boundary is globally invariant in this source contract")
    states = source.get("successStates")
    require(isinstance(states, dict) and set(states) == _SUCCESS_STATES
            and all(_text(value) for value in states.values()),
            "accounting, function, outcome, safe stop and value must remain distinct")
    require(_strings(source.get("variables")), "source variables must be explicit")

    applicability = section("applicability", ("unknown", "conflict", "representation"))
    classes = applicability.get("classes")
    require(isinstance(classes, dict) and set(classes) == {"compliance", "commitment", "strategy"}
            and all(_text(value) for value in classes.values()),
            "global compliance, bound commitments and conditional strategies must be distinct")
    require(_strings(applicability.get("strategyBinding")), "strategy applicability binding is missing")

    implementation = section("implementation", ("rule", "triggerRule", "nativeRule", "reconstructionRule", "runtimeRequirement"))
    modes = implementation.get("modes")
    require(_strings(modes) and set(modes) == {
        "accord-contained", "agent-native", "accord-agent-composed",
    }, "all three implementation modes must remain eligible")
    require(implementation.get("formNeutral") is True
            and implementation.get("runtimeEligible") is True
            and implementation.get("mandatoryMechanisms") == [],
            "form neutrality cannot require a Hook/core or exclude a runtime")
    require(implementation.get("selectionOrder") == [
        "compliance-and-authority", "full-bound-functional-and-quality-sufficiency",
        "total-lifecycle-cost-and-context-fit",
    ], "functional sufficiency must precede cost optimization")
    require(_strings(implementation.get("effectChain")), "effect chain is missing")
    model_route = implementation.get("modelSelection")
    require(isinstance(model_route, dict)
            and model_route.get("roles") == ["main-agent", "subagent"]
            and all(_text(model_route.get(field)) for field in (
                "trigger", "selection", "authority", "nativeReplacement", "verification", "failureOracle",
            )), "model selection must bind main/subagent needs, native coverage, authority and execution evidence")

    principles = section("supportingPrinciples", (
        "precondition", "subtraction", "restraint", "fallback", "gapFilling", "activation",
    ))
    require(principles.get("class") == "strategy",
            "subtraction, restraint, fallback and gap filling are conditional strategies")

    acceptance = section("acceptance", ("coverageRule", "executionBoundary", "historicalEvidenceRule"))
    require(_strings(acceptance.get("evidenceUnit")), "per-duty evidence binding is missing")
    duties = acceptance.get("duties")
    if not isinstance(duties, list) or not duties:
        errors.append("acceptance duties must be a nonempty list")
        duties = []
    ids, covered, edges = set(), set(), {}
    for duty in duties:
        if not isinstance(duty, dict) or set(duty) != _DUTY_FIELDS:
            errors.append("duty shape is invalid")
            continue
        duty_id = duty.get("id")
        if not _text(duty_id) or duty_id in ids:
            errors.append("duty ids must be nonempty and unique")
            continue
        ids.add(duty_id)
        for field in ("name", "activationWhen", "requiredOutcome", "normalEntry", "failureOracle"):
            require(_text(duty.get(field)), f"{duty_id}.{field} is missing")
        tasks = duty.get("goldenTasks")
        if not _strings(tasks) or not set(tasks) <= set(golden_task_ids):
            errors.append(f"{duty_id} has invalid Golden Task mappings")
        else:
            covered.update(tasks)
        dependencies = duty.get("dependsOn")
        if not _strings(dependencies, empty=True):
            errors.append(f"{duty_id} dependencies are invalid")
        else:
            edges[duty_id] = set(dependencies)
        require(duty.get("assessment") == "unverified" and duty.get("evidence") == [],
                f"{duty_id}: source mapping cannot promote historical evidence or functional success")
    retired_ids = set()
    require(_text(acceptance.get("functionReview")), "function necessity review is missing")
    retired = acceptance.get("retiredDuties")
    require(isinstance(retired, list), "retired responsibilities must be explicitly accounted for")
    for item in retired if isinstance(retired, list) else []:
        if (not isinstance(item, dict) or not _text(item.get("id"))
                or not _text(item.get("reason")) or not _text(item.get("acceptanceChange"))
                or not _strings(item.get("goldenTasks"))):
            errors.append("retirement requires a necessity decision and changed acceptance mapping")
            continue
        require(item["id"] not in ids | retired_ids, "active and retired responsibilities overlap")
        require(set(item["goldenTasks"]) <= set(golden_task_ids), "retirement task mapping is invalid")
        retired_ids.add(item["id"])
        covered.update(item["goldenTasks"])
    require(covered == set(golden_task_ids), "historical Golden Task disposition is incomplete")
    require(_BASELINE_DUTIES <= ids | retired_ids, "functional responsibility coverage or disposition is incomplete")
    require(all(deps <= ids for deps in edges.values()), "duty dependency is unresolved")
    capability_map = section("capabilityMap", (
        "representation", "refreshRule", "allocationRule", "runtimeGap",
    ))
    errors.extend(_entry_surface_errors(capability_map.get("entrySurfaces")))
    require(capability_map.get("scope") == "existing-host-development-review-not-runtime-admission",
            "capability inventory cannot establish runtime admission")
    try:
        captured = datetime.fromisoformat(capability_map.get("reviewedAt", "").replace("Z", "+00:00"))
        require(captured.utcoffset() is not None, "capability snapshot must have a timezone")
    except (ValueError, TypeError, AttributeError):
        errors.append("capability snapshot needs a dated source review")
    observations = capability_map.get("localObservations")
    observation_ids = set()
    for observation in observations if isinstance(observations, list) else []:
        if (not isinstance(observation, dict) or not all(_text(observation.get(field))
                for field in ("id", "host", "subject", "method", "finding", "claimLimit"))):
            errors.append("capability observation must bind subject, method and claim limit")
            continue
        require(observation["id"] not in observation_ids
                and observation["host"] in ("codex", "claude-code"), "capability observation identity is invalid")
        observation_ids.add(observation["id"])
    require(isinstance(observations, list) and bool(observation_ids), "capability local observations are missing")
    native = capability_map.get("native")
    native_ids = set()
    for capability in native if isinstance(native, list) else []:
        if (not isinstance(capability, dict) or not all(_text(capability.get(field))
                for field in ("id", "host", "name", "officialSource", "surface", "conditions"))):
            errors.append("native capability must bind its surface, source and conditions")
            continue
        require(capability["id"] not in native_ids, "native capability ids must be unique")
        native_ids.add(capability["id"])
        require(capability.get("layer") in ("model", "host-runtime", "model-api-composition"),
                "model, host runtime and API composition must remain distinct")
        domains = {"codex": {"learn.chatgpt.com", "developers.openai.com"},
                   "claude-code": {"code.claude.com", "platform.claude.com"}}
        try:
            url = urlsplit(capability["officialSource"])
            official = (url.scheme == "https" and url.hostname in domains.get(capability["host"], set())
                        and url.username is None and url.password is None)
        except ValueError:
            official = False
        require(official, "native capability needs the relevant official host source")
        refs = capability.get("localObservationIds")
        require(_strings(refs, empty=True) and set(refs) <= observation_ids
                and all(observation.get("host") == capability["host"]
                        for observation in observations if isinstance(observation, dict)
                        and observation.get("id") in refs),
                "native capability observation reference is unresolved")
        require(capability.get("currentEffect") == "unverified",
                "documentation or interface presence cannot establish current effects")
    require(isinstance(native, list) and bool(native_ids), "native capability review is missing")
    mapped_duties = set()
    for row in capability_map.get("accord", []) if isinstance(capability_map.get("accord"), list) else []:
        if (not isinstance(row, dict) or not all(_text(row.get(field))
                for field in ("dutyId", "role", "nextProbe"))):
            errors.append("Accord capability mapping needs a duty, role and next effect probe")
            continue
        require(row["dutyId"] not in mapped_duties, "duplicate Accord capability duty")
        mapped_duties.add(row["dutyId"])
        require(_strings(row.get("nativeIds"), empty=True) and set(row["nativeIds"]) <= native_ids,
                "Accord capability mapping has an unresolved native reference")
        require(row.get("assessment") == "unverified", "capability mapping is not functional acceptance")
    require(mapped_duties == ids, "capability matrix must account for all current duties")
    require(isinstance(model_route, dict) and _strings(model_route.get("capabilityRefs"))
            and set(model_route["capabilityRefs"]) <= native_ids,
            "model selection must reference the shared capability facts")
    stages = optimization.get("workSequence")
    require(isinstance(stages, list) and bool(stages),
            "development work sequence is missing")
    mapped, stage_ids = set(), set()
    for stage in stages if isinstance(stages, list) else []:
        if (not isinstance(stage, dict)
                or not all(_text(stage.get(field)) for field in ("id", "title", "procedure", "exit"))
                or not _strings(stage.get("duties"))):
            errors.append("plan step must map procedure and acceptance to responsibilities")
            continue
        require(stage["id"] not in stage_ids, "plan step ids must be unique")
        stage_ids.add(stage["id"])
        require(set(stage["duties"]) <= ids, "plan step refers to an unknown responsibility")
        require(stage.get("state") in ("pending", "active", "implemented-local-unreleased"),
                "plan progress cannot claim functional or release completion")
        mapped.update(stage["duties"])
    require(mapped == ids, "plan, process and acceptance must cover every responsibility")
    scenarios = environment.get("adaptationScenarios")
    require(isinstance(scenarios, list) and bool(scenarios), "dynamic adaptation acceptance is missing")
    for scenario in scenarios if isinstance(scenarios, list) else []:
        require(isinstance(scenario, dict)
                and all(_text(scenario.get(field)) for field in (
                    "id", "trigger", "requiredEffect", "failureOracle",
                )) and _strings(scenario.get("duties"))
                and set(scenario["duties"]) <= ids,
                "adaptation scenario must bind trigger, effect, failure and responsibilities")
    # This is an implementation-order view, not a ban on runtime feedback loops.
    pending = dict(edges)
    while pending:
        ready = {key for key, deps in pending.items() if not deps & pending.keys()}
        if not ready:
            errors.append("implementation-order dependency cycle")
            break
        pending = {key: deps for key, deps in pending.items() if key not in ready}

    change = section("changePolicy", ("rule", "versionRule", "replacementRule", "sourceRevisionRule"))
    require(_strings(change.get("materialVariables")), "change-dependent revalidation is missing")
    section("nextBoundary", ("work", "requires"))
    ceiling = section("claimCeiling")
    require(ceiling.get("localContractOnly") is True
            and ceiling.get("functionalCompletion") is False
            and ceiling.get("currentHostBehavior") == "unverified"
            and ceiling.get("incrementalValue") == "unverified"
            and ceiling.get("candidateEligible") is False
            and ceiling.get("releaseIntent") == "conditional-v3.2-release-after-acceptance",
            "source-phase checks cannot establish behavior, value or release eligibility")
    return errors


def _inspect_development(root):
    """Return conformance and the same source object that was checked."""
    root = Path(root)
    errors, contract, golden_ids, changed_paths = [], {}, [], []
    try:
        data, state = _bounded_regular_bytes(root / DEVELOPMENT_FILE)
        if state is not None:
            raise ValueError(f"development source is {state}")
        contract = _strict_json_object(data.decode("utf-8"))
        match = _PREDECESSOR.fullmatch(contract.get("predecessorSnapshot", ""))
        if match is None:
            raise ValueError("invalid predecessor locator")
        revision = match[1]
        _bounded_git_bytes(root, ("merge-base", "--is-ancestor", revision, "HEAD"))
        for locator in _BASELINE_FILES:
            current, state = _bounded_regular_bytes(root / locator)
            previous = _bounded_git_bytes(root, ("show", f"{revision}:{locator}"))
            if state is not None or current != previous:
                errors.append(f"historical baseline changed: {locator}")
            if locator == "product/program.json":
                snapshot = _strict_json_object(previous.decode("utf-8"))["maintenanceCycle"]["closeoutSnapshot"]
                if snapshot.get("state") != "closed":
                    errors.append("predecessor snapshot is not closed")
            if locator == "evals/golden-tasks.json":
                golden_ids = [task["id"] for task in _strict_json_object(previous.decode("utf-8"))["tasks"]]
        errors.extend(development_contract_errors(contract, golden_ids))
        if not errors:
            plan, state = _bounded_regular_bytes(root / PLAN_FILE)
            if state is not None or plan.decode("utf-8").replace("\r\n", "\n") != render_development_plan(contract):
                errors.append("visible plan is missing or out of sync with the development contract")
        changed = _bounded_git_bytes(root, (
            "diff", "--name-only", "-z", "--no-renames", "--no-ext-diff", revision, "--",
        )) + _bounded_git_bytes(root, ("ls-files", "--others", "--exclude-standard", "-z"))
        changed_paths = sorted(set(part.decode("utf-8") for part in changed.split(b"\0") if part))
        boundary = contract.get("changeBoundary")
        allowed = boundary.get("allowedPaths") if isinstance(boundary, dict) else None
        if not _strings(allowed) or set(changed_paths) - set(allowed):
            errors.append("observed changes exceed the development implementation boundary")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        errors.append(f"development source cannot be verified: {exc}")
    acceptance = contract.get("acceptance")
    duties = acceptance.get("duties") if isinstance(acceptance, dict) else None
    report = {
        "valid": not errors,
        "scope": "development-source-conformance-only",
        "phase": contract.get("phase"),
        "predecessorSnapshot": contract.get("predecessorSnapshot"),
        "historicalEvidenceRevision": (match[1] if not errors else None),
        "changedPaths": changed_paths,
        "complexityBudget": (contract.get("changeBoundary", {}).get("complexityBudget")
                             if isinstance(contract.get("changeBoundary"), dict) else None),
        "dutiesMapped": len(duties) if isinstance(duties, list) else 0,
        "goldenTasksCovered": len(golden_ids) if not errors else None,
        "functionalCompletion": False,
        "currentHostBehavior": "unverified",
        "incrementalValue": "unverified",
        "candidateEligible": False,
        "releaseIntent": (contract["claimCeiling"]["releaseIntent"] if not errors else None),
        "errors": errors,
    }
    return report, contract


def verify_development(root):
    """Verify the active development source plus its unchanged predecessor data."""
    return _inspect_development(root)[0]


def render_development_plan(contract):
    """Derived human view; the contract remains the only editable progress source."""
    states = {"pending": "待开展", "active": "进行中", "implemented-local-unreleased": "本地实现，未发布"}
    duties = {item["id"]: item for item in contract["acceptance"]["duties"]}
    lines = ["# YIYUAN Accord 3.2 开发计划与进度", "",
             "由 `product/development.json` 派生；修改源数据后同步本页，校验会拒绝不一致。", "",
             "当前为未冻结的开发基线；目标是完成验收后发布新的 3.2，不改写 3.1。",
             "动态自适应是原有核心承诺；驱动宿主实现必要结果，按证据保留、合并、删除或补强，暂缓增加宿主适配。", "",
             "## 工序与验收映射", "",
             "| 工序 | 当前进度 | 执行步骤 | 验收出口 |", "|---|---|---|---|"]
    for stage in contract["systemOptimization"]["workSequence"]:
        lines.append(f"| {stage['title']} | {states[stage['state']]} | {stage['procedure']} | {stage['exit']} |")
    lines += ["", "## 完整职责覆盖", "",
              contract["acceptance"]["coverageRule"], "",
              "| 职责 | 所属工序 | 历史需求与反例参考 |", "|---|---|---|"]
    for duty_id, duty in duties.items():
        stages = "、".join(stage["title"] for stage in contract["systemOptimization"]["workSequence"]
                          if duty_id in stage["duties"])
        lines.append(f"| {duty['name']} | {stages} | {', '.join(duty['goldenTasks'])} |")
    for retired in contract["acceptance"]["retiredDuties"]:
        lines.append(f"| {retired['id']}（已处置） | {retired['reason']}；{retired['acceptanceChange']} | {', '.join(retired['goldenTasks'])} |")
    capability_map = contract["capabilityMap"]
    entries = capability_map["entrySurfaces"]
    lines += ["", "## 宿主家族与入口边界", "",
              f"入口资料核对时间：`{entries['reviewedAt']}`。以下是开发盘点，不是各入口已适配或验收通过。", "",
              entries["rule"], "",
              "| 入口 / 官方来源 | 执行位置 | 环境与权限边界 | 当前观察与未实测项 |",
              "|---|---|---|---|"]
    for row in entries["rows"]:
        lines.append(f"| `{row['id']}` [{row['name']}]({row['officialSource']}) | {row['execution']} | {row['environment']} | {row['observation']} |")
    lines += ["", "## 原生能力与 Accord 职责矩阵", "",
              f"资料核对时间：`{capability_map['reviewedAt']}`。这是现有两宿主的开发评审快照，不是永久能力目录或当前行为验收。",
              "原生项的条件和效果尚需在实际客户端、模型路线及权限下核对。接口存在、配置可见、实际执行和结果成立分别取证。", "",
              "| 原生能力 / 来源 | 能力层 | 已核对的接口或能力 | 适用条件与未证实边界 |",
              "|---|---|---|---|"]
    for capability in capability_map["native"]:
        lines.append(f"| `{capability['id']}` [{capability['name']}]({capability['officialSource']}) | {capability['layer']} | {capability['surface']} | {capability['conditions']} |")
    lines += ["", "| Accord 职责 | 原生候选关系 | Accord 必要介入的假设 | 下一效果验证 |",
              "|---|---|---|---|"]
    for row in capability_map["accord"]:
        lines.append(f"| {duties[row['dutyId']]['name']} | {', '.join(row['nativeIds'])} | {row['role']} | {row['nextProbe']} |")
    lines += ["", "### 事实、索引、图与运行时", "",
              capability_map["representation"], "", capability_map["refreshRule"], "",
              capability_map["runtimeGap"], "",
              "运行时分配要求：" + contract["implementation"]["runtimeRequirement"], "",
              "源数据中的职责依赖、工序、场景和能力引用构成评审关系；它们不证明插件已经执行该链路。", "",
              "### 本机接口观察（非行为验收）", ""]
    for observation in capability_map["localObservations"]:
        lines.append(f"- `{observation['id']}` — {observation['subject']}。{observation['finding']} {observation['claimLimit']}")
    lines += ["", "## 动态适应的必查链路", "",
              "按具体声明选择原生对照、可交付最小组合和受控干扰；不把干净宿主规定为通用运行前提。",
              "环境处理：" + contract["environmentControl"]["handlingRule"], "",
              "| 环境变化 | 要观察的功能效果 | 失败判据 |", "|---|---|---|"]
    for scenario in contract["environmentControl"]["adaptationScenarios"]:
        lines.append(f"| {scenario['trigger']} | {scenario['requiredEffect']} | {scenario['failureOracle']} |")
    lines += ["", "## 当前短板及证据边界", ""]
    for finding in contract["systemOptimization"]["priorityFindings"]:
        lines.append(f"- `{finding['id']}` — `{finding['status']}`：{finding['basis']}")
    lines += ["", "## 发布顺序", "",
              "更新日志：[CHANGELOG.md](../../CHANGELOG.md)。当前为未发布开发摘要；定版时以精确候选及验收证据核对，不混入历史发布账本。", "",
              "版本内改动提交 → 推送精确候选 → 精确提交的验收与独立评审 → 发布同一提交 → 公共结果及清理核验。",
              "提交不能夹带无关工作；推送成功、工作区干净或本地测试通过都不能单独代替发布验收。", "",
              "当前对话含已启用的 Accord、其他能力及继承上下文，只作为开发辅助；不能用它证明普通用户环境下的效果。",
              "本页是计划的可见投影，不是宿主原生计划面板修复，也不是功能完成或发布凭证。", ""]
    return "\n".join(lines)
