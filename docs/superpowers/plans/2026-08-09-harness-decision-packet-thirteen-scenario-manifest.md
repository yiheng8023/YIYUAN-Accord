# Harness Decision Packet Thirteen-Scenario Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic packet v2 values for all thirteen current human-AI collaboration scenarios and one atomic digest-only manifest without promoting heterogeneous source evidence into execution, behavior, value, portability, production, release, or residual-gap claims.

**Architecture:** A governed binding registry declares how each current coverage row maps to its heterogeneous original source. A pure resolver normalizes eleven scenario-record bindings and two document-level bindings; packet v2 reuses the v1 request, authority, route, fallback, gate, claim, and digest semantics while making the normalized binding explicit. A separate manifest builder validates all thirteen packets in memory and emits only an all-or-nothing summary.

**Tech Stack:** Python 3 standard library (`argparse`, `copy`, `hashlib`, `json`, `os`, `pathlib`, `tempfile`, `typing`, `unittest`), JSON Schema Draft 2020-12 documents, repository JSON registries, Markdown, and local `scripts/verify.py` integration.

**Authoritative Design:** `docs/superpowers/specs/2026-08-08-harness-decision-packet-thirteen-scenario-manifest-design.md`.

## Global Constraints

- Work directly in `C:\Projects\agent-autonomy-harness` on `main`; do not create a branch or worktree for this sequential mainline slice.
- Preserve `plugin-compatible + manager-agnostic + release-not-eligible` exactly.
- The portable core must not depend on CC Switch; CC Switch and each host-native manager retain their separately owned lifecycle scopes.
- Preserve packet v1 schema, CLI behavior, checked fixture bytes, and digest exactly.
- The current coverage reconciliation remains authority for the exact thirteen-scenario set, source paths, six route classes, fallback order, unassessed cells, and claim ceiling.
- The binding registry is a derived source-shape contract only. It cannot redirect sources, select routes, grant lifecycle authority, or strengthen evidence.
- Build exactly eleven `scenario-record` and two `document-level-support` bindings.
- Every mechanism request has `evidenceLane: mechanism-validation`; `observedAvailability`, `taskBinding`, `currentCapabilityGap`, and `activationAuthority` remain `null`.
- Every packet and manifest entry has `selectedRoute: null`; every authorization and claim flag remains false.
- A batch failure emits no manifest and leaves an existing output target byte-for-byte unchanged.
- Keep `acceptance.decision-ready-consumer-projection` at `partial` and the program inventory at 46 verified / 15 partial / 0 planned.
- Do not install, enable, invoke, connect an account, dispatch a model, mutate CC Switch or a consumer, publish, release, delete, or claim a residual gap.
- Use canonical JSON with `ensure_ascii=False`, `sort_keys=True`, and `separators=(",", ":")`; compute each digest over the object body without its digest field.
- Use `apply_patch` for repository writes. CLI output tests may use operating-system temporary directories outside the repository.
- Run focused tests first, then the complete local unittest suite and `python -B scripts/verify.py`. GitHub Actions is optional corroboration, never the primary or sole acceptance surface.
- Under Subagent-Driven Development, an implementer commits but does not push. The controller pushes only after the task's specification and quality review is clean. A missing-module or missing-symbol runner error is interface preflight, not sufficient TDD RED evidence; before implementation, add or rerun a behavior test that reaches the declared interface and fails by assertion for the expected unimplemented behavior.
- README currently makes no single-scenario decision-packet claim, so this plan does not change README. Recheck that fact before the documentation commit.

---

## File Structure

**Create:**

- `schemas/harness-scenario-evidence-binding-registry-v1.schema.json` — exact binding-registry contract.
- `registry/harness-scenario-evidence-bindings-v1.json` — current thirteen-row source-shape binding registry.
- `scripts/harness_scenario_evidence_binding.py` — registry loading, JSON Pointer resolution, and binding validation.
- `tests/test_harness_scenario_evidence_binding.py` — exact-set, locator, aggregate, and drift tests.
- `schemas/harness-decision-packet-v2.schema.json` — v2 packet contract with `scenarioEvidenceBinding`.
- `scripts/harness_decision_packet_v2.py` — v2 construction, independent validation, and serialization.
- `scripts/build_harness_decision_packet_v2.py` — one-request stdout CLI.
- `tests/test_harness_decision_packet_v2.py` — v2 scenario-record, document-level, digest, gate, and CLI tests.
- `schemas/harness-decision-packet-manifest-v1.schema.json` — atomic summary-manifest contract.
- `scripts/harness_decision_packet_manifest.py` — canonical probe requests, batch failure aggregation, manifest construction, and validation.
- `scripts/build_harness_decision_packet_manifest.py` — stdout or explicit atomic-output CLI.
- `tests/test_harness_decision_packet_manifest.py` — all-thirteen, deterministic, mutation, and atomic-write tests.
- `tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json` — checked canonical manifest, not packet bodies.
- `scripts/validate_harness_decision_packet_manifest_poc.py` — repository evidence and mutation replay validator.
- `tests/test_harness_decision_packet_manifest_poc.py` — evidence/acceptance integration tests.
- `registry/harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09.json` — dated mechanism evidence.
- `docs/strategy/HARNESS-DECISION-PACKET-THIRTEEN-SCENARIO-MANIFEST-POC-2026-08-09.md` — human-readable result and claim boundary.

**Modify:**

- `scripts/harness_decision_packet.py` — extract byte-compatible shared authority and projection helpers for v1/v2.
- `tests/test_harness_decision_packet.py` — lock v1 bytes/digest through the shared-helper refactor.
- `registry/program-acceptance-map.json` — add one evidence record/reference without changing assessment or counts.
- `docs/strategy/RESEARCH-AND-POC-PLAN.md` — record the bounded mechanism result and next gates.
- `docs/operations/CURRENT-GOAL-MODE-PROMPT.md` — replace the single-scenario mechanism projection with the thirteen-scenario boundary.
- `docs/operations/CONTINUATION.md` — append live repository result, verification, claims, and next action.
- `scripts/verify.py` — require and invoke the focused PoC validator.

---

### Task 1: Add the governed scenario-evidence binding layer

**Files:**
- Create: `schemas/harness-scenario-evidence-binding-registry-v1.schema.json`
- Create: `registry/harness-scenario-evidence-bindings-v1.json`
- Create: `scripts/harness_scenario_evidence_binding.py`
- Create: `tests/test_harness_scenario_evidence_binding.py`
- Modify: `scripts/harness_decision_packet.py`
- Modify: `tests/test_harness_decision_packet.py`

**Interfaces:**
- Consumes: request v1 dictionaries and current semantic/coverage/scheduler/acceptance JSON.
- Produces: `load_current_authority_bundle(root, request) -> dict[str, Any]`, `load_source_evidence_record(root, relative) -> dict[str, Any]`, `load_binding_registry(root, relative=BINDING_REGISTRY_PATH) -> dict[str, Any]`, `validate_binding_registry(root, registry, coverage) -> None`, and `resolve_scenario_evidence_binding(root, registry, scenario) -> tuple[dict[str, Any], list[dict[str, Any]]]`.

