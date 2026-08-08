# Harness Decision Packet Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, source-bound decision-packet interface that lets an Agent inspect one governed human-AI collaboration scenario without promoting static evidence into execution, behavior, value, portability, production, or residual-gap claims.

**Architecture:** A focused Python library validates a structured request, binds current repository authorities and original evidence, builds a six-route decision packet, and validates it independently before canonical JSON serialization. A thin stdout-first CLI and repository validator reuse the library; current policy, plan, acceptance, goal-mode, README, continuation, and closeout surfaces bind the resulting mechanism evidence without becoming alternate decision logic.

**Tech Stack:** Python 3 standard library (`argparse`, `copy`, `hashlib`, `json`, `pathlib`, `typing`, `unittest`), JSON Schema Draft 2020-12 documents, Markdown, existing repository JSON registries, and `scripts/verify.py` integration.

## Global Constraints

- Work directly in `C:\Projects\agent-autonomy-harness` on `main`; do not create a branch or worktree for this sequential mainline slice.
- Preserve `plugin-compatible + manager-agnostic + release-not-eligible` exactly.
- The portable core must not depend on CC Switch; CC Switch and host-native plugin managers retain their separately owned lifecycle scopes.
- Do not install, enable, invoke, connect an account, dispatch a model, publish, release, delete, or mutate CC Switch or a consumer environment.
- Keep `46 verified / 15 partial / 0 planned`; `acceptance.decision-ready-consumer-projection` remains `partial`.
- `GEN-RESEARCH-01` is the only positive vertical-slice scenario in version one.
- Preserve route classes `N`, `O`, `E`, `C`, `H`, and `R`, including `unassessed` and `not-eligible-no-residual-gap`.
- A portfolio or mechanism packet has `selectedRoute: null` and cannot claim task-time execution.
- Request data cannot grant its own authority. Activation authority is a reference to independent evidence, not a boolean flag.
- Historical `registry/capabilities.json`, `registry/routing.json`, `registry/scenarios.json`, `registry/skills.json`, and `release-manifest.json` remain deprecated transition evidence, never current route authority.
- Use canonical JSON with `ensure_ascii=False`, `sort_keys=True`, and `separators=(",", ":")`; compute SHA-256 over the packet body without `packetSha256`.
- Default CLI behavior writes only to stdout. Repository writes in this plan use `apply_patch`.
- Run targeted local tests before repository-wide verification. GitHub Actions is optional repetition, not sole acceptance authority.

---

## File Structure

**Create:**

- `schemas/harness-decision-request-v1.schema.json` — `DecisionRequest` structure.
- `schemas/harness-decision-packet-v1.schema.json` — `DecisionPacket` structure.
- `scripts/harness_decision_packet.py` — pure contracts, authority loading, construction, validation, and canonical serialization.
- `scripts/build_harness_decision_packet.py` — thin stdout-first CLI.
- `scripts/validate_harness_decision_packet_core_poc.py` — repository evidence and failure-matrix validator.
- `tests/test_harness_decision_packet.py` — focused contract, authority, builder, validator, and CLI tests.
- `tests/test_harness_decision_packet_core_poc.py` — repository integration and evidence replay tests.
- `tests/fixtures/harness-decision-request-gen-research-01.json` — positive request.
- `tests/fixtures/harness-decision-packet-gen-research-01.json` — final canonical packet.
- `registry/harness-decision-packet-core-poc-2026-08-08.json` — dated mechanism evidence.
- `docs/strategy/HARNESS-DECISION-PACKET-CORE-POC-2026-08-08.md` — claim and authority boundary.

**Modify:**

- `docs/superpowers/specs/2026-08-08-harness-decision-packet-core-design.md`
- `registry/skill-portfolio-current-authority.json`
- `registry/portfolio-tasktime-projection-contract-2026-08-06.json`
- `scripts/validate_portfolio_tasktime_projection_contract.py`
- `tests/test_portfolio_tasktime_projection_contract.py`
- `registry/program-acceptance-map.json`
- `registry/program-final-closeout-readiness-reconciliation-2026-07-28.json`
- `scripts/validate_program_final_closeout_readiness_reconciliation.py`
- `tests/test_program_final_closeout_readiness_reconciliation.py`
- `docs/strategy/RESEARCH-AND-POC-PLAN.md`
- `docs/operations/CURRENT-GOAL-MODE-PROMPT.md`
- `docs/operations/CONTINUATION.md`
- `README.md` and `README.zh-CN.md`
- `scripts/verify.py`

