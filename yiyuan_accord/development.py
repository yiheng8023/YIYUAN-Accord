"""Development-contract conformance, not a runtime or a behavior evaluator.

The post-release successor has its own semantics and unverified functional
obligations. Historical validation remains separate and is not promoted by
this check. These versioned checks bind their phase, not every future form.
"""

from pathlib import Path
import re

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

    implementation = section("implementation", ("rule", "triggerRule", "nativeRule", "reconstructionRule"))
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
    stages = optimization.get("workSequence")
    require(isinstance(stages, list) and len(stages) == 5,
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
              "这是现有职责的必要性评审清单，不是必须原样保留的功能集。保留项需当前效果证据，合并或删除项需说明需求判断及验收变更。", "",
              "| 职责 | 所属工序 | 历史需求与反例参考 |", "|---|---|---|"]
    for duty_id, duty in duties.items():
        stages = "、".join(stage["title"] for stage in contract["systemOptimization"]["workSequence"]
                          if duty_id in stage["duties"])
        lines.append(f"| {duty['name']} | {stages} | {', '.join(duty['goldenTasks'])} |")
    for retired in contract["acceptance"]["retiredDuties"]:
        lines.append(f"| {retired['id']}（已处置） | {retired['reason']}；{retired['acceptanceChange']} | {', '.join(retired['goldenTasks'])} |")
    lines += ["", "## 动态适应的必查链路", "",
              "按具体声明选择原生对照、可交付最小组合和受控干扰；不把干净宿主规定为通用运行前提。",
              "核对全局、父目录与项目的 AGENTS.md、config.toml 等全部生效配置，以及记忆、历史、插件和环境变量；记录来源与影响，不复制秘密。", "",
              "| 环境变化 | 要观察的功能效果 | 失败判据 |", "|---|---|---|"]
    for scenario in contract["environmentControl"]["adaptationScenarios"]:
        lines.append(f"| {scenario['trigger']} | {scenario['requiredEffect']} | {scenario['failureOracle']} |")
    lines += ["", "## 当前短板及证据边界", ""]
    for finding in contract["systemOptimization"]["priorityFindings"]:
        lines.append(f"- `{finding['id']}` — `{finding['status']}`：{finding['basis']}")
    lines += ["", "## 发布顺序", "",
              "版本内改动提交 → 推送精确候选 → 精确提交的验收与独立评审 → 发布同一提交 → 公共结果及清理核验。",
              "提交不能夹带无关工作；推送成功、工作区干净或本地测试通过都不能单独代替发布验收。", "",
              "当前对话含已启用的 Accord、其他能力及继承上下文，只作为开发辅助；不能用它证明普通用户环境下的效果。",
              "本页是计划的可见投影，不是宿主原生计划面板修复，也不是功能完成或发布凭证。", ""]
    return "\n".join(lines)