- [ ] **Step 1: Write failing registry and v1-compatibility tests**

Create `tests/test_harness_scenario_evidence_binding.py` with these starting assertions:

```python
import copy
import json
from pathlib import Path
import unittest

from scripts.harness_decision_packet import DecisionPacketError, load_current_authority_bundle
from scripts.harness_scenario_evidence_binding import (
    BINDING_REGISTRY_PATH,
    load_binding_registry,
    resolve_scenario_evidence_binding,
    validate_binding_registry,
)

ROOT = Path(__file__).resolve().parent.parent


def request_for(scenario_id: str) -> dict[str, object]:
    return {
        "schema": 1,
        "requestId": f"harness.manifest.v1:{scenario_id}",
        "scenarioId": scenario_id,
        "evidenceLane": "mechanism-validation",
        "expectedSemanticAuthorityId": "skill-portfolio-current-authority-v1",
        "observedAvailability": None,
        "taskBinding": None,
        "currentCapabilityGap": None,
        "activationAuthority": None,
    }


class HarnessScenarioEvidenceBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        first = load_current_authority_bundle(ROOT, request_for("GEN-CREATIVE-01"))
        self.coverage = first["coverage"]
        self.registry = load_binding_registry(ROOT)

    def test_registry_matches_exact_current_coverage_order(self) -> None:
        validate_binding_registry(ROOT, self.registry, self.coverage)
        expected = [item["scenarioId"] for item in self.coverage["document"]["scenarioCoverage"]]
        actual = [item["scenarioId"] for item in self.registry["bindings"]]
        self.assertEqual(expected, actual)
        self.assertEqual(11, sum(item["bindingMode"] == "scenario-record" for item in self.registry["bindings"]))
        self.assertEqual(2, sum(item["bindingMode"] == "document-level-support" for item in self.registry["bindings"]))

    def test_all_current_bindings_resolve(self) -> None:
        for row in self.coverage["document"]["scenarioCoverage"]:
            with self.subTest(scenario_id=row["scenarioId"]):
                normalized, sources = resolve_scenario_evidence_binding(ROOT, self.registry, row)
                self.assertEqual(row["scenarioId"], normalized["scenarioId"])
                self.assertEqual(row["evidenceSourcePaths"], [item["path"] for item in sources])

    def test_document_level_bindings_preserve_aggregate_identity(self) -> None:
        for scenario_id in ("SE-ARCH-DESIGN-01", "SE-VERIFY-SECURE-01"):
            row = next(item for item in self.coverage["document"]["scenarioCoverage"] if item["scenarioId"] == scenario_id)
            normalized, _ = resolve_scenario_evidence_binding(ROOT, self.registry, row)
            self.assertEqual("document-level-support", normalized["bindingMode"])
            self.assertFalse(normalized["scenarioIdentityPresentInSource"])
            self.assertEqual("SE-E2E-THIN-01", normalized["sourceScenarioId"])

    def test_source_redirection_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.registry)
        mutated["bindings"][0]["sourcePath"] = "registry/program-acceptance-map.json"
        with self.assertRaises(DecisionPacketError) as raised:
            validate_binding_registry(ROOT, mutated, self.coverage)
        self.assertEqual("binding-source-path-drift", raised.exception.code)
```

Add to `tests/test_harness_decision_packet.py`:

```python
    def test_v1_fixture_bytes_remain_exact_after_shared_helper_refactor(self) -> None:
        expected = (ROOT / "tests/fixtures/harness-decision-packet-gen-research-01.json").read_bytes()
        actual = serialize_decision_packet(build_decision_packet(ROOT, self.load_request()))
        self.assertEqual(expected, actual)
```

- [ ] **Step 2: Run the new tests and confirm missing-interface failures**

```powershell
python -B -m unittest tests.test_harness_scenario_evidence_binding tests.test_harness_decision_packet.HarnessDecisionPacketBuildTests.test_v1_fixture_bytes_remain_exact_after_shared_helper_refactor -v
```

Expected: FAIL because the binding module and shared loader do not exist.

- [ ] **Step 3: Add the strict registry schema and exact thirteen-row registry**

The schema requires exactly:

```json
{
  "topLevel": ["schema", "id", "date", "status", "coverageAuthority", "bindings"],
  "coverageAuthority": ["path", "id", "sha256"],
  "binding": [
    "scenarioId", "sourcePath", "bindingMode", "identityPointers",
    "aggregateScenarioPointer", "expectedAggregateScenarioId",
    "scenarioIdentityPresentInSource", "bindingEvidenceCeiling", "explanation"
  ]
}
```

Use `additionalProperties: false` at every object level. `bindingMode` is one of `scenario-record` and `document-level-support`. For scenario records, `identityPointers` is non-empty and both aggregate fields are null. For document-level support, `identityPointers` is empty and the aggregate fields are non-empty strings.

Create the registry with coverage digest `d962097402f55c3bc878df0a6ce192ee35086eceef4ea97c4c8d258a971bdf65` and these exact binding values:

```json
[
  ["GEN-CREATIVE-01", "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json", "scenario-record", ["/scenarioBinding/scenarioId"]],
  ["GEN-RESEARCH-01", "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json", "scenario-record", ["/scenarios/1/id"]],
  ["GEN-LEARNING-01", "registry/human-ai-collaboration-learning-capability-baseline-2026-07-31.json", "scenario-record", ["/scenarioBinding/scenarioId"]],
  ["GEN-ORG-DECISION-01", "registry/human-ai-collaboration-org-decision-zero-model-protocol-2026-07-31.json", "scenario-record", ["/scenarioBinding/scenarioId"]],
  ["GEN-ACCESS-COMMS-01", "registry/human-ai-collaboration-access-comms-capability-baseline-2026-07-31.json", "scenario-record", ["/scenarioBinding/scenarioId"]],
  ["SE-DISCOVERY-REQ-01", "registry/other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json", "scenario-record", ["/behaviorallyObservedScenarioCells/0/scenarioId"]],
  ["SE-ARCH-DESIGN-01", "registry/human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-evidence-2026-07-27.json", "document-level-support", []],
  ["SE-IMPLEMENT-REVIEW-01", "registry/other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json", "scenario-record", ["/behaviorallyObservedScenarioCells/1/scenarioId"]],
  ["SE-VERIFY-SECURE-01", "registry/human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-evidence-2026-07-27.json", "document-level-support", []],
  ["SE-RELEASE-CHANGE-01", "registry/human-ai-collaboration-release-change-current-cc-codex-no-model-preflight-2026-07-30.json", "scenario-record", ["/scenarioId"]],
  ["SE-OPS-INCIDENT-01", "registry/other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json", "scenario-record", ["/behaviorallyObservedScenarioCells/2/scenarioId", "/behaviorallyObservedScenarioCells/3/scenarioId"]],
  ["SE-MAINT-MIGRATE-01", "registry/other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json", "scenario-record", ["/behaviorallyObservedScenarioCells/4/scenarioId"]],
  ["SE-MGMT-PRACTICE-01", "registry/human-ai-collaboration-engineering-management-zero-model-protocol-2026-07-31.json", "scenario-record", ["/scenarioBinding/scenarioId"]]
]
```