---

### Task 1: Define request and packet contracts

**Files:**
- Create: `schemas/harness-decision-request-v1.schema.json`
- Create: `schemas/harness-decision-packet-v1.schema.json`
- Create: `scripts/harness_decision_packet.py`
- Create: `tests/test_harness_decision_packet.py`
- Create: `tests/fixtures/harness-decision-request-gen-research-01.json`
- Modify: `docs/superpowers/specs/2026-08-08-harness-decision-packet-core-design.md`

**Interfaces:**
- Consumes: Python dictionaries loaded from repository JSON.
- Produces: `DecisionPacketError`, `canonical_json_bytes(value)`, `canonical_sha256(value)`, and `validate_decision_request(request)`.

- [ ] **Step 1: Add the exact positive request fixture**

```json
{
  "schema": 1,
  "requestId": "fixture.gen-research-01",
  "scenarioId": "GEN-RESEARCH-01",
  "evidenceLane": "portfolio-curation",
  "expectedSemanticAuthorityId": "skill-portfolio-current-authority-v1",
  "observedAvailability": null,
  "taskBinding": null,
  "currentCapabilityGap": null,
  "activationAuthority": null
}
```

- [ ] **Step 2: Write failing request-contract tests**

Start `tests/test_harness_decision_packet.py` with:

```python
import json
from pathlib import Path
import unittest

from scripts.harness_decision_packet import (
    DecisionPacketError,
    canonical_sha256,
    validate_decision_request,
)

ROOT = Path(__file__).resolve().parent.parent
REQUEST_PATH = Path("tests/fixtures/harness-decision-request-gen-research-01.json")


class HarnessDecisionPacketContractTests(unittest.TestCase):
    def load_request(self) -> dict[str, object]:
        return json.loads((ROOT / REQUEST_PATH).read_text(encoding="utf-8"))

    def test_portfolio_request_is_valid_and_canonical(self) -> None:
        request = self.load_request()
        validate_decision_request(request)
        self.assertEqual(64, len(canonical_sha256(request)))

    def test_boolean_activation_authority_is_rejected(self) -> None:
        request = self.load_request()
        request["activationAuthority"] = True
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-activation-authority", raised.exception.code)

    def test_unknown_request_field_is_rejected(self) -> None:
        request = self.load_request()
        request["selectedSkill"] = "skill.curated.grill-with-docs"
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-request-shape", raised.exception.code)
```

- [ ] **Step 3: Confirm the missing module failure**

Run:

```powershell
python -B -m unittest tests.test_harness_decision_packet.HarnessDecisionPacketContractTests -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.harness_decision_packet'`.

- [ ] **Step 4: Add both Draft 2020-12 schemas**

The request schema uses `additionalProperties: false` and requires exactly:

```json
[
  "schema",
  "requestId",
  "scenarioId",
  "evidenceLane",
  "expectedSemanticAuthorityId",
  "observedAvailability",
  "taskBinding",
  "currentCapabilityGap",
  "activationAuthority"
]
```

Use lanes `portfolio-curation`, `mechanism-validation`, and `task-time`. Define nullable objects with these required fields:

```text
observedAvailability: asOf, host, availableRouteClasses, evidencePaths
taskBinding: taskId, goal, target, verificationSurface
currentCapabilityGap: requiredCapability, observedLimitation, evidencePaths
activationAuthority: evidencePath, scope
```

The packet schema requires `schema`, `packetId`, `authorityBinding`, `request`, `sourceEvidence`, `routeCoverage`, `fallbackOrder`, `decisionState`, `selectedRoute`, `authorizationGates`, `claimBoundary`, `recheckTriggers`, `projectionBoundary`, and `packetSha256`. `routeCoverage` requires exactly `N`, `O`, `E`, `C`, `H`, and `R`.

- [ ] **Step 5: Implement the contract foundation**

Create `scripts/harness_decision_packet.py` with:

```python
#!/usr/bin/env python3
"""Build and validate source-bound Harness decision packets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ROUTE_CLASSES = ("N", "O", "E", "C", "H", "R")
EVIDENCE_LANES = {"portfolio-curation", "mechanism-validation", "task-time"}
REQUEST_FIELDS = {
    "schema", "requestId", "scenarioId", "evidenceLane",
    "expectedSemanticAuthorityId", "observedAvailability", "taskBinding",
    "currentCapabilityGap", "activationAuthority",
}


class DecisionPacketError(ValueError):
    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "status": "error", "code": self.code, "message": str(self)
        }
        if self.path is not None:
            result["path"] = self.path
        return result


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
```