For scenario records set aggregate fields to null, identity-present true, and ceiling `source-record-identity-only-no-evidence-promotion`. For both document-level entries set `/scenarioId`, `SE-E2E-THIN-01`, identity-present false, and ceiling `document-level-support-no-independent-scenario-identity`.

- [ ] **Step 4: Extract byte-compatible current-authority helpers from v1**

In `scripts/harness_decision_packet.py`, add:

```python
def load_current_authority_bundle(root: Path, request: object) -> dict[str, Any]:
    validate_decision_request(request)
    assert isinstance(request, dict)
    semantic = _authority_record(root, SEMANTIC_AUTHORITY_PATH, missing_code="semantic-authority-missing")
    if semantic["id"] != request["expectedSemanticAuthorityId"]:
        raise DecisionPacketError("semantic-authority-id-mismatch", "Expected semantic authority does not match the current authority.")
    coverage = _authority_record(root, COVERAGE_PATH, missing_code="coverage-authority-missing")
    scheduler = _authority_record(root, SCHEDULER_PATH, missing_code="scheduler-authority-missing")
    acceptance = _authority_record(root, ACCEPTANCE_PATH, missing_code="acceptance-authority-missing")
    scenario = _find_scenario(coverage["document"].get("scenarioCoverage"), "scenarioId", request["scenarioId"])
    if scenario is None:
        raise DecisionPacketError("unknown-scenario", "Scenario is not present in the current coverage authority.")
    return {
        "semanticAuthority": semantic,
        "coverage": coverage,
        "scheduler": scheduler,
        "acceptance": acceptance,
        "scenario": scenario,
    }


def load_source_evidence_record(root: Path, relative: str | Path) -> dict[str, Any]:
    path = Path(relative)
    document = _load_json(root, path, "evidence-source-missing")
    return {
        "path": path.as_posix(),
        "id": document.get("id"),
        "sha256": _source_sha256(root, path, "evidence-source-missing"),
        "status": document.get("status"),
        "document": document,
    }
```

Refactor `load_authority_bundle` to call `load_current_authority_bundle`, then retain its existing v1-only `document.scenarios[].id` check. Do not change the public v1 packet content.

- [ ] **Step 5: Implement registry validation and JSON Pointer resolution**

Create `scripts/harness_scenario_evidence_binding.py` with these public constants and functions:

```python
BINDING_REGISTRY_PATH = Path("registry/harness-scenario-evidence-bindings-v1.json")
BINDING_MODES = {"scenario-record", "document-level-support"}
BINDING_FIELDS = {
    "scenarioId", "sourcePath", "bindingMode", "identityPointers",
    "aggregateScenarioPointer", "expectedAggregateScenarioId",
    "scenarioIdentityPresentInSource", "bindingEvidenceCeiling", "explanation",
}


def resolve_json_pointer(document: object, pointer: str) -> object:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise DecisionPacketError("binding-pointer-invalid", "Binding pointer must be a non-root JSON Pointer.")
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise DecisionPacketError("binding-pointer-unresolved", "Binding pointer does not resolve.")
            current = current[int(token)]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise DecisionPacketError("binding-pointer-unresolved", "Binding pointer does not resolve.")
    return current
```

Reject duplicate/extra/reordered scenarios with `binding-scenario-set-drift`, mismatched source paths with `binding-source-path-drift`, invalid mode shapes with `binding-mode-invalid`, wrong resolved IDs with `binding-scenario-identity-mismatch`, wrong aggregate ID with `binding-aggregate-identity-drift`, and any `scenarioId` field or `scenarios/*/id` matching a document-level target with `document-level-identity-promotion`. Evaluate `scenarioIdentityPresentInSource is False` plus a non-document-level mode as `document-level-identity-promotion` before the generic mode-shape error. For `scenario-record`, require identity completeness inside each declared JSON Pointer collection surface: if a pointer traverses a list index, enumerate matching scenario identities only in that same list and with the same remaining field suffix; require that complete pointer set to equal `identityPointers`. For non-list pointers, validate only the exact declared pointer. This makes an omitted duplicate current record fail closed without promoting identities from unrelated historical collections.

Return a normalized binding object containing registry public binding, scenario/source IDs, source path, mode, pointers/resolved values, identity-present flag, and ceiling, plus source records shaped exactly like v1 `sourceEvidence` bundle records.

- [ ] **Step 6: Run focused tests and the entire v1 packet suite**

```powershell
python -B -m unittest tests.test_harness_scenario_evidence_binding tests.test_harness_decision_packet -v
```

Expected: all tests PASS and the checked v1 fixture remains byte-identical.

- [ ] **Step 7: Commit the binding layer for review**

```powershell
git add -- schemas/harness-scenario-evidence-binding-registry-v1.schema.json registry/harness-scenario-evidence-bindings-v1.json scripts/harness_scenario_evidence_binding.py scripts/harness_decision_packet.py tests/test_harness_scenario_evidence_binding.py tests/test_harness_decision_packet.py
git diff --cached --check
git commit -m "feat: bind all harness decision scenarios"
```

After the task's specification and quality review is clean, the controller runs `git push origin main`, verifies `HEAD == origin/main`, ahead/behind `0/0`, and a clean worktree before Task 2.

---

### Task 2: Build and independently validate decision packet v2

**Files:**
- Create: `schemas/harness-decision-packet-v2.schema.json`
- Create: `scripts/harness_decision_packet_v2.py`
- Create: `scripts/build_harness_decision_packet_v2.py`
- Create: `tests/test_harness_decision_packet_v2.py`
- Modify: `scripts/harness_decision_packet.py`
- Modify: `tests/test_harness_decision_packet.py`

**Interfaces:**
- Consumes: `load_current_authority_bundle`, normalized binding/source records, and v1 canonical/request/route constants.
- Produces: `build_decision_packet_from_bundle(...)`, `validate_decision_packet_projection(...)`, `build_decision_packet_v2(root, request) -> dict[str, Any]`, `validate_decision_packet_v2(root, packet) -> None`, and `serialize_decision_packet_v2(packet) -> bytes`.

- [ ] **Step 1: Write failing v2 positive, document-level, mutation, and CLI tests**

Create `tests/test_harness_decision_packet_v2.py` starting with:

```python
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.harness_decision_packet import DecisionPacketError, canonical_sha256
from scripts.harness_decision_packet_v2 import (
    build_decision_packet_v2,
    serialize_decision_packet_v2,
    validate_decision_packet_v2,
)
from tests.test_harness_scenario_evidence_binding import request_for

ROOT = Path(__file__).resolve().parent.parent


class HarnessDecisionPacketV2Tests(unittest.TestCase):
    def test_scenario_record_packet_is_source_bound(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("GEN-CREATIVE-01"))
        validate_decision_packet_v2(ROOT, packet)
        self.assertEqual(2, packet["schema"])
        self.assertEqual("scenario-record", packet["scenarioEvidenceBinding"]["bindingMode"])
        self.assertTrue(packet["scenarioEvidenceBinding"]["scenarioIdentityPresentInSource"])
        self.assertEqual("mechanism-evidence-only", packet["decisionState"])
        self.assertIsNone(packet["selectedRoute"])
        self.assertFalse(any(packet["authorizationGates"].values()))
        self.assertFalse(any(packet["claimBoundary"].values()))

    def test_document_level_packet_keeps_aggregate_ceiling(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("SE-ARCH-DESIGN-01"))
        binding = packet["scenarioEvidenceBinding"]
        self.assertEqual("document-level-support", binding["bindingMode"])
        self.assertFalse(binding["scenarioIdentityPresentInSource"])
        self.assertEqual("SE-E2E-THIN-01", binding["sourceScenarioId"])
        self.assertEqual("document-level-support-no-independent-scenario-identity", binding["bindingEvidenceCeiling"])

    def test_binding_promotion_is_rejected_after_resealing(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("SE-VERIFY-SECURE-01"))
        mutated = copy.deepcopy(packet)
        mutated["scenarioEvidenceBinding"]["bindingMode"] = "scenario-record"
        mutated["packetSha256"] = canonical_sha256({k: v for k, v in mutated.items() if k != "packetSha256"})
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_packet_v2(ROOT, mutated)
        self.assertEqual("document-level-identity-promotion", raised.exception.code)

    def test_repeated_v2_build_is_byte_identical(self) -> None:
        request = request_for("GEN-LEARNING-01")
        self.assertEqual(
            serialize_decision_packet_v2(build_decision_packet_v2(ROOT, request)),
            serialize_decision_packet_v2(build_decision_packet_v2(ROOT, request)),
        )
```

Add this CLI test:

```python
    def test_cli_emits_canonical_v2_packet_without_repository_writes(self) -> None:
        before = subprocess.run(
            ["git", "status", "--short"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        with tempfile.TemporaryDirectory() as temporary_directory:
            request_path = Path(temporary_directory) / "request.json"
            request_path.write_text(
                json.dumps(request_for("SE-VERIFY-SECURE-01"), ensure_ascii=False),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-B", "scripts/build_harness_decision_packet_v2.py", str(request_path)],
                cwd=ROOT, check=False, capture_output=True,
            )
        after = subprocess.run(
            ["git", "status", "--short"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stderr)
        self.assertEqual(before, after)
        packet = json.loads(result.stdout)
        self.assertEqual(2, packet["schema"])
        self.assertEqual(result.stdout, serialize_decision_packet_v2(packet))
        self.assertIsNone(packet["selectedRoute"])
```

- [ ] **Step 2: Run the v2 tests and confirm missing-interface failures**

```powershell
python -B -m unittest tests.test_harness_decision_packet_v2 -v
```

Expected: FAIL because packet v2 interfaces do not exist.

- [ ] **Step 3: Add the packet v2 schema**

Start from packet v1 but require schema 2 and this exact top-level set:

```json
[
  "schema", "packetId", "authorityBinding", "request", "sourceEvidence",
  "scenarioEvidenceBinding", "routeCoverage", "fallbackOrder", "decisionState",
  "selectedRoute", "authorizationGates", "claimBoundary", "recheckTriggers",
  "projectionBoundary", "packetSha256"
]
```

`scenarioEvidenceBinding` requires exactly:

```json
[
  "registry", "scenarioId", "sourcePath", "bindingMode", "identityPointers",
  "resolvedIdentityValues", "aggregateScenarioPointer", "sourceScenarioId",
  "scenarioIdentityPresentInSource", "bindingEvidenceCeiling"
]
```

Require `selectedRoute` to be null, all authorization/claim fields false, and the existing projection boundary unchanged.

- [ ] **Step 4: Extract common packet construction and validation without changing v1 bytes**

In `scripts/harness_decision_packet.py`, add:

```python
def build_decision_packet_from_bundle(
    root: Path,
    request: dict[str, Any],
    bundle: dict[str, Any],
    *,
    schema: int,
    packet_id_prefix: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_bound_source_digests(root, bundle)
    packet = {
        "schema": schema,
        "packetId": f"{packet_id_prefix}:{request['requestId']}",
        "authorityBinding": {
            "semanticAuthority": _public_binding(bundle["semanticAuthority"]),
            "coverage": _public_binding(bundle["coverage"]),
            "scheduler": _public_binding(bundle["scheduler"]),
            "acceptance": _public_binding(bundle["acceptance"]),
        },
        "request": copy.deepcopy(request),
        "sourceEvidence": _packet_source_evidence(bundle),
        "routeCoverage": _packet_route_coverage(bundle["scenario"]),
        "fallbackOrder": copy.deepcopy(bundle["scenario"]["fallbackOrder"]),
        "decisionState": _decision_state(request),
        "selectedRoute": None,
        "authorizationGates": copy.deepcopy(AUTHORIZATION_GATES),
        "claimBoundary": copy.deepcopy(bundle["coverage"]["document"]["claimBoundary"]),
        "recheckTriggers": copy.deepcopy(bundle["coverage"]["document"]["recheckTriggers"]),
        "projectionBoundary": copy.deepcopy(PROJECTION_BOUNDARY),
    }
    packet.update(copy.deepcopy(extra_fields or {}))
    packet["packetSha256"] = canonical_sha256(packet)
    return packet
```

Extract the current validator body into `validate_decision_packet_projection(root, bundle, packet, *, packet_fields, schema, packet_id_prefix)`. It must retain every existing typed route, fallback, authority, source, gate, claim, projection, and digest error. `build_decision_packet` and `validate_decision_packet` become v1 wrappers; their tests and fixture must remain exact.

- [ ] **Step 5: Implement packet v2 construction and independent validation**

In `scripts/harness_decision_packet_v2.py`:

```python
PACKET_V2_FIELDS = PACKET_FIELDS | {"scenarioEvidenceBinding"}


def load_v2_bundle(root: Path, request: object) -> tuple[dict[str, Any], dict[str, Any]]:
    core = load_current_authority_bundle(root, request)
    registry = load_binding_registry(root)
    validate_binding_registry(root, registry, core["coverage"])
    normalized, sources = resolve_scenario_evidence_binding(root, registry, core["scenario"])
    bundle = {**core, "sourceEvidence": sources}
    validate_authority_bundle(bundle, request)
    return bundle, normalized


def build_decision_packet_v2(root: Path, request: object) -> dict[str, Any]:
    validate_decision_request(request)
    assert isinstance(request, dict)
    bundle, normalized = load_v2_bundle(root, request)
    packet = build_decision_packet_from_bundle(
        root, request, bundle,
        schema=2,
        packet_id_prefix="harness-decision-packet-v2",
        extra_fields={"scenarioEvidenceBinding": normalized},
    )
    validate_decision_packet_v2(root, packet)
    return packet
```

`validate_decision_packet_v2` must independently reload the registry and source, call the common projection validator with v2 fields, compare the complete normalized binding object, reject document-level promotion with `document-level-identity-promotion`, and then recompute the packet digest. `serialize_decision_packet_v2` returns canonical JSON plus one newline.