Implement `validate_decision_request(request: dict[str, Any]) -> None` to reject unknown fields, require schema 1 and non-empty IDs, validate the lane and each nullable object, reject boolean activation authority, and reject any solution-selection field because it is outside `REQUEST_FIELDS`.

- [ ] **Step 6: Run the contract tests**

```powershell
python -B -m unittest tests.test_harness_decision_packet.HarnessDecisionPacketContractTests -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit the contract foundation**

```powershell
git add -- schemas/harness-decision-request-v1.schema.json schemas/harness-decision-packet-v1.schema.json scripts/harness_decision_packet.py tests/test_harness_decision_packet.py tests/fixtures/harness-decision-request-gen-research-01.json docs/superpowers/specs/2026-08-08-harness-decision-packet-core-design.md
git diff --cached --check
git commit -m "feat: define harness decision packet contracts"
```

---

### Task 2: Bind current authority and original evidence

**Files:**
- Modify: `scripts/harness_decision_packet.py`
- Modify: `tests/test_harness_decision_packet.py`

**Interfaces:**
- Consumes: `validate_decision_request(request)`.
- Produces: `load_authority_bundle(root, request)`, `validate_authority_bundle(bundle, request)`, and `validate_bound_source_digests(root, bundle)`.

- [ ] **Step 1: Write failing authority tests**

```python
from scripts.harness_decision_packet import (
    load_authority_bundle,
    validate_authority_bundle,
)


class HarnessDecisionPacketAuthorityTests(HarnessDecisionPacketContractTests):
    def test_current_gen_research_authority_reopens_original_evidence(self) -> None:
        request = self.load_request()
        bundle = load_authority_bundle(ROOT, request)
        validate_authority_bundle(bundle, request)
        self.assertEqual("GEN-RESEARCH-01", bundle["scenario"]["scenarioId"])
        self.assertEqual(
            ["registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"],
            [item["path"] for item in bundle["sourceEvidence"]],
        )
        self.assertFalse(
            bundle["semanticAuthority"]["document"]["legacyAdaptedRelease"]
            ["routingProjectionCurrentAuthority"]
        )

    def test_unknown_scenario_fails_closed(self) -> None:
        request = self.load_request()
        request["scenarioId"] = "GEN-UNKNOWN-01"
        with self.assertRaises(DecisionPacketError) as raised:
            load_authority_bundle(ROOT, request)
        self.assertEqual("unknown-scenario", raised.exception.code)

    def test_expected_authority_id_must_match(self) -> None:
        request = self.load_request()
        request["expectedSemanticAuthorityId"] = "stale-authority"
        with self.assertRaises(DecisionPacketError) as raised:
            load_authority_bundle(ROOT, request)
        self.assertEqual("semantic-authority-id-mismatch", raised.exception.code)
```

- [ ] **Step 2: Confirm missing-interface failures**

```powershell
python -B -m unittest tests.test_harness_decision_packet.HarnessDecisionPacketAuthorityTests -v
```

Expected: FAIL because the authority functions are not defined.

- [ ] **Step 3: Implement safe source loading**

Add constants:

```python
SEMANTIC_AUTHORITY_PATH = Path("registry/skill-portfolio-current-authority.json")
COVERAGE_PATH = Path("registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json")
SCHEDULER_PATH = Path("registry/portfolio-tasktime-projection-contract-2026-08-06.json")
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
```

Implement `_resolve_repository_path(root, value)` to reject absolute paths, `..`, and resolved paths outside `root.resolve()` with `unsafe-source-path`. Implement `_load_json(root, relative, missing_code)` with typed missing, UTF-8, and JSON errors without exposing file content.

- [ ] **Step 4: Implement the stable authority bundle**

Return:

```python
{
    "semanticAuthority": {"path": str, "id": str, "sha256": str, "document": dict},
    "coverage": {"path": str, "id": str, "sha256": str, "document": dict},
    "scheduler": {"path": str, "id": str, "sha256": str, "document": dict},
    "acceptance": {"path": str, "id": str, "sha256": str, "document": dict},
    "scenario": dict,
    "sourceEvidence": [
        {"path": str, "id": str, "sha256": str, "status": str, "document": dict}
    ],
}
```

Require current IDs and statuses, exactly six route classes, safe original evidence paths, `legacyAdaptedRelease.routingProjectionCurrentAuthority is False`, no CC Switch portable-core dependency, current plugin posture, and false release eligibility.

- [ ] **Step 5: Add digest-drift coverage**

Build a bundle, copy its bound files to a temporary root, change the original evidence after bundle construction, and require `validate_bound_source_digests` to raise `evidence-source-digest-drift`. The packet binds the current digest; existing source-specific validators remain responsible for the original record's internal semantics.

- [ ] **Step 6: Run focused authority tests**

```powershell
python -B -m unittest tests.test_harness_decision_packet.HarnessDecisionPacketAuthorityTests -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit authority binding**