- [ ] **Step 6: Add the thin on-demand v2 CLI**

Mirror the v1 CLI. It accepts one request path and optional `--root`, emits only canonical packet bytes on stdout, and emits `DecisionPacketError.as_dict()` or `request-read-failed` on stderr with exit code 2. It has no output-file option; atomic persistence belongs to the manifest CLI.

- [ ] **Step 7: Run v1 and v2 focused suites**

```powershell
python -B -m unittest tests.test_harness_decision_packet tests.test_harness_scenario_evidence_binding tests.test_harness_decision_packet_v2 -v
```

Expected: all tests PASS; packet v1 fixture bytes and digest are unchanged.

- [ ] **Step 8: Commit packet v2 for review**

```powershell
git add -- schemas/harness-decision-packet-v2.schema.json scripts/harness_decision_packet.py scripts/harness_decision_packet_v2.py scripts/build_harness_decision_packet_v2.py tests/test_harness_decision_packet.py tests/test_harness_decision_packet_v2.py
git diff --cached --check
git commit -m "feat: add harness decision packet v2"
```

After the task's specification and quality review is clean, the controller runs `git push origin main`, verifies `HEAD == origin/main`, ahead/behind `0/0`, and a clean worktree before Task 3.

---

### Task 3: Build the atomic thirteen-scenario summary manifest

**Files:**
- Create: `schemas/harness-decision-packet-manifest-v1.schema.json`
- Create: `scripts/harness_decision_packet_manifest.py`
- Create: `scripts/build_harness_decision_packet_manifest.py`
- Create: `tests/test_harness_decision_packet_manifest.py`

**Interfaces:**
- Consumes: current coverage order and `build_decision_packet_v2` / `validate_decision_packet_v2`.
- Produces: `BatchBindingError`, `build_canonical_probe_request(scenario_id)`, `build_decision_packet_manifest(root)`, `validate_decision_packet_manifest(root, manifest)`, `serialize_decision_packet_manifest(manifest)`, and `write_manifest_atomically(path, data)`.

- [ ] **Step 1: Write failing all-thirteen and atomic-output tests**

Create `tests/test_harness_decision_packet_manifest.py` with:

```python
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.harness_decision_packet import canonical_sha256
from scripts.harness_decision_packet_manifest import (
    BatchBindingError,
    build_decision_packet_manifest,
    serialize_decision_packet_manifest,
    validate_decision_packet_manifest,
)

ROOT = Path(__file__).resolve().parent.parent


class HarnessDecisionPacketManifestTests(unittest.TestCase):
    def test_manifest_contains_all_scenarios_in_current_order(self) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        validate_decision_packet_manifest(ROOT, manifest)
        coverage = json.loads((ROOT / "registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json").read_text(encoding="utf-8"))
        expected = [item["scenarioId"] for item in coverage["scenarioCoverage"]]
        self.assertEqual(expected, [item["scenarioId"] for item in manifest["entries"]])
        self.assertEqual(13, manifest["scenarioCount"])
        self.assertEqual(11, sum(item["bindingMode"] == "scenario-record" for item in manifest["entries"]))
        self.assertEqual(2, sum(item["bindingMode"] == "document-level-support" for item in manifest["entries"]))
        self.assertTrue(manifest["atomic"])
        self.assertTrue(all(item["selectedRoute"] is None for item in manifest["entries"]))

    def test_repeated_manifest_is_byte_identical(self) -> None:
        first = serialize_decision_packet_manifest(build_decision_packet_manifest(ROOT))
        second = serialize_decision_packet_manifest(build_decision_packet_manifest(ROOT))
        self.assertEqual(first, second)

    def test_manifest_entry_removal_is_rejected(self) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        mutated = copy.deepcopy(manifest)
        mutated["entries"].pop()
        mutated["manifestSha256"] = canonical_sha256({k: v for k, v in mutated.items() if k != "manifestSha256"})
        with self.assertRaises(BatchBindingError) as raised:
            validate_decision_packet_manifest(ROOT, mutated)
        self.assertEqual("batch-binding-failed", raised.exception.code)

    def test_failed_cli_leaves_existing_output_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "manifest.json"
            output.write_bytes(b"known-good\n")
            result = subprocess.run(
                [sys.executable, "-B", "scripts/build_harness_decision_packet_manifest.py", "--root", str(Path(temporary_directory) / "missing-root"), "--output", str(output)],
                cwd=ROOT, check=False, capture_output=True,
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual(b"known-good\n", output.read_bytes())
            self.assertEqual(b"", result.stdout)
```

- [ ] **Step 2: Run the manifest tests and confirm missing-interface failures**

```powershell
python -B -m unittest tests.test_harness_decision_packet_manifest -v
```

Expected: FAIL because the manifest module does not exist.

- [ ] **Step 3: Add the exact manifest schema**

Require exactly:

```json
[
  "schema", "id", "packetSchema", "authorityBinding", "atomic",
  "scenarioCount", "entries", "executionCounters", "authorizationGates",
  "claimBoundary", "projectionBoundary", "manifestSha256"
]
```

Each entry requires exactly:

```json
[
  "scenarioId", "bindingMode", "sourcePath", "sourceSha256",
  "packetSha256", "decisionState", "selectedRoute", "bindingEvidenceCeiling"
]
```

Require schema 1, packet schema 2, `atomic: true`, `scenarioCount: 13`, exactly thirteen entries, null selected routes, zero counters, false gates/claims, and the unchanged projection boundary.

- [ ] **Step 4: Implement canonical requests, batch failures, construction, and validation**

Create `scripts/harness_decision_packet_manifest.py` with:

```python
class BatchBindingError(DecisionPacketError):
    def __init__(self, issues: list[dict[str, object]]) -> None:
        super().__init__("batch-binding-failed", "One or more scenario bindings failed; no manifest was produced.")
        self.issues = issues

    def as_dict(self) -> dict[str, object]:
        return {**super().as_dict(), "issues": copy.deepcopy(self.issues)}


def build_canonical_probe_request(scenario_id: str) -> dict[str, object]:
    return {
        "schema": 1,
        "requestId": f"harness.manifest.v1:{scenario_id}",
        "scenarioId": scenario_id,
        "evidenceLane": "mechanism-validation",
        "expectedSemanticAuthorityId": "skill-portfolio-current-authority-v1",
        "observedAvailability": None,
        "taskBinding": None,
        "currentCapabilityGap": None,
        "activationAuthority": None,
    }
```

Build in current coverage order. Collect scenario failures as `{scenarioId, code, message, path}`; use `scenarioId: None` for registry-wide failures. Do not include successful packet bodies. If issues exist, raise one `BatchBindingError`. Otherwise create entries from validated packet v2 values and bind semantic, coverage, scheduler, acceptance, and binding-registry public digests at manifest level.

`validate_decision_packet_manifest` independently rebuilds all thirteen canonical packets, compares ordered entries and bindings, requires zero/false boundaries, and checks `manifestSha256`. Any mismatch is returned as one deterministic `BatchBindingError`.

- [ ] **Step 5: Implement stdout and atomic-file CLI behavior**