```powershell
git add -- scripts/harness_decision_packet.py tests/test_harness_decision_packet.py
git diff --cached --check
git commit -m "feat: bind decision packets to current authority"
```

---

### Task 3: Build, validate, and expose the deterministic packet

**Files:**
- Modify: `scripts/harness_decision_packet.py`
- Create: `scripts/build_harness_decision_packet.py`
- Modify: `tests/test_harness_decision_packet.py`

**Interfaces:**
- Consumes: `load_authority_bundle(root, request)` and canonical helpers.
- Produces: `build_decision_packet(root, request)`, `validate_decision_packet(root, packet)`, `serialize_decision_packet(packet)`, and CLI `main(argv=None)`.

- [ ] **Step 1: Write failing positive packet tests**

```python
from scripts.harness_decision_packet import (
    build_decision_packet,
    serialize_decision_packet,
    validate_decision_packet,
)


class HarnessDecisionPacketBuildTests(HarnessDecisionPacketContractTests):
    def test_gen_research_packet_preserves_all_evidence_states(self) -> None:
        packet = build_decision_packet(ROOT, self.load_request())
        validate_decision_packet(ROOT, packet)
        self.assertEqual("coverage-packet-only", packet["decisionState"])
        self.assertIsNone(packet["selectedRoute"])
        self.assertEqual({"N", "O", "E", "C", "H", "R"}, set(packet["routeCoverage"]))
        self.assertEqual("unassessed", packet["routeCoverage"]["O"]["state"])
        self.assertEqual("unassessed", packet["routeCoverage"]["E"]["state"])
        self.assertEqual(
            "not-eligible-no-residual-gap",
            packet["routeCoverage"]["R"]["state"],
        )
        self.assertEqual(["N", "C", "H"], packet["fallbackOrder"])
        self.assertFalse(any(packet["claimBoundary"].values()))

    def test_repeated_build_is_byte_identical(self) -> None:
        request = self.load_request()
        first = serialize_decision_packet(build_decision_packet(ROOT, request))
        second = serialize_decision_packet(build_decision_packet(ROOT, request))
        self.assertEqual(first, second)
```

- [ ] **Step 2: Confirm missing-interface failures**

```powershell
python -B -m unittest tests.test_harness_decision_packet.HarnessDecisionPacketBuildTests -v
```

Expected: FAIL because build, validate, and serialize functions are not defined.

- [ ] **Step 3: Implement packet construction**

Use:

```python
ROUTE_NAMES = {
    "N": "native",
    "O": "official-or-runtime-owned",
    "E": "reviewed-external",
    "C": "composition",
    "H": "accountable-human-control",
    "R": "residual-or-repository-authored",
}
```

Remove raw documents from `authorityBinding`, retaining `path`, `id`, and `sha256`. Emit original `sourceEvidence` with `path`, `id`, `sha256`, `status`, and historical `authorityBoundary` when present. Use this positive-fixture authorization result:

```python
{
    "install": False,
    "enable": False,
    "connectAccount": False,
    "executeCandidate": False,
    "dispatchModel": False,
    "publish": False,
    "release": False,
    "mutateCcSwitch": False,
    "mutateConsumer": False,
}
```

Copy the current coverage record's `claimBoundary` and require every value false. Copy its `recheckTriggers`. Emit:

```python
"projectionBoundary": {
    "derivedProjectionNotAuthority": True,
    "legacyRoutingIsCurrentAuthority": False,
    "portableCoreDependsOnCcSwitch": False,
    "pluginReleaseEligible": False,
}
```

Use these version-one decision states, always with `selectedRoute: null`:

```text
portfolio-curation -> coverage-packet-only
mechanism-validation -> mechanism-evidence-only
task-time with null taskBinding -> needs-task-binding
task-time with null currentCapabilityGap -> needs-current-capability-gap
task-time with null observedAvailability -> needs-live-availability
task-time with null activationAuthority -> needs-activation-authority
otherwise task-time -> needs-human-judgment
```

Compute `packetSha256` from the packet body excluding the digest. `serialize_decision_packet` returns canonical bytes plus one newline; the digest excludes the newline.

- [ ] **Step 4: Implement independent packet validation**

`validate_decision_packet(root, packet)` must reopen authority and source paths, compare IDs and digests, compare route states/candidate IDs/evidence ceilings/fallback with the scenario, validate the exact top-level schema, recompute the packet digest, and raise these codes when applicable:

```text
route-class-coverage-incomplete
unassessed-route-promotion
residual-gap-promotion
portfolio-selected-route
task-time-route-selection
claim-boundary-promotion
fallback-order-drift
deprecated-routing-authority-promotion
historical-authority-promotion
portable-core-dependency-promotion
packet-digest-mismatch
```

- [ ] **Step 5: Implement the thin CLI**

Create `scripts/build_harness_decision_packet.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from harness_decision_packet import (
    DecisionPacketError,
    ROOT,
    build_decision_packet,
    serialize_decision_packet,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        packet = build_decision_packet(args.root, request)
    except (DecisionPacketError, OSError, json.JSONDecodeError) as exc:
        error = exc.as_dict() if isinstance(exc, DecisionPacketError) else {
            "status": "error",
            "code": "request-read-failed",
            "message": str(exc),
        }
        sys.stderr.buffer.write(
            json.dumps(error, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
        )
        return 2
    sys.stdout.buffer.write(serialize_decision_packet(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add subprocess tests requiring exit 0, empty stderr, valid canonical stdout, and unchanged `git status --short`. Invalid input requires exit 2, empty stdout, and machine-readable stderr.

- [ ] **Step 6: Run focused tests and the CLI**

```powershell
python -B -m unittest tests.test_harness_decision_packet -v
python -B scripts/build_harness_decision_packet.py tests/fixtures/harness-decision-request-gen-research-01.json
```

Expected: tests PASS; CLI prints one packet with `selectedRoute: null` and performs no repository write.

- [ ] **Step 7: Commit the working interface**

```powershell
git add -- scripts/harness_decision_packet.py scripts/build_harness_decision_packet.py tests/test_harness_decision_packet.py
git diff --cached --check
git commit -m "feat: build source-bound harness decision packets"
```

---

### Task 4: Add the fourteen-case fail-closed harness

**Files:**
- Create: `scripts/validate_harness_decision_packet_core_poc.py`
- Create: `tests/test_harness_decision_packet_core_poc.py`
- Modify: `tests/test_harness_decision_packet.py`

**Interfaces:**
- Consumes: `build_decision_packet`, `validate_decision_packet`, and `DecisionPacketError`.
- Produces: `MUTATION_CASE_IDS`, `run_failure_matrix(root)`, and later `validate_repository_record(root)`.

- [ ] **Step 1: Write the failing failure-matrix test**

```python
from pathlib import Path
import unittest

from scripts.validate_harness_decision_packet_core_poc import (
    MUTATION_CASE_IDS,
    run_failure_matrix,
)

ROOT = Path(__file__).resolve().parent.parent


class HarnessDecisionPacketCorePocTests(unittest.TestCase):
    def test_all_fourteen_mutations_fail_closed(self) -> None:
        results = run_failure_matrix(ROOT)
        self.assertEqual(MUTATION_CASE_IDS, [item["caseId"] for item in results])
        self.assertTrue(all(item["status"] == "rejected" for item in results))
```

- [ ] **Step 2: Confirm the missing module failure**

```powershell
python -B -m unittest tests.test_harness_decision_packet_core_poc -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the exact failure inventory**

```python
MUTATION_CASE_IDS = [
    "unknown-scenario",
    "semantic-authority-id-drift",
    "original-evidence-missing",
    "original-evidence-digest-drift",
    "route-class-removed",
    "unassessed-route-promoted",
    "residual-route-promoted",
    "portfolio-selected-route",
    "claim-boundary-promoted",
    "fallback-order-drift",
    "deprecated-routing-restored",
    "task-time-route-selected",
    "historical-authority-overrides-current",
    "portable-core-dependency-promoted",
]
```