Add the atomic helper to `scripts/harness_decision_packet_manifest.py`, then import it from `scripts/build_harness_decision_packet_manifest.py`. The CLI accepts `--root` and optional `--output`. Without output, emit canonical bytes to stdout. With output, use:

```python
def write_manifest_atomically(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
```

Do not touch the target until build, packet validation, manifest validation, and serialization all succeed. On `BatchBindingError`, emit its machine-readable envelope to stderr, exit 2, and emit no stdout.

- [ ] **Step 6: Add mutation tests for every approved boundary**

Add this helper and the direct manifest mutations:

```python
    def assert_manifest_issue(self, mutate, expected_code: str) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        mutated = copy.deepcopy(manifest)
        mutate(mutated)
        mutated["manifestSha256"] = canonical_sha256(
            {key: value for key, value in mutated.items() if key != "manifestSha256"}
        )
        with self.assertRaises(BatchBindingError) as raised:
            validate_decision_packet_manifest(ROOT, mutated)
        self.assertIn(expected_code, [item["code"] for item in raised.exception.issues])

    def test_manifest_entry_duplication_is_rejected(self) -> None:
        self.assert_manifest_issue(
            lambda value: value["entries"].insert(1, copy.deepcopy(value["entries"][0])),
            "manifest-entry-set-drift",
        )

    def test_manifest_entry_reordering_is_rejected(self) -> None:
        def swap(value: dict[str, object]) -> None:
            value["entries"][0], value["entries"][1] = value["entries"][1], value["entries"][0]
        self.assert_manifest_issue(swap, "manifest-entry-order-drift")

    def test_manifest_digest_drift_is_rejected(self) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        manifest["manifestSha256"] = "0" * 64
        with self.assertRaises(BatchBindingError) as raised:
            validate_decision_packet_manifest(ROOT, manifest)
        self.assertIn("manifest-digest-mismatch", [item["code"] for item in raised.exception.issues])
```

Use temporary repository copies for source mutations. Add one named test per approved mutation with this exact expected mapping:

```python
SOURCE_MUTATION_EXPECTATIONS = {
    "test_registry_missing_scenario_is_rejected": "binding-scenario-set-drift",
    "test_registry_extra_scenario_is_rejected": "binding-scenario-set-drift",
    "test_registry_reordering_is_rejected": "binding-scenario-set-drift",
    "test_source_redirection_is_rejected": "binding-source-path-drift",
    "test_malformed_pointer_is_rejected": "binding-pointer-invalid",
    "test_unresolved_pointer_is_rejected": "binding-pointer-unresolved",
    "test_wrong_identity_is_rejected": "binding-scenario-identity-mismatch",
    "test_missing_second_ops_pointer_is_rejected": "binding-scenario-identity-mismatch",
    "test_document_level_mode_promotion_is_rejected": "document-level-identity-promotion",
    "test_aggregate_identity_drift_is_rejected": "binding-aggregate-identity-drift",
    "test_document_level_identity_appearance_is_rejected": "document-level-identity-promotion",
    "test_authority_digest_drift_is_rejected": "authority-source-digest-drift",
    "test_source_digest_drift_is_rejected": "evidence-source-digest-drift",
}
```

Each named test copies only the bound authorities, registry, and relevant original source into `tempfile.TemporaryDirectory()`, applies its one mutation, calls the same public builder or validator against that root, and asserts the mapped code in `BatchBindingError.issues`. Do not combine two mutations in one test.

- [ ] **Step 7: Run all packet and manifest focused tests**

```powershell
python -B -m unittest tests.test_harness_decision_packet tests.test_harness_scenario_evidence_binding tests.test_harness_decision_packet_v2 tests.test_harness_decision_packet_manifest -v
```

Expected: all tests PASS with no repository writes from stdout-only CLIs.

- [ ] **Step 8: Commit the atomic manifest mechanism for review**

```powershell
git add -- schemas/harness-decision-packet-manifest-v1.schema.json scripts/harness_decision_packet_manifest.py scripts/build_harness_decision_packet_manifest.py tests/test_harness_decision_packet_manifest.py
git diff --cached --check
git commit -m "feat: build atomic harness decision manifests"
```

After the task's specification and quality review is clean, the controller runs `git push origin main`, verifies `HEAD == origin/main`, ahead/behind `0/0`, and a clean worktree before Task 4.

---

### Task 4: Bind repository evidence, acceptance posture, goal mode, and continuation

**Files:**
- Create: `tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json`
- Create: `scripts/validate_harness_decision_packet_manifest_poc.py`
- Create: `tests/test_harness_decision_packet_manifest_poc.py`
- Create: `registry/harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09.json`
- Create: `docs/strategy/HARNESS-DECISION-PACKET-THIRTEEN-SCENARIO-MANIFEST-POC-2026-08-09.md`
- Modify: `docs/strategy/RESEARCH-AND-POC-PLAN.md`
- Modify: `docs/operations/CURRENT-GOAL-MODE-PROMPT.md`
- Modify: `docs/operations/CONTINUATION.md`
- Modify: `scripts/verify.py`
- Modify: `tests/test_verify_integration.py`

**Interfaces:**
- Consumes: canonical manifest bytes and all focused validators.
- Produces: `run_failure_matrix(root) -> list[dict[str, str]]` and `validate_repository_record(root=ROOT) -> dict[str, object]`.

- [ ] **Step 1: Write failing repository-integration tests**

Create `tests/test_harness_decision_packet_manifest_poc.py`:

```python
import json
from pathlib import Path
import unittest

from scripts.validate_harness_decision_packet_manifest_poc import (
    EXPECTED_MANIFEST_PATH,
    MUTATION_CASE_IDS,
    run_failure_matrix,
    validate_repository_record,
)

ROOT = Path(__file__).resolve().parent.parent


class HarnessDecisionPacketManifestPocTests(unittest.TestCase):
    def test_all_manifest_mutations_fail_closed(self) -> None:
        results = run_failure_matrix(ROOT)
        self.assertEqual(MUTATION_CASE_IDS, [item["caseId"] for item in results])
        self.assertTrue(all(item["status"] == "rejected" for item in results))

    def test_repository_record_replays_canonical_manifest(self) -> None:
        record = validate_repository_record(ROOT)
        self.assertEqual("verified-zero-model-thirteen-scenario-binding-and-atomic-manifest-mechanism-only", record["status"])
        self.assertTrue((ROOT / EXPECTED_MANIFEST_PATH).is_file())

    def test_acceptance_remains_partial_and_counts_remain_46_15_0(self) -> None:
        acceptance = json.loads((ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8"))
        criterion = next(item for item in acceptance["acceptanceCriteria"] if item["id"] == "acceptance.decision-ready-consumer-projection")
        self.assertEqual("partial", criterion["assessment"])
        self.assertIn("evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09", criterion["evidenceIds"])
        counts = {state: sum(item["assessment"] == state for item in acceptance["acceptanceCriteria"]) for state in ("verified", "partial", "planned")}
        self.assertEqual({"verified": 46, "partial": 15, "planned": 0}, counts)
```

- [ ] **Step 2: Run the integration test and confirm missing-artifact failures**

```powershell
python -B -m unittest tests.test_harness_decision_packet_manifest_poc -v
```

Expected: FAIL because the validator and evidence artifacts do not exist.

- [ ] **Step 3: Generate outside the repository, inspect, and add the canonical manifest fixture**

Use a temporary directory so generation does not write the repository:

```powershell
$manifestTemp = Join-Path ([System.IO.Path]::GetTempPath()) 'harness-decision-packet-thirteen-scenario-manifest.json'
python -B scripts/build_harness_decision_packet_manifest.py --output $manifestTemp
python -B -c "import json,sys; p=json.load(open(sys.argv[1],encoding='utf-8')); assert p['scenarioCount']==13; assert len(p['entries'])==13; assert all(x['selectedRoute'] is None for x in p['entries']); print(p['manifestSha256'])" $manifestTemp
```

Inspect the full temporary JSON, then add the exact canonical bytes to `tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json` with `apply_patch`. Re-run the builder to stdout and assert byte equality with the checked fixture.

- [ ] **Step 4: Implement the dated repository validator and mutation matrix**

Define these exact case IDs and expected codes:

```python
EXPECTED_ERROR_CODES = {
    "binding-scenario-missing": "binding-scenario-set-drift",
    "binding-scenario-extra": "binding-scenario-set-drift",
    "binding-scenario-reordered": "binding-scenario-set-drift",
    "binding-source-redirected": "binding-source-path-drift",
    "binding-pointer-malformed": "binding-pointer-invalid",
    "binding-pointer-unresolved": "binding-pointer-unresolved",
    "binding-identity-mismatch": "binding-scenario-identity-mismatch",
    "ops-pointer-removed": "binding-scenario-identity-mismatch",
    "document-level-promoted": "document-level-identity-promotion",
    "aggregate-identity-drift": "binding-aggregate-identity-drift",
    "document-level-identity-appears": "document-level-identity-promotion",
    "authority-digest-drift": "authority-source-digest-drift",
    "source-digest-drift": "evidence-source-digest-drift",
    "manifest-entry-removed": "manifest-entry-set-drift",
    "manifest-entry-reordered": "manifest-entry-order-drift",
    "manifest-digest-drift": "manifest-digest-mismatch",
    "atomic-output-preserved": "batch-binding-failed",
}
```

Implement the replay loop with this result contract:

```python
def run_failure_matrix(root: Path) -> list[dict[str, str]]:
    actions: dict[str, Callable[[], None]] = {
        "binding-scenario-missing": mutate_binding_scenario_missing,
        "binding-scenario-extra": mutate_binding_scenario_extra,
        "binding-scenario-reordered": mutate_binding_scenario_reordered,
        "binding-source-redirected": mutate_binding_source_redirected,
        "binding-pointer-malformed": mutate_binding_pointer_malformed,
        "binding-pointer-unresolved": mutate_binding_pointer_unresolved,
        "binding-identity-mismatch": mutate_binding_identity_mismatch,
        "ops-pointer-removed": mutate_ops_pointer_removed,
        "document-level-promoted": mutate_document_level_promoted,
        "aggregate-identity-drift": mutate_aggregate_identity_drift,
        "document-level-identity-appears": mutate_document_level_identity_appears,
        "authority-digest-drift": mutate_authority_digest_drift,
        "source-digest-drift": mutate_source_digest_drift,
        "manifest-entry-removed": mutate_manifest_entry_removed,
        "manifest-entry-reordered": mutate_manifest_entry_reordered,
        "manifest-digest-drift": mutate_manifest_digest_drift,
        "atomic-output-preserved": verify_atomic_output_preserved,
    }
    results: list[dict[str, str]] = []
    for case_id in MUTATION_CASE_IDS:
        expected = EXPECTED_ERROR_CODES[case_id]
        try:
            actions[case_id]()
        except (DecisionPacketError, BatchBindingError) as exc:
            observed = exc.code
            if (
                case_id != "atomic-output-preserved"
                and isinstance(exc, BatchBindingError)
                and exc.issues
            ):
                observed = str(exc.issues[0]["code"])
            results.append({
                "caseId": case_id,
                "status": "rejected" if observed == expected else "wrong-error",
                "expectedCode": expected,
                "observedCode": observed,
            })
        else:
            results.append({
                "caseId": case_id,
                "status": "accepted",
                "expectedCode": expected,
                "observedCode": "none",
            })
    return results
```

Each `mutate_*` function creates its own temporary root, copies the exact current authority, binding-registry, and relevant source files, performs only the named mutation, then calls the public validator. `validate_repository_record` must replay the checked manifest, independently reproduce all thirteen packet digests, verify zero execution counters and false boundaries, and require exact design/documentation/fixture/authority paths and SHA-256 digests.

- [ ] **Step 5: Add the evidence record and human-readable result**

The machine record uses:

```json
{
  "schema": 1,
  "id": "harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09",
  "date": "2026-08-09",
  "status": "verified-zero-model-thirteen-scenario-binding-and-atomic-manifest-mechanism-only",
  "scenarioCount": 13,
  "bindingCounts": {"scenarioRecord": 11, "documentLevelSupport": 2},
  "selectedRoute": null,
  "acceptanceAssessment": "partial",
  "acceptanceInventory": {"verified": 46, "partial": 15, "planned": 0}
}
```

Use these additional exact top-level fields in the record:

```json
[
  "design", "plan", "documentation", "manifestFixture", "bindingRegistry",
  "schemas", "scripts", "authorityBindings", "manifestSha256",
  "mutationResults", "executionCounters", "claimBoundary", "authorityBoundary"
]
```

Bind `design` to `docs/superpowers/specs/2026-08-08-harness-decision-packet-thirteen-scenario-manifest-design.md` and `plan` to `docs/superpowers/plans/2026-08-09-harness-decision-packet-thirteen-scenario-manifest.md`. `schemas` and `scripts` are exact path/SHA-256 arrays. `authorityBindings` contains semantic, coverage, scheduler, acceptance, and binding-registry public bindings. `mutationResults` equals `run_failure_matrix(root)`. Every execution counter is zero; every claim and lifecycle authorization value is false. The Markdown result must state exactly what the local mechanism proves and list every natural-language, task-time, behavior, value, cross-host, production, release, and residual-gap non-claim.

- [ ] **Step 6: Preserve the acceptance posture without mutating its frozen v1 authority**

Do not modify `registry/program-acceptance-map.json` in this slice. Live
regression proved that its raw digest is part of the frozen packet-v1 fixture
and the 2026-08-08 core PoC authority binding. Appending the new evidence would
make the existing immutable v1 packet cease to represent current authority,
while refreshing that historical fixture/evidence or allowing historical
acceptance bindings would violate stronger compatibility and authority gates.

Keep the new evidence as an independently governed registry record, checked
fixture, documentation surface, and required local-verifier input. It is not
registered as acceptance-map evidence in this slice. Require the existing
criterion to remain `partial`, the inventory to remain 46 verified / 15 partial
/ 0 planned, and the acceptance-map bytes to remain unchanged. A future change
to make the acceptance authority appendable must use a separately designed,
versioned binding/migration; it must not silently refresh historical packet
evidence or promote a stale authority binding.