Map them to these error codes in the same order:

```python
{
    "unknown-scenario": "unknown-scenario",
    "semantic-authority-id-drift": "semantic-authority-id-mismatch",
    "original-evidence-missing": "evidence-source-missing",
    "original-evidence-digest-drift": "evidence-source-digest-drift",
    "route-class-removed": "route-class-coverage-incomplete",
    "unassessed-route-promoted": "unassessed-route-promotion",
    "residual-route-promoted": "residual-gap-promotion",
    "portfolio-selected-route": "portfolio-selected-route",
    "claim-boundary-promoted": "claim-boundary-promotion",
    "fallback-order-drift": "fallback-order-drift",
    "deprecated-routing-restored": "deprecated-routing-authority-promotion",
    "task-time-route-selected": "task-time-route-selection",
    "historical-authority-overrides-current": "historical-authority-promotion",
    "portable-core-dependency-promoted": "portable-core-dependency-promotion",
}
```

Build the positive packet once, deep-copy inputs for pure mutations, and use a temporary copied root only for missing or changed sources. No mutation helper may write inside the repository.

- [ ] **Step 4: Add direct dangerous-promotion tests**

Add explicit tests for unassessed promotion, R promotion, a true behavior claim, deprecated routing authority, and portable-core CC Switch dependency. Each deep-copies the positive packet or authority bundle and asserts the exact error code above.

- [ ] **Step 5: Run the failure suite**

```powershell
python -B -m unittest tests.test_harness_decision_packet tests.test_harness_decision_packet_core_poc -v
```

Expected: all focused tests PASS and fourteen cases are rejected.

- [ ] **Step 6: Commit the fail-closed harness**

```powershell
git add -- scripts/validate_harness_decision_packet_core_poc.py tests/test_harness_decision_packet.py tests/test_harness_decision_packet_core_poc.py
git diff --cached --check
git commit -m "test: harden harness decision packet boundaries"
```

---

### Task 5: Bind evidence, projections, acceptance, closeout, and verification

**Files:**
- Create: `registry/harness-decision-packet-core-poc-2026-08-08.json`
- Create: `docs/strategy/HARNESS-DECISION-PACKET-CORE-POC-2026-08-08.md`
- Create: `tests/fixtures/harness-decision-packet-gen-research-01.json`
- Modify: `scripts/validate_harness_decision_packet_core_poc.py`
- Modify: `tests/test_harness_decision_packet_core_poc.py`
- Modify: `registry/skill-portfolio-current-authority.json`
- Modify: `registry/portfolio-tasktime-projection-contract-2026-08-06.json`
- Modify: `scripts/validate_portfolio_tasktime_projection_contract.py`
- Modify: `tests/test_portfolio_tasktime_projection_contract.py`
- Modify: `registry/program-acceptance-map.json`
- Modify: `registry/program-final-closeout-readiness-reconciliation-2026-07-28.json`
- Modify: `scripts/validate_program_final_closeout_readiness_reconciliation.py`
- Modify: `tests/test_program_final_closeout_readiness_reconciliation.py`
- Modify: `docs/strategy/RESEARCH-AND-POC-PLAN.md`
- Modify: `docs/operations/CURRENT-GOAL-MODE-PROMPT.md`
- Modify: `docs/operations/CONTINUATION.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `scripts/verify.py`

**Interfaces:**
- Consumes: the complete core and failure harness from Tasks 1-4.
- Produces: `validate_repository_record(root)`, one stable expected packet, dated evidence, synchronized projections, and full-verifier integration.

- [ ] **Step 1: Write failing repository integration tests**

Extend `tests/test_harness_decision_packet_core_poc.py`:

```python
import json

from scripts.validate_harness_decision_packet_core_poc import (
    EVIDENCE_PATH,
    EXPECTED_PACKET_PATH,
    validate_repository_record,
)


class HarnessDecisionPacketRepositoryIntegrationTests(unittest.TestCase):
    def test_repository_record_replays_packet_and_failures(self) -> None:
        record = validate_repository_record(ROOT)
        self.assertEqual(
            "verified-zero-model-source-bound-decision-packet-mechanism-only",
            record["status"],
        )
        self.assertTrue((ROOT / EVIDENCE_PATH).is_file())
        self.assertTrue((ROOT / EXPECTED_PACKET_PATH).is_file())

    def test_acceptance_remains_partial(self) -> None:
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criterion = next(
            item for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.decision-ready-consumer-projection"
        )
        self.assertEqual("partial", criterion["assessment"])
        self.assertIn(
            "evidence.harness-decision-packet-core-poc-2026-08-08",
            criterion["evidenceIds"],
        )
```

Run:

```powershell
python -B -m unittest tests.test_harness_decision_packet_core_poc.HarnessDecisionPacketRepositoryIntegrationTests -v
```

Expected: FAIL because evidence, expected packet, and repository validator are absent.

- [ ] **Step 2: Bind the mechanism in current semantic authority and scheduler projection**

Add to `registry/skill-portfolio-current-authority.json`:

```json
"decisionPacketCore": {
  "design": "docs/superpowers/specs/2026-08-08-harness-decision-packet-core-design.md",
  "evidence": "registry/harness-decision-packet-core-poc-2026-08-08.json",
  "status": "verified-zero-model-source-bound-decision-packet-mechanism-only",
  "primaryConsumer": "agent-or-harness",
  "naturalLanguageInterpretationProved": false,
  "liveRouteSelectionProved": false,
  "behaviorOrValueProved": false,
  "portableCoreDependsOnPluginOrManager": false
}
```

Add the same fields under `sourceBindings.decisionPacketCore` in `registry/portfolio-tasktime-projection-contract-2026-08-06.json`. Extend its validator to require equality and add `decision-packet-core-boundary-removal` to both the Python and registry mutation lists. Add a test that removes the binding and expects failure. Do not change scheduler-lane semantics.

- [ ] **Step 3: Add mechanism evidence without acceptance promotion**

Append `evidence.harness-decision-packet-core-poc-2026-08-08` to `acceptance.decision-ready-consumer-projection.evidenceIds`. Add:

```json
{
  "id": "evidence.harness-decision-packet-core-poc-2026-08-08",
  "path": "registry/harness-decision-packet-core-poc-2026-08-08.json",
  "kind": "pure-zero-model-source-bound-six-route-agent-consumable-decision-packet-and-fourteen-case-failure-injection-no-live-selection-behavior-value-portability-production-or-residual-gap-proof",
  "asOf": "2026-08-08",
  "supports": [
    "acceptance.decision-ready-consumer-projection"
  ]
}
```

Keep the criterion `partial` and every acceptance count unchanged.

- [ ] **Step 4: Update closeout and human projections with identical narrow claims**

Update closeout, plan, goal prompt, READMEs, and continuation with these exact facts:

- one structured `GEN-RESEARCH-01` request builds a deterministic packet;
- six route classes, source digests, evidence ceilings, unknowns, fallback, authorization gates, and claim limits are retained;
- fourteen mutations fail closed;
- `selectedRoute` remains null;
- no model, candidate, Plugin, manager, account, consumer, install, enablement, behavior, value, portability, production, publication, release, or residual-gap evidence follows; and
- inventory remains 46/15/0.

Keep the closeout cluster open/partial and preserve loader, task-delivery, recovery, cross-device, behavior, value, and release gaps. Extend its validator/tests to reject closeout or claim promotion.

Because this is a new public repository interface, add narrow usage to both READMEs:

```powershell
python -B scripts/build_harness_decision_packet.py tests/fixtures/harness-decision-request-gen-research-01.json
```

Label the output mechanism-only and non-executing in both languages.

- [ ] **Step 5: Generate and independently review the final packet outside the repository**

After Steps 2-4 stabilize the authority files:

```powershell
$decisionPacketTemp = Join-Path $env:TEMP 'harness-decision-packet-gen-research-01.json'
python -B scripts/build_harness_decision_packet.py tests/fixtures/harness-decision-request-gen-research-01.json > $decisionPacketTemp
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Get-Content -Raw $decisionPacketTemp
```

Independently compare paths, IDs, digests, route states, fallback, claims, and authorization gates with the current sources. Use `apply_patch` to add the exact canonical JSON as `tests/fixtures/harness-decision-packet-gen-research-01.json`; do not use a script to write the repository fixture.

- [ ] **Step 6: Add final evidence and documentation**

Create `registry/harness-decision-packet-core-poc-2026-08-08.json` containing:

- schema, ID, date, status, design, documentation, request fixture, and expected packet fixture;
- exact authority paths and IDs;
- `GEN-RESEARCH-01` route-state summary;
- `packetSha256` from the reviewed fixture;
- all fourteen mutation case IDs and expected error codes;
- zero execution counters for models, candidates, Plugins, managers, accounts, consumers, installs, enablements, and publications;
- the existing acceptance ID with `partial` assessment;
- inventory 46/15/0; and
- false claims for interpretation, invocation, delivery, behavior, value, portability, production, release eligibility, and residual gap.

Create `docs/strategy/HARNESS-DECISION-PACKET-CORE-POC-2026-08-08.md` with the same boundary.

- [ ] **Step 7: Implement repository validation**

In `validate_harness_decision_packet_core_poc.py`, define:

```python
EVIDENCE_PATH = Path("registry/harness-decision-packet-core-poc-2026-08-08.json")
EXPECTED_PACKET_PATH = Path("tests/fixtures/harness-decision-packet-gen-research-01.json")
DOCUMENTATION_PATH = Path("docs/strategy/HARNESS-DECISION-PACKET-CORE-POC-2026-08-08.md")
```

`validate_repository_record(root)` must validate identity and path bindings, rebuild and compare the expected packet, validate its digest, replay fourteen failures, require current authority/projection bindings, require the unchanged partial acceptance and 46/15/0 inventory, require matching narrow claims across all human projections and closeout, and reject any execution/value/release promotion.

- [ ] **Step 8: Integrate only the focused validator into `scripts/verify.py`**

Add:

```python
from validate_harness_decision_packet_core_poc import (
    validate_repository_record as validate_harness_decision_packet_core_poc,
)
```

Add every new schema, script, test, fixture, registry, design/plan, and strategy file to `REQUIRED_FILES`. Call `validate_harness_decision_packet_core_poc(ROOT)` beside current 2026-08 mechanism validators. Do not put construction or validation logic in `verify.py`.

- [ ] **Step 9: Run targeted integration**

```powershell
python -B -m unittest tests.test_harness_decision_packet tests.test_harness_decision_packet_core_poc tests.test_portfolio_tasktime_projection_contract tests.test_program_final_closeout_readiness_reconciliation -v
python -B scripts/validate_harness_decision_packet_core_poc.py
python -B scripts/validate_portfolio_tasktime_projection_contract.py
python -B scripts/validate_program_final_closeout_readiness_reconciliation.py
```

Expected: all PASS; fixture replay is byte-stable; acceptance remains 46/15/0.

- [ ] **Step 10: Run repository-wide local verification**

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/verify.py
git diff --check
git status --short --branch
```