The deferred evidence entry that must not be appended in this slice is:

```json
{
  "id": "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09",
  "path": "registry/harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09.json",
  "kind": "pure-zero-model-thirteen-scenario-heterogeneous-source-binding-packet-v2-and-atomic-summary-manifest-no-live-selection-behavior-value-portability-production-release-or-residual-gap-proof",
  "asOf": "2026-08-09",
  "supports": ["acceptance.decision-ready-consumer-projection"]
}
```

Do not append that evidence ID to the existing criterion. Record this
non-registration boundary in the machine evidence, human-readable result,
goal-mode prompt, and continuation so repository-verified mechanism evidence is
not confused with acceptance-map admission.

- [ ] **Step 7: Update plan, goal-mode prompt, and continuation**

Append one dated checkpoint to `docs/strategy/RESEARCH-AND-POC-PLAN.md` and `docs/operations/CONTINUATION.md`. Replace the goal prompt's current decision-packet section so it states:

```text
All thirteen current coverage scenarios now have zero-model packet-v2 binding.
Eleven have exact scenario-record identity; SE-ARCH-DESIGN-01 and
SE-VERIFY-SECURE-01 remain document-level support under SE-E2E-THIN-01.
The atomic manifest stores digests, not packet bodies, and no route is selected.
This is deterministic mechanism evidence only; acceptance remains partial and
46 verified / 15 partial / 0 planned remains unchanged.
```

State that the next task-time, live-host, Plugin, candidate, behavior/value, and release transitions remain behind their existing natural-task and authorization gates. Re-run the README search and leave README unchanged if it still contains no single-scenario claim.

- [ ] **Step 8: Integrate the focused validator into `scripts/verify.py`**

Import:

```python
from validate_harness_decision_packet_manifest_poc import (
    validate_repository_record as validate_harness_decision_packet_manifest_poc,
)
```

Add every new schema, registry, script, fixture, evidence, documentation, the approved design spec, and this plan file to `REQUIRED_FILES`. Call `validate_harness_decision_packet_manifest_poc(ROOT)` immediately after the v1 core validator.

The production verifier must execute the focused validator on every real
`verify()` call. In `tests/test_verify_integration.py`, unrelated mutation
helpers that repeatedly invoke the whole verifier may patch only this expensive
Task 4 validator to a side-effect-free stub; add one dedicated integration
regression proving an ordinary `verify()` call invokes the real Task 4 runner
exactly once. Keep the dedicated validator CLI and repository-record/failure-
matrix tests as independent full replays. This test-only isolation prevents the
17-case matrix from being multiplied across hundreds of unrelated verifier
mutation cases without adding a production cache or skip path.

- [ ] **Step 9: Run focused verification**

```powershell
python -B -m unittest tests.test_harness_decision_packet tests.test_harness_scenario_evidence_binding tests.test_harness_decision_packet_v2 tests.test_harness_decision_packet_manifest tests.test_harness_decision_packet_core_poc tests.test_harness_decision_packet_manifest_poc -v
python -B scripts/validate_harness_decision_packet_manifest_poc.py
```

Expected: all focused tests PASS; the validator prints the verified zero-model status and all mutation cases report `rejected` with their expected codes.

- [ ] **Step 10: Run repository-wide local verification**

```powershell
python -B -m unittest discover -s tests -q
python -B scripts/verify.py
git diff --check
```

Expected: full unittest suite PASS, `Agent Autonomy Harness validation passed.`, and no whitespace errors. Do not substitute GitHub Actions for these checks.

- [ ] **Step 11: Review claims and repository posture before commit**

```powershell
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse --abbrev-ref --symbolic-full-name '@{u}'
git rev-list --left-right --count HEAD...origin/main
git diff --stat
git diff -- registry/program-acceptance-map.json docs/strategy/RESEARCH-AND-POC-PLAN.md docs/operations/CURRENT-GOAL-MODE-PROMPT.md docs/operations/CONTINUATION.md
```

Require `main`, expected upstream `origin/main`, no unrelated dirty files, no criterion promotion, no count change, no live-task/behavior/value/production/release claim, and only the planned slice in the diff.

- [ ] **Step 12: Commit the evidence and integration slice for review**

```powershell
git add -- tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json scripts/validate_harness_decision_packet_manifest_poc.py tests/test_harness_decision_packet_manifest_poc.py registry/harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09.json docs/strategy/HARNESS-DECISION-PACKET-THIRTEEN-SCENARIO-MANIFEST-POC-2026-08-09.md registry/program-acceptance-map.json docs/strategy/RESEARCH-AND-POC-PLAN.md docs/operations/CURRENT-GOAL-MODE-PROMPT.md docs/operations/CONTINUATION.md scripts/verify.py
git diff --cached --check
git commit -m "feat: verify thirteen-scenario decision manifests"
```

After the task review and final whole-slice review are clean, the controller runs `git push origin main` and `python -B scripts/verify.py`. Finally require `HEAD == origin/main`, ahead/behind `0/0`, a clean worktree, and a passing post-push verifier. Report this mechanism slice as verified only within its zero-model claim ceiling; do not mark the overall Harness program or goal complete.

---

## Final whole-slice review resolution: exact JSON and JSON Pointer conformance

The final review found four cross-layer strictness gaps that must close before
push:

1. request, packet-v2 binding, authorization, and projection validation must
   use JSON-type-strict comparison so Python boolean/number equality cannot
   satisfy a different JSON Schema type;
2. the binding registry runtime validator must enforce the schema's exact
   integer schema value, non-empty/status constraints, and date shape;
3. JSON Pointer resolution must reject invalid `~` escapes and array indices
   with leading zeroes while preserving the existing non-root boundary and
   typed `binding-pointer-invalid` error; and
4. the repository PoC evidence validator must use type-strict checks for its
   schema, counts, counters, boundaries, and other exact record projections.

Add focused adversarial tests for each reviewed example. Keep strict JSON
comparison in a shared low-level packet helper when it avoids divergent
implementations, but do not weaken schema shape, typed errors, authority
binding, or claim ceilings. After the Task 1 and Task 2 repairs, regenerate the
plan-bound Task 4 record/document digests, rerun focused/full/verifier checks,
and return the complete range to final review before push.

### Final review round 2: stable validation before Python operations

All user/source JSON values must be type-guarded before set/dictionary
membership, hashing, counting, or other operations that can raise native
`TypeError`. Public CLIs must convert such invalid request/binding values into
their stable `DecisionPacketError` envelope and exit 2, never a traceback.

JSON array indices that pass ASCII syntax may be arbitrarily long. Check bounds
by length/lexicographic comparison (or an equivalently bounded method) before
any integer conversion, so Python's large-integer digit limit cannot leak a
native `ValueError`. Direct resolution and completeness traversal must retain
typed `binding-pointer-invalid`/`binding-pointer-unresolved` behavior. Add
adversarial unhashable membership and 4301-digit index tests, then refresh the
Task 4 evidence bindings and repeat the review/verification sequence.