Expected: full tests PASS; verifier prints `Agent Autonomy Harness validation passed.`; only intended files are dirty.

- [ ] **Step 11: Commit and push the completed mechanism slice**

```powershell
git add -- schemas scripts tests registry docs README.md README.zh-CN.md
git diff --cached --check
git commit -m "feat: add harness decision packet core"
git push origin main
git status --short --branch
git rev-list --left-right --count origin/main...HEAD
```

Expected: push succeeds, worktree is clean, ahead/behind is `0 0`.

- [ ] **Step 12: Audit the slice without closing the whole program**

Reopen the design, this plan, evidence, expected packet, acceptance criterion, closeout reconciliation, goal prompt, and continuation checkpoint. Map every design requirement to direct current evidence. Report mechanism completion separately from unproved task-time behavior, value, cross-host, production, live-plugin validation, and overall program closeout. Do not mark the overall Harness goal complete merely because this slice passes.

---

## Plan Self-Review Checklist

- Spec coverage: Tasks 1-5 cover contracts, authority, original evidence, six routes, fallback, claims, authorization, deterministic serialization, CLI, fourteen failures, evidence, projections, acceptance, closeout, READMEs, continuation, and verification.
- Scope: one `GEN-RESEARCH-01` slice; no natural-language parser, live selection, Plugin, manager, model, account, install, enablement, publication, or release work.
- Type consistency: later tasks use public names defined earlier; request fields match the clarified approved design.
- Acceptance consistency: the decision-ready criterion stays partial and inventory stays 46/15/0.
- Execution topology: sequential main-workspace execution; no branch, worktree, or parallel writer.
