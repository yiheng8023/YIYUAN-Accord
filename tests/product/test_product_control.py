from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import hmac
from io import BytesIO, StringIO
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[2]
CODEX_PLUGIN_ROOT = ROOT / "adapters/agent-autonomy-harness-codex"
CLAUDE_PLUGIN_ROOT = ROOT / "adapters/agent-autonomy-harness-claude"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import harness.control as control  # noqa: E402
from harness.continuation import _serialize_bounded  # noqa: E402
from harness.claude_reference import (  # noqa: E402
    ADAPTER_ID as CLAUDE_ADAPTER_ID,
    render_session_start_context as render_claude_session_start_context,
)
from harness.codex_reference import (  # noqa: E402
    ADAPTER_ID,
    render_session_start_context,
    session_start_hook_output,
)
from harness.control import (  # noqa: E402
    SUPPORTED_EVIDENCE_VALIDATORS,
    SUPPORTED_PRE_MEASUREMENT_VALIDATORS,
    verify_product,
)
from harness.task_validator_o1_lifecycle_suite import (  # noqa: E402
    INCREMENT_ID as O1_LIFECYCLE_INCREMENT_ID,
    VALIDATOR_KIND as O1_LIFECYCLE_VALIDATOR_KIND,
    VALIDATOR_LOCATOR as O1_LIFECYCLE_VALIDATOR_LOCATOR,
    validate_evidence as validate_o1_lifecycle_evidence,
    validate_registration as validate_o1_lifecycle_registration,
)
from harness.task_validator_o2_codex_reference import (  # noqa: E402
    INCREMENT_ID as O2_CODEX_INCREMENT_ID,
    VALIDATOR_KIND as O2_CODEX_VALIDATOR_KIND,
    VALIDATOR_LOCATOR as O2_CODEX_VALIDATOR_LOCATOR,
    validate_evidence as validate_o2_codex_evidence,
    validate_registration as validate_o2_codex_registration,
)
from harness.__main__ import main as cli_main  # noqa: E402


AUTHORITY_FILES = (
    ".github/workflows/validate.yml",
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/claude_reference.py",
    "harness/codex_reference.py",
    "harness/continuation.py",
    "harness/control.py",
    "harness/task_validator_o1_lifecycle_suite.py",
    "harness/task_validator_o2_codex_reference.py",
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "SUPPORT.zh-CN.md",
    "docs/DEMAND-TO-CAPABILITY-PROFILE.md",
    "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md",
    "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json",
    "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.1.md",
    "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.1.json",
    "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.2.md",
    "docs/CONTROLLED-CONFORMANCE-PROTOCOL-V1.2.json",
    "docs/architecture.md",
    "docs/strategy/PRODUCT-NORTH-STAR.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "docs/operations/CONTINUATION.md",
    "docs/operations/HISTORY.md",
    "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/SKILL.md",
)
FIXTURE_INCREMENT_ID = "increment.fixture-current"
FIXTURE_WORK_ID = "work.fixture-current"


def fixture_task_identity(label: str) -> str:
    return (
        "conformance-unit.public-v1:"
        + hashlib.sha256(label.encode("utf-8")).hexdigest()[:32]
    )


def fixture_private_hmac(key: bytes, domain: str, *parts: str) -> str:
    message = "\0".join((domain, *parts)).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


def fixture_private_bytes_hmac(key: bytes, domain: str, payload: bytes) -> str:
    message = domain.encode("utf-8") + b"\0" + payload
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


class ProductControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative in AUTHORITY_FILES:
            source = ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        self.reset_program_fixture()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def read_json(self, relative: str) -> dict:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def write_json(self, relative: str, value: object) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def hosted_private_authorization_source_is_unavailable(self, report: dict) -> bool:
        if (
            os.name != "nt"
            and report.get("valid") is False
            and report.get("errors")
            == ["revoked current v1.1 expiry cleanup trigger absence is unverifiable"]
            and report.get("criterionStates", {}).get("G3") is False
        ):
            return True
        return (
            os.environ.get("GITHUB_ACTIONS") == "true"
            and report.get("valid") is False
            and report.get("errors")
            in (
                ["initial binding authorization private source is unavailable"],
                ["successor binding authorization private source is unavailable"],
                [
                    "current v1.1 binding authorization private source is unavailable"
                ],
            )
            and report.get("criterionStates", {}).get("G3") is False
        )

    def reset_program_fixture(self) -> None:
        """Keep generic mutation tests independent of the live causal increment."""

        program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        program["status"] = "ready"
        program["activeIncrementId"] = None
        program["increments"] = []
        program["normativeProfileBinding"] = deepcopy(
            control.UNFROZEN_NORMATIVE_PROFILE_BINDING
        )
        self.write_json("product/program.json", program)
        registration = self.root / "product/evidence/fixture-registration.json"
        if registration.exists():
            registration.unlink()
        self.reset_acceptance_fixture()

    def initialize_fixture_repository(
        self, *, protocol_strata: list[str] | None = None
    ) -> str:
        if (self.root / ".git").is_dir():
            return subprocess.run(
                ["git", "rev-list", "--max-parents=0", "HEAD"],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        if protocol_strata is not None:
            protocol = self.read_json("docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json")
            protocol["strata"] = protocol_strata
            self.write_json("docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json", protocol)
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_DATE": "2026-08-12T02:50:00+08:00",
                "GIT_COMMITTER_DATE": "2026-08-12T02:50:00+08:00",
            }
        )
        commands = (
            ["git", "init", "--quiet"],
            ["git", "config", "user.name", "Harness Fixture"],
            ["git", "config", "user.email", "fixture@example.invalid"],
            ["git", "config", "core.autocrlf", "true"],
            [
                "git",
                "add",
                "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md",
                "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json",
                "product/program.json",
            ],
            ["git", "commit", "--quiet", "-m", "fixture authority"],
        )
        for command in commands:
            subprocess.run(
                command,
                cwd=self.root,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def reset_acceptance_fixture(self) -> None:
        """Keep generic tests independent of live outcome evidence and validators."""

        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        for criterion in acceptance["criteria"]:
            if criterion["id"] in {"O1", "O2", "O3", "O4", "O5"}:
                criterion["assessment"] = "planned"
                criterion.pop("evidence", None)
        self.write_json("product/acceptance.json", acceptance)

    def mutate(self, relative: str, callback) -> None:
        value = self.read_json(relative)
        callback(value)
        self.write_json(relative, value)

    def report(
        self,
        *,
        bind_successor: bool = True,
        auto_bind_task_validators: bool = True,
    ) -> dict:
        if not (self.root / ".git").is_dir():
            with patch.multiple(
                control,
                CURRENT_PROFILE_FREEZE_ENABLED=True,
                _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY=True,
                _normative_profile_binding_history_valid=lambda root, binding, errors: True,
                _v10_historical_authority_valid=lambda root, errors: True,
                _v11_historical_authority_valid=lambda root, errors: True,
                _frozen_v02_profile_artifacts_valid=lambda root, errors: True,
            ):
                return verify_product(self.root)
        floor = subprocess.run(
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        initial_binding_revision: str | None = None
        initial_binding_sha256: str | None = None
        initial_key_fingerprint: str | None = None
        successor_binding_revision: str | None = None
        successor_binding_sha256: str | None = None
        predecessor_revocation_revision: str | None = None
        predecessor_revocation_binding_sha256: str | None = None
        revoked_seen = False
        binding_revisions = subprocess.run(
            [
                "git",
                "log",
                "--first-parent",
                "--reverse",
                "--format=%H",
                "--",
                "product/program.json",
            ],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        for revision in binding_revisions:
            historical_program = json.loads(
                subprocess.run(
                    ["git", "show", f"{revision}:product/program.json"],
                    cwd=self.root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            binding = historical_program.get("normativeProfileBinding")
            if not isinstance(binding, dict):
                continue
            if binding.get("state") == "revoked":
                if not revoked_seen:
                    predecessor_revocation_revision = revision
                    predecessor_revocation_binding_sha256 = hashlib.sha256(
                        json.dumps(
                            binding,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                revoked_seen = True
                continue
            if binding.get("state") != "frozen":
                continue
            binding_sha256 = hashlib.sha256(
                json.dumps(
                    binding,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            if initial_binding_revision is None:
                initial_binding_revision = revision
                initial_binding_sha256 = binding_sha256
                activation = binding.get("cohortActivation")
                initial_key_fingerprint = (
                    activation.get("keyFingerprint")
                    if isinstance(activation, dict)
                    and isinstance(activation.get("keyFingerprint"), str)
                    else None
                )
            elif revoked_seen and successor_binding_revision is None:
                successor_binding_revision = revision
                successor_binding_sha256 = binding_sha256
        initial_authorization_validator_id = (
            "fixture-initial-binding-authorization"
            if initial_binding_revision is not None
            else None
        )
        authorization_validators = dict(
            control.SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS
        )
        authorization_validators["fixture-initial-binding-authorization"] = (
            lambda document, root, errors: True
        )
        authorization_validators["fixture-successor-binding-authorization"] = (
            lambda document, root, errors: document
            == {
                "kind": "successor-normative-profile-binding-authorization",
                "revision": successor_binding_revision,
                "bindingSha256": successor_binding_sha256,
                "predecessorRevocationRevision": predecessor_revocation_revision,
                "predecessorRevocationBindingSha256": predecessor_revocation_binding_sha256,
                "sourceWindowRule": control.EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_WINDOW_RULE,
            }
        )
        pre_measurement_validators = dict(
            control.SUPPORTED_PRE_MEASUREMENT_VALIDATORS
        )
        externally_bound_pre_measurement_kinds = set(pre_measurement_validators)
        current_program = self.read_json("product/program.json")
        for increment in current_program.get("increments", []):
            if not isinstance(increment, dict):
                continue
            registration_binding = increment.get("taskRegistration")
            validator_binding = (
                registration_binding.get("preMeasurementValidator")
                if isinstance(registration_binding, dict)
                else None
            )
            kind = validator_binding.get("kind") if isinstance(validator_binding, dict) else None
            locator = (
                validator_binding.get("locator")
                if isinstance(validator_binding, dict)
                else None
            )
            increment_id = increment.get("id")
            mapped = set(increment.get("acceptanceIds", [])) & {
                "O1",
                "O2",
                "O3",
                "O4",
                "O5",
            }
            if (
                auto_bind_task_validators
                and isinstance(kind, str)
                and isinstance(locator, str)
                and isinstance(increment_id, str)
                and kind not in externally_bound_pre_measurement_kinds
            ):
                existing = pre_measurement_validators.get(kind)
                existing_criteria = existing[0] if existing is not None else frozenset()
                existing_increments = existing[1] if existing is not None else frozenset()
                existing_locator = existing[2] if existing is not None else locator
                pre_measurement_validators[kind] = (
                    existing_criteria | frozenset(mapped),
                    existing_increments | frozenset({increment_id}),
                    existing_locator,
                    lambda registration, increment, criteria, root, errors: True,
                )
        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=True,
            _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY=True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
            _frozen_v02_profile_artifacts_valid=lambda root, errors: True,
            NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
            EXPECTED_V1_PROFILE_ARTIFACT_REVISION=floor,
            EXPECTED_V1_INITIAL_BINDING_REVISION=initial_binding_revision,
            EXPECTED_V1_INITIAL_BINDING_SHA256=initial_binding_sha256,
            EXPECTED_V1_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID=(
                initial_authorization_validator_id
            ),
            EXPECTED_INITIAL_AUTHORIZATION_KEY_FINGERPRINT=(
                initial_key_fingerprint
                or control.EXPECTED_INITIAL_AUTHORIZATION_KEY_FINGERPRINT
            ),
            EXPECTED_V1_SUCCESSOR_BINDING_REVISION=(
                successor_binding_revision if bind_successor else None
            ),
            EXPECTED_V1_SUCCESSOR_BINDING_SHA256=(
                successor_binding_sha256 if bind_successor else None
            ),
            EXPECTED_V1_SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID=(
                "fixture-successor-binding-authorization"
                if bind_successor and successor_binding_revision is not None
                else None
            ),
            EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION=(
                predecessor_revocation_revision
            ),
            EXPECTED_V1_PREDECESSOR_REVOCATION_BINDING_SHA256=(
                predecessor_revocation_binding_sha256
            ),
            SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS=authorization_validators,
            SUPPORTED_PRE_MEASUREMENT_VALIDATORS=pre_measurement_validators,
        ):
            return verify_product(self.root)

    def evidence_document(
        self,
        *,
        criterion_ids: object | None = None,
        validator_kind: str = "test-validator",
    ) -> dict:
        return {
            "schema": 1,
            "id": "typed-o2",
            "criterionIds": ["O2"] if criterion_ids is None else criterion_ids,
            "observedAt": "2026-08-12T03:00:00+08:00",
            "incrementId": FIXTURE_INCREMENT_ID,
            "workItemId": FIXTURE_WORK_ID,
            "source": {
                "kind": "repository-task-receipt",
                "locator": "task-receipt-001",
                "identity": "sha256:fixture",
            },
            "authority": {
                "kind": "named-accountable-human",
                "name": "fixture reviewer",
                "decision": "accepted",
                "decidedAt": "2026-08-12T03:01:00+08:00",
            },
            "result": {"accepted": True},
            "claimLimits": ["fixture only"],
            "validator": {"kind": validator_kind, "version": 1},
        }

    def validator_registry(
        self,
        validator,
        *,
        criterion_ids: frozenset[str] | None = None,
        increment_ids: frozenset[str] | None = None,
    ) -> dict:
        supported_criteria = (
            criterion_ids
            if criterion_ids is not None
            else frozenset({"O1", "O2", "O3", "O4", "O5"})
        )
        supported_increments = (
            increment_ids
            if increment_ids is not None
            else frozenset({FIXTURE_INCREMENT_ID})
        )
        program = self.read_json("product/program.json")
        locator = "harness/task_validator_fixture.py"
        for increment in program.get("increments", []):
            binding = increment.get("taskRegistration")
            validator_binding = (
                binding.get("preMeasurementValidator")
                if isinstance(binding, dict)
                else None
            )
            if isinstance(validator_binding, dict) and isinstance(
                validator_binding.get("locator"), str
            ):
                locator = validator_binding["locator"]
                break
        return {
            "test-validator": (
                supported_criteria,
                supported_increments,
                locator,
                validator,
            )
        }

    def terminal_authorization_registry(self, validator) -> dict:
        return {
            "fixture-human-authorization-validator": (
                "harness/terminal_authorization_validator_fixture.py",
                validator,
            )
        }

    def increment_fixture(self, *, state: str = "planned") -> dict:
        work_state = "completed" if state == "completed" else "planned"
        return {
            "id": FIXTURE_INCREMENT_ID,
            "state": state,
            "correctionClass": "fixture-correction",
            "observedProblem": "fixture observed problem",
            "hypothesis": "fixture causal hypothesis",
            "falsifier": "fixture falsifier",
            "stopCondition": "fixture finite stop",
            "acceptanceIds": ["G4"],
            "taskRegistration": None,
            "processLossBudget": {
                "maxSameClassUserCorrectionBeforeStop": 1,
                "maxConsecutiveOutcomeNeutralWorkItems": 1,
                "maxProhibitedAgentWorkTransfers": 0,
                "stopOnAuthorityOrIrreversibleIncident": True,
                "stopOnUnboundedResidue": True,
            },
            "cleanupBoundary": {
                "repositoryTemporaryPaths": [
                    ".tmp",
                    "harness/__pycache__",
                    "tests/product/__pycache__",
                ],
                "privateResourceDispositions": [],
            },
            "workItems": [
                {
                    "id": FIXTURE_WORK_ID,
                    "state": work_state,
                    "acceptanceIds": ["G4"],
                    "operationIds": ["repository-read", "local-verification"],
                    "deliverables": ["fixture deliverable"],
                }
            ],
        }

    def ensure_increment(self, program: dict, *, state: str = "planned") -> dict:
        if not program["increments"]:
            program["increments"].append(self.increment_fixture(state=state))
        return program["increments"][-1]

    def map_outcome_to_latest_work(self, criterion_id: str) -> None:
        def add_mapping(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            increment["acceptanceIds"].append(criterion_id)
            increment["workItems"][0]["acceptanceIds"].append(criterion_id)
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", add_mapping)

    def configure_terminal_candidate(
        self, *, bind_release: bool = True
    ) -> tuple[list[str], str, str]:
        outcome_ids = ["O1", "O2", "O3", "O4", "O5"]

        def map_all(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            increment["acceptanceIds"].extend(outcome_ids)
            increment["workItems"][0]["acceptanceIds"].extend(outcome_ids)
            self.bind_fixture_registration(value, increment)
            value["status"] = "completed"
            value["activeIncrementId"] = None

        self.mutate("product/program.json", map_all)
        evidence_locator = "product/evidence/all-outcomes.json"
        self.write_json(
            evidence_locator,
            self.evidence_document(criterion_ids=outcome_ids),
        )

        def promote(value: dict) -> None:
            for criterion in value["criteria"]:
                if criterion["id"] in outcome_ids:
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = [evidence_locator]

        self.mutate("product/acceptance.json", promote)
        evidence_digest = hashlib.sha256()
        evidence_digest.update(evidence_locator.encode("utf-8"))
        evidence_digest.update(b"\0")
        evidence_digest.update(
            (self.root / evidence_locator).read_bytes().replace(b"\r\n", b"\n")
        )
        evidence_digest.update(b"\0")
        if bind_release:
            validator_relative = "harness/terminal_authorization_validator_fixture.py"
            validator_path = self.root / validator_relative
            validator_path.parent.mkdir(parents=True, exist_ok=True)
            validator_path.write_text(
                "def validate_terminal_authorization():\n    return True\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", validator_relative],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "fixture terminal validator"],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            validator_revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            validator_bytes = subprocess.run(
                ["git", "show", f"{validator_revision}:{validator_relative}"],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
            program = self.read_json("product/program.json")
            terminal_tag = f"{control.CURRENT_RELEASE}.0"
            program["terminalReleaseBinding"] = {
                "state": "candidate",
                "tag": terminal_tag,
                "publicRemote": control.EXPECTED_PUBLIC_REMOTE,
                "annotationFormat": control.TERMINAL_RELEASE_ANNOTATION_FORMAT,
                "o5EvidenceSetSha256": evidence_digest.hexdigest(),
                "authorizationValidator": {
                    "kind": "fixture-human-authorization-validator",
                    "version": 1,
                    "locator": validator_relative,
                    "revision": validator_revision,
                    "sha256": hashlib.sha256(validator_bytes).hexdigest(),
                },
                "authorizationSourcePolicy": {
                    "sourceKind": "fixture-trusted-user-event",
                    "publicIdentityScheme": control.EXPECTED_TERMINAL_AUTHORIZATION_PUBLIC_IDENTITY_SCHEME,
                    "commitmentScheme": control.EXPECTED_TERMINAL_AUTHORIZATION_COMMITMENT_SCHEME,
                    "privateLocatorRule": control.EXPECTED_TERMINAL_AUTHORIZATION_PRIVATE_LOCATOR_RULE,
                },
            }
            self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "terminal fixture candidate"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return outcome_ids, evidence_digest.hexdigest(), head

    def create_terminal_fixture_tag(
        self,
        evidence_digest: str,
        head: str,
        *,
        accepted_scope: list[str] | None = None,
        authorization_source: dict | None = None,
        authorization_validator_kind: str = "fixture-human-authorization-validator",
    ) -> str:
        annotation = {
            "schema": 1,
            "format": control.TERMINAL_RELEASE_ANNOTATION_FORMAT,
            "productId": "agent-autonomy-harness",
            "release": control.CURRENT_RELEASE,
            "candidateRevision": head,
            "tag": f"{control.CURRENT_RELEASE}.0",
            "publicRemote": control.EXPECTED_PUBLIC_REMOTE,
            "o5EvidenceSetSha256": evidence_digest,
            "authority": {
                "kind": "named-accountable-human",
                "name": "fixture reviewer",
                "decision": "authorized",
                "decidedAt": "2026-08-15T12:00:00+08:00",
                "source": (
                    {
                        "kind": "fixture-trusted-user-event",
                        "publicIdentity": (
                            "terminal-authorization.public-v1:" + "e" * 32
                        ),
                        "commitment": "hmac-sha256:" + "f" * 64,
                    }
                    if authorization_source is None
                    else authorization_source
                ),
                "validator": {
                    "kind": authorization_validator_kind,
                    "version": 1,
                },
            },
            "acceptedScope": (
                control.EXPECTED_TERMINAL_RELEASE_SCOPE
                if accepted_scope is None
                else accepted_scope
            ),
        }
        subprocess.run(
            [
                "git",
                "tag",
                "-a",
                f"{control.CURRENT_RELEASE}.0",
                "-m",
                json.dumps(annotation, separators=(",", ":")),
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return subprocess.run(
            ["git", "rev-parse", f"refs/tags/{control.CURRENT_RELEASE}.0"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def freeze_program_profile(
        self, program: dict, *, commit_binding: bool = True
    ) -> None:
        if program["normativeProfileBinding"]["state"] == "frozen":
            return
        profile_locator = "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md"
        protocol_locator = "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json"
        profile_revision = self.initialize_fixture_repository()
        profile_blob = subprocess.run(
            ["git", "show", f"{profile_revision}:{profile_locator}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        protocol_blob = subprocess.run(
            ["git", "show", f"{profile_revision}:{protocol_locator}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        program["normativeProfileBinding"] = {
            "state": "frozen",
            "profileIdentity": control.EXPECTED_V1_PROFILE_IDENTITY,
            "locator": profile_locator,
            "sha256": hashlib.sha256(profile_blob).hexdigest(),
            "cohortProtocolIdentity": control.EXPECTED_V1_COHORT_PROTOCOL_IDENTITY,
            "cohortProtocolLocator": protocol_locator,
            "cohortProtocolSha256": hashlib.sha256(protocol_blob).hexdigest(),
            "frozenAtRevision": profile_revision,
            "cohortActivation": {
                "surfaceIdentity": "enrollment-surface.public-v1:" + "1" * 32,
                "activationCursorCommitment": "hmac-sha256:" + "2" * 64,
                "keyIdentity": "cohort-key.public-v1:" + "3" * 32,
                "keyFingerprint": "sha256:" + "4" * 64,
                "sourceMessageRule": control.EXPECTED_SOURCE_MESSAGE_RULE,
                "hmacDomain": control.EXPECTED_HMAC_DOMAIN,
                "surfaceTransitionRule": control.EXPECTED_SURFACE_TRANSITION_RULE,
                "keyRetentionRule": control.EXPECTED_KEY_RETENTION_RULE,
            },
        }
        if commit_binding:
            self.write_json("product/program.json", program)
            environment = os.environ.copy()
            environment.update(
                {
                    "GIT_AUTHOR_DATE": "2026-08-12T02:57:00+08:00",
                    "GIT_COMMITTER_DATE": "2026-08-12T02:57:00+08:00",
                }
            )
            subprocess.run(
                ["git", "add", "product/program.json"],
                cwd=self.root,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            staged = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.root,
                env=environment,
                check=False,
            )
            if staged.returncode != 0:
                subprocess.run(
                    ["git", "commit", "--quiet", "-m", "freeze fixture profile binding"],
                    cwd=self.root,
                    env=environment,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

    def revoke_program_profile(self, program: dict, message: str = "revoke fixture cohort") -> None:
        program["normativeProfileBinding"]["state"] = "revoked"
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", message],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def start_successor_program_cohort(
        self, program: dict, *, reuse_activation_fields: tuple[str, ...] = ()
    ) -> None:
        binding = program["normativeProfileBinding"]
        self.assertEqual(binding["state"], "revoked")
        prior_activation = deepcopy(binding["cohortActivation"])
        binding["state"] = "frozen"
        binding["cohortActivation"] = {
            "surfaceIdentity": "enrollment-surface.public-v1:" + "5" * 32,
            "activationCursorCommitment": "hmac-sha256:" + "6" * 64,
            "keyIdentity": "cohort-key.public-v1:" + "7" * 32,
            "keyFingerprint": "sha256:" + "8" * 64,
            "sourceMessageRule": control.EXPECTED_SOURCE_MESSAGE_RULE,
            "hmacDomain": control.EXPECTED_HMAC_DOMAIN,
            "surfaceTransitionRule": control.EXPECTED_SURFACE_TRANSITION_RULE,
            "keyRetentionRule": control.EXPECTED_KEY_RETENTION_RULE,
        }
        for field in reuse_activation_fields:
            binding["cohortActivation"][field] = prior_activation[field]
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "start successor fixture cohort"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def bind_fixture_registration(
        self,
        program: dict,
        increment: dict,
        *,
        task_identity: str = fixture_task_identity("fixture-current"),
        scenario_class: str = "zero-tool-knowledge-new-intake",
        registration_id: str = "registration.fixture-current",
        relative: str = "product/evidence/fixture-registration.json",
        commit_profile_binding: bool = True,
        environment_manifest_schema: object = 1,
    ) -> None:
        outcome_ids = sorted(
            set(increment["acceptanceIds"]) & {"O1", "O2", "O3", "O4", "O5"}
        )
        if not outcome_ids:
            increment["taskRegistration"] = None
            return
        self.freeze_program_profile(program, commit_binding=commit_profile_binding)
        validator_relative = "harness/task_validator_fixture.py"
        validator_path = self.root / validator_relative
        validator_path.parent.mkdir(parents=True, exist_ok=True)
        validator_path.write_text(
            "def preregistered_task_validator():\n    return True\n",
            encoding="utf-8",
        )
        validator_environment = os.environ.copy()
        validator_environment.update(
            {
                "GIT_AUTHOR_DATE": "2026-08-12T02:56:00+08:00",
                "GIT_COMMITTER_DATE": "2026-08-12T02:56:00+08:00",
            }
        )
        subprocess.run(
            ["git", "add", validator_relative],
            cwd=self.root,
            env=validator_environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        validator_staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", validator_relative],
            cwd=self.root,
            env=validator_environment,
            check=False,
        )
        if validator_staged.returncode != 0:
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "fixture task validator"],
                cwd=self.root,
                env=validator_environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        validator_revision = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", validator_relative],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        committed_validator = subprocess.run(
            ["git", "show", f"{validator_revision}:{validator_relative}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        pre_measurement_validator_binding = {
            "kind": "test-validator",
            "version": 1,
            "locator": validator_relative,
            "revision": validator_revision,
            "sha256": hashlib.sha256(committed_validator).hexdigest(),
        }
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        fields = {
            field
            for criterion_id in outcome_ids
            for field in criteria[criterion_id]["operationalization"][
                "preRegistrationFields"
            ]
        }
        floors = {
            "quality": "fixture quality floor",
            "safety": "fixture safety floor",
            "evidence": "fixture evidence floor",
            "residue": "fixture residue floor",
        }
        interventions = ["fixture material intervention"]
        losses = ["fixture material collaboration loss"]
        harness_activation_delta = {
            "state": "active",
            "packageIdentity": "fixture-harness-package-v1",
            "packageSha256": "a" * 64,
            "activationIdentity": "fixture-harness-activation-v1",
            "activationSha256": "b" * 64,
            "taskExposureIdentity": "fixture-task-exposure-v1",
            "taskExposureSha256": "c" * 64,
        }
        manifest_relative = (
            "product/evidence/environment-manifests/fixture-"
            + hashlib.sha256(registration_id.encode("utf-8")).hexdigest()[:16]
            + ".json"
        )
        manifest = {
            "schema": environment_manifest_schema,
            "environmentClass": "user-configured",
            "treatmentArm": "with-exact-harness",
            "capturedAt": "2026-08-12T02:57:00+08:00",
            **{
                field: f"fixture fixed value for {field}"
                for field in control.EXPECTED_ENVIRONMENT_ATTRIBUTION[
                    "manifestFields"
                ]
            },
        }
        manifest[
            "exact-harness-package-activation-and-exposure-delta"
        ] = harness_activation_delta
        self.write_json(manifest_relative, manifest)
        manifest_environment = os.environ.copy()
        manifest_environment.update(
            {
                "GIT_AUTHOR_DATE": "2026-08-12T02:57:00+08:00",
                "GIT_COMMITTER_DATE": "2026-08-12T02:57:00+08:00",
            }
        )
        subprocess.run(
            ["git", "add", manifest_relative],
            cwd=self.root,
            env=manifest_environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        manifest_staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", manifest_relative],
            cwd=self.root,
            env=manifest_environment,
            check=False,
        )
        if manifest_staged.returncode != 0:
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "fixture environment manifest"],
                cwd=self.root,
                env=manifest_environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            manifest_revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        else:
            manifest_revision = subprocess.run(
                ["git", "log", "-1", "--format=%H", "--", manifest_relative],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        committed_manifest = subprocess.run(
            ["git", "show", f"{manifest_revision}:{manifest_relative}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        environment_attribution_binding = {
            "contractSha256": control.EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256,
            "environmentClass": "user-configured",
            "treatmentArm": "with-exact-harness",
            "manifestLocator": manifest_relative,
            "manifestRevision": manifest_revision,
            "manifestSha256": hashlib.sha256(committed_manifest).hexdigest(),
            "harnessActivationDelta": harness_activation_delta,
        }
        aliases = {
            "registeredAt": "2026-08-12T02:59:00+08:00",
            "taskIdentity": task_identity,
            "scenarioClass": scenario_class,
            "namedHumanAcceptor": "fixture reviewer",
            "qualitySafetyEvidenceAndResidueFloors": floors,
            "materialInterventionTaxonomy": interventions,
            "materialCollaborationLossTaxonomy": losses,
            "environmentAttributionBinding": environment_attribution_binding,
            "normativeProfileIdentity": control.EXPECTED_V1_PROFILE_IDENTITY,
            "cohortProtocolIdentity": control.EXPECTED_V1_COHORT_PROTOCOL_IDENTITY,
            "profileSha256": program["normativeProfileBinding"]["sha256"],
            "cohortProtocolSha256": program["normativeProfileBinding"][
                "cohortProtocolSha256"
            ],
        }
        registration = {
            "schema": 1,
            "id": registration_id,
            "registeredAt": aliases["registeredAt"],
            "taskIdentity": aliases["taskIdentity"],
            "incrementId": increment["id"],
            "criterionIds": outcome_ids,
            "preRegistrationValues": {
                field: aliases.get(field, f"fixture value for {field}")
                for field in sorted(fields)
            },
            "acceptanceAuthority": {
                "locator": "product/acceptance.json",
                "criteriaContractSha256": (
                    control.EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256
                ),
            },
            "namedHumanAcceptor": aliases["namedHumanAcceptor"],
            "qualitySafetyEvidenceAndResidueFloors": floors,
            "materialInterventionTaxonomy": interventions,
            "materialCollaborationLossTaxonomy": losses,
            "scenarioEvidenceAndStopRule": {
                "evidenceClass": "controlled-live-host",
                "startingTruthBoundBefore": "immutable-registration",
                "executionStartsAfter": "immutable-registration",
                "expectedInvariantOrCounterexample": "fixture controlled invariant",
                "failureDisposition": (
                    "retain failure, stop unsupported claims, and do not replace "
                    "missing evidence"
                ),
                "stopRule": "stop on any fixture floor failure",
            },
            "claimLimits": ["fixture task only"],
            "preMeasurementValidator": pre_measurement_validator_binding,
        }
        self.write_json(relative, registration)
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_DATE": "2026-08-12T02:58:00+08:00",
                "GIT_COMMITTER_DATE": "2026-08-12T02:58:00+08:00",
            }
        )
        subprocess.run(
            ["git", "add", relative],
            cwd=self.root,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=self.root,
            env=environment,
            check=False,
        )
        if staged.returncode != 0:
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "fixture task registration"],
                cwd=self.root,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        source_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        committed_registration = subprocess.run(
            ["git", "show", f"{source_revision}:{relative}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        increment["taskRegistration"] = {
            "locator": relative,
            "sha256": hashlib.sha256(committed_registration).hexdigest(),
            "sourceRevision": source_revision,
            "measurementNotBefore": "2026-08-12T02:59:00+08:00",
            "profileSha256": program["normativeProfileBinding"]["sha256"],
            "cohortProtocolSha256": program["normativeProfileBinding"][
                "cohortProtocolSha256"
            ],
            "preMeasurementValidator": pre_measurement_validator_binding,
        }

    def recommit_fixture_registration(
        self, program: dict, *, increment_index: int = 0
    ) -> None:
        relative = program["increments"][increment_index]["taskRegistration"][
            "locator"
        ]
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_DATE": "2026-08-12T02:58:30+08:00",
                "GIT_COMMITTER_DATE": "2026-08-12T02:58:30+08:00",
            }
        )
        subprocess.run(
            ["git", "add", relative],
            cwd=self.root,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "--amend", "--no-edit"],
            cwd=self.root,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        committed = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        binding = program["increments"][increment_index]["taskRegistration"]
        binding["sha256"] = hashlib.sha256(committed).hexdigest()
        binding["sourceRevision"] = revision

    def activate_program(self, program: dict) -> dict:
        increment = self.ensure_increment(program)
        program["status"] = "active"
        program["activeIncrementId"] = increment["id"]
        increment["state"] = "active"
        increment["workItems"][0]["state"] = "active"
        return increment

    def run_cli(
        self, *, json_output: bool = True, root: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT)
        verification_root = self.root if root is None else root
        command = [
            sys.executable,
            "-B",
            "-m",
            "harness",
            "verify",
            "--root",
            str(verification_root),
        ]
        if json_output:
            command.append("--json")
        return subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )

    def codex_session_start_payload(self, *, source: str = "startup") -> dict:
        return {
            "session_id": "00000000-0000-4000-8000-000000000001",
            "transcript_path": str(self.root / "must-not-be-read.jsonl"),
            "cwd": str(self.root),
            "hook_event_name": "SessionStart",
            "model": "gpt-test",
            "permission_mode": "default",
            "source": source,
        }

    def render_codex_fixture_context(self, payload: dict) -> str | None:
        with patch.multiple(
            control,
            _normative_profile_binding_history_valid=lambda root, binding, errors: True,
            _current_normative_profile_binding_history_valid=lambda root, binding, errors, **kwargs: True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
            _frozen_v02_profile_artifacts_valid=lambda root, errors: True,
        ):
            return render_session_start_context(self.root, payload)

    def claude_session_start_payload(self, *, source: str = "startup") -> dict:
        return {
            "session_id": "00000000-0000-4000-8000-000000000002",
            "transcript_path": str(self.root / "must-not-be-read.jsonl"),
            "cwd": str(self.root),
            "hook_event_name": "SessionStart",
            "source": source,
            "model": "claude-test",
        }

    def render_claude_fixture_context(self, payload: dict) -> str | None:
        with patch.multiple(
            control,
            _normative_profile_binding_history_valid=lambda root, binding, errors: True,
            _current_normative_profile_binding_history_valid=lambda root, binding, errors, **kwargs: True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
            _frozen_v02_profile_artifacts_valid=lambda root, errors: True,
        ):
            return render_claude_session_start_context(self.root, payload)

    def test_current_v12_contract_is_valid_active_o2_seam_with_bounded_o1_and_preserves_stopped_history(
        self,
    ) -> None:
        report = verify_product(ROOT)
        live_program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["release"], "v1.2")
        self.assertEqual(report["programStatus"], live_program["status"])
        self.assertEqual(report["activeIncrement"], live_program["activeIncrementId"])
        self.assertEqual(live_program["status"], "active")
        self.assertEqual(
            live_program["activeIncrementId"],
            "increment.v12-o2-codex-reference-validator-seam",
        )
        self.assertEqual(len(live_program["increments"]), 2)
        self.assertEqual(
            live_program["increments"][0]["taskRegistration"]["sourceRevision"],
            "11a2f9ae6eaeabe76042dec50d81a9f82347503e",
        )
        o2_seam = live_program["increments"][1]
        self.assertEqual(o2_seam["state"], "active")
        self.assertEqual(o2_seam["acceptanceIds"], ["G2", "G4"])
        self.assertIsNone(o2_seam["taskRegistration"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(
            report["sourceCarrierRelease"],
            {
                "allowed": True,
                "state": "release-eligible",
                "reason": "no-live-frozen-cohort-source-dependency",
                "scope": "live-cohort-source-dependency-only",
            },
        )
        self.assertEqual(report["outcomes"], {"verified": 1, "total": 5})
        self.assertEqual(report["guardrails"], {"passed": 4, "total": 4})
        self.assertTrue(report["criterionStates"]["O1"])
        self.assertTrue(all(not report["criterionStates"][f"O{i}"] for i in range(2, 6)))
        constitution = json.loads((ROOT / "product/constitution.json").read_text(encoding="utf-8"))
        v02 = constitution["historicalMilestones"][-3]
        self.assertEqual(v02["release"], "v0.2")
        self.assertEqual(v02["revision"], "0dbcb0af34197e5c35c75d69a1aeacf4fd91b404")
        self.assertIn("not the constitution terminal proposition", v02["claimLimit"])
        v10 = constitution["historicalMilestones"][-2]
        self.assertEqual(v10["release"], "v1.0")
        self.assertEqual(v10["revision"], "910ac016f1e5963450e3cfc46f5056ab0a6b04d7")
        self.assertIn("zero-outcome", v10["state"])
        self.assertIn("can be inherited", v10["claimLimit"])
        v11 = constitution["historicalMilestones"][-1]
        self.assertEqual(v11["release"], "v1.1")
        self.assertEqual(v11["revision"], "5ae71bbdd43c0c5dd5a0e120e508bccf9dd9464c")
        self.assertIn("missed-enrollment", v11["state"])
        self.assertIn("outcome-bearing assistance", v11["claimLimit"])
        self.assertEqual(live_program["priorRelease"]["release"], "v1.1")
        binding = live_program["normativeProfileBinding"]
        self.assertEqual(binding, self.current_v12_profile_binding())
        self.assertTrue(control.CURRENT_PROFILE_FREEZE_ENABLED)
        self.assertEqual(
            control.EXPECTED_CURRENT_INITIAL_BINDING_REVISION,
            "3e816863846135618299aa196f607c9f42e1f51f",
        )
        self.assertEqual(
            control.EXPECTED_CURRENT_INITIAL_BINDING_SHA256,
            "31dafe95aedab17d5fa1252c804e9a60179dbcf6f5b6014b52c3889646feff7d",
        )
        self.assertEqual(dict(control.SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS), {})

    def test_v10_profile_and_cohort_protocol_remain_exact_historical_inputs(self) -> None:
        profile = (ROOT / "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md").read_text(
            encoding="utf-8"
        )
        protocol = json.loads(
            (ROOT / "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("Identity: `harness-demand-to-capability-v1.0-candidate.5`", profile)
        self.assertIn("Status: pre-freeze candidate", profile)
        self.assertEqual(
            hashlib.sha256(profile.encode("utf-8")).hexdigest(),
            control.EXPECTED_V1_PROFILE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(
                (ROOT / "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json")
                .read_bytes()
                .replace(b"\r\n", b"\n")
            ).hexdigest(),
            control.EXPECTED_V1_COHORT_PROTOCOL_SHA256,
        )
        self.assertEqual(
            control.EXPECTED_V1_PROFILE_ARTIFACT_REVISION,
            "502c4ff7edfc6307ea5469bcb81089e13612a24a",
        )

        self.assertEqual(
            control.EXPECTED_V1_INITIAL_BINDING_REVISION,
            "d19d2fb9da0883a44eec887eca4072e70a93f8d7",
        )
        self.assertEqual(
            control.EXPECTED_V1_INITIAL_BINDING_SHA256,
            "ee4ba7a16f15bba78efbefce1022ac6180d1c7e40e800011348df5ae21ab0eb7",
        )
        self.assertEqual(
            control.EXPECTED_V1_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID,
            control.INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID,
        )
        self.assertNotIn(
            control.INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID,
            control.SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS,
        )
        self.assertEqual(
            control.EXPECTED_V1_SUCCESSOR_BINDING_REVISION,
            "8e8e76ba65db8f625792aed7dfb9180790433459",
        )
        self.assertEqual(
            control.EXPECTED_V1_SUCCESSOR_BINDING_SHA256,
            "d2cf0cdce692fb06bf59bc1002d8b6036b6d1ee79ac6a86c27c74358f157dbfa",
        )
        self.assertEqual(
            control.EXPECTED_V1_SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID,
            control.SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID,
        )
        self.assertNotIn(
            control.SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID,
            control.SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS,
        )
        for heading in (
            "## Agent method",
            "## Prospective registration",
            "## Mandatory floors",
            "## Baseline state machine",
            "## Carrier and topology state machine",
            "## Cross-host realization",
            "## Evidence, privacy, and residue",
            "## Publication and release state machine",
            "## Claim ceiling",
        ):
            self.assertIn(heading, profile)
        self.assertEqual(set(protocol), control.COHORT_PROTOCOL_FIELDS)
        self.assertEqual(protocol["schema"], 1)
        self.assertEqual(
            protocol["profileIdentity"],
            "harness-demand-to-capability-v1.0-candidate.5",
        )
        self.assertEqual(
            protocol["cohortProtocolIdentity"],
            "harness-prospective-cohort-v1.0-candidate.5",
        )
        self.assertEqual(
            protocol["strata"], list(control.EXPECTED_COHORT_SCENARIO_CLASSES)
        )
        for field, expected in control.EXPECTED_COHORT_PROTOCOL_RULES.items():
            self.assertEqual(protocol[field], expected)
        self.assertTrue(protocol["claimLimits"])

    def test_v12_profile_artifacts_are_distinct_and_do_not_reuse_v11_binding(self) -> None:
        program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        profile_path = ROOT / control.EXPECTED_CURRENT_PROFILE_CANDIDATE_LOCATOR
        protocol_path = (
            ROOT / control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_LOCATOR
        )
        profile_bytes = profile_path.read_bytes().replace(b"\r\n", b"\n")
        protocol_bytes = protocol_path.read_bytes().replace(b"\r\n", b"\n")
        profile = profile_bytes.decode("utf-8")
        profile_flat = " ".join(profile.split())
        protocol = json.loads(protocol_bytes)

        binding = program["normativeProfileBinding"]
        self.assertEqual(binding, self.current_v12_profile_binding())
        historical_program = json.loads(
            subprocess.run(
                [
                    "git",
                    "show",
                    control.EXPECTED_PRIOR_RELEASE["revision"]
                    + ":product/program.json",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        historical_binding = historical_program["normativeProfileBinding"]
        self.assertEqual(historical_binding["state"], "revoked")
        self.assertNotEqual(
            historical_binding["profileIdentity"],
            control.EXPECTED_CURRENT_PROFILE_CANDIDATE_IDENTITY,
        )
        self.assertNotEqual(
            historical_binding["cohortProtocolIdentity"],
            control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_IDENTITY,
        )
        self.assertEqual(
            hashlib.sha256(profile_bytes).hexdigest(),
            control.EXPECTED_CURRENT_PROFILE_CANDIDATE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(protocol_bytes).hexdigest(),
            control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_SHA256,
        )
        candidate_errors: list[str] = []
        self.assertTrue(
            control._current_profile_candidate_artifacts_valid(
                ROOT, candidate_errors
            ),
            candidate_errors,
        )
        self.assertIn(control.EXPECTED_CURRENT_PROFILE_CANDIDATE_IDENTITY, profile)
        self.assertIn("Status: pre-freeze candidate", profile)
        self.assertIn("not a static capability ceiling", profile_flat)
        self.assertIn("Resolve version-sensitive sources", profile)
        self.assertIn("technically or authoritatively human-only", profile_flat)
        self.assertIn("simplified, disabled, or retired", profile_flat)
        self.assertIn("Operate and reconcile continuously", profile)
        self.assertIn("stop further effects", profile_flat)
        self.assertIn("context capacity", profile_flat)
        self.assertIn("structured machine contract", profile_flat)
        self.assertIn("JSON is still inert", profile)
        self.assertIn("only for the residual host action", profile_flat)
        self.assertIn("not a feature backlog", profile_flat)
        self.assertIn("not mean every risk is eliminated", profile_flat)
        self.assertIn("Natural tasks may later", profile)
        self.assertIn("not a product-delivery prerequisite", profile_flat)
        self.assertIn("No private source-capture key", profile)
        self.assertIn("verifier enforces those authorities", profile_flat)
        self.assertEqual(protocol["schema"], 2)
        self.assertEqual(set(protocol), control.CURRENT_COHORT_PROTOCOL_FIELDS)
        self.assertEqual(
            protocol["profileIdentity"],
            control.EXPECTED_CURRENT_PROFILE_CANDIDATE_IDENTITY,
        )
        self.assertEqual(
            protocol["cohortProtocolIdentity"],
            control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_IDENTITY,
        )
        self.assertIn("starting-manifest", protocol["environmentAttributionRule"])
        self.assertIn("current-source", protocol["versionResolutionRule"])
        self.assertIn("human-only", protocol["humanInterventionRule"])
        self.assertIn("no-invented-natural-demand", protocol["scenarioEligibilityRule"])
        self.assertIn("before-outcome-bearing-execution", protocol["registrationRule"])
        self.assertIn("remain-distinct", protocol["evidenceClassRule"])
        self.assertIn("stop-recover-minimal-correct-reverify", protocol["selfCorrectionRule"])
        self.assertNotIn("strata", protocol)
        self.assertIn("current-acceptance-owned", protocol["scenarioCoverageRule"])
        self.assertEqual(
            control.EXPECTED_CURRENT_PROFILE_ARTIFACT_REVISION,
            "de5dbc42fb1e265a720bb26808a31d03d032e602",
        )
        self.assertEqual(
            control.EXPECTED_CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID,
            None,
        )
        for field, expected in control.EXPECTED_CURRENT_COHORT_PROTOCOL_RULES.items():
            self.assertEqual(protocol[field], expected)
        criteria = self.read_json("product/acceptance.json")["criteria"][:5]
        self.assertFalse(any(item["assessment"] == "verified" for item in criteria))

    def current_v12_profile_binding(self) -> dict:
        return {
            "state": "frozen",
            "profileIdentity": control.EXPECTED_CURRENT_PROFILE_CANDIDATE_IDENTITY,
            "locator": control.EXPECTED_CURRENT_PROFILE_CANDIDATE_LOCATOR,
            "sha256": control.EXPECTED_CURRENT_PROFILE_CANDIDATE_SHA256,
            "cohortProtocolIdentity": control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_IDENTITY,
            "cohortProtocolLocator": control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_LOCATOR,
            "cohortProtocolSha256": control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_SHA256,
            "frozenAtRevision": control.EXPECTED_CURRENT_PROFILE_ARTIFACT_REVISION,
            "cohortActivation": None,
        }

    def current_authorization_anchors(self) -> dict:
        return {
            "EXPECTED_CURRENT_INITIAL_BINDING_REVISION": "a" * 40,
            "EXPECTED_CURRENT_INITIAL_BINDING_SHA256": "b" * 64,
            "EXPECTED_CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID": (
                control.CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID
            ),
            "EXPECTED_CURRENT_INITIAL_AUTHORIZATION_KEY_FINGERPRINT": (
                "sha256:" + "c" * 64
            ),
            "EXPECTED_CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT": (
                "hmac-sha256:" + "f" * 64
            ),
            "EXPECTED_CURRENT_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT": (
                "hmac-sha256:" + "1" * 64
            ),
            "EXPECTED_CURRENT_INITIAL_MATERIALIZATION_EVENT_COMMITMENT": (
                "hmac-sha256:" + "2" * 64
            ),
            "EXPECTED_CURRENT_INITIAL_AUTHORIZATION_EVENT_COMMITMENT": (
                "hmac-sha256:" + "3" * 64
            ),
            "EXPECTED_CURRENT_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT": (
                "hmac-sha256:" + "4" * 64
            ),
            "EXPECTED_CURRENT_INITIAL_SURFACE_IDENTITY": (
                "enrollment-surface.public-v1:" + "5" * 32
            ),
            "EXPECTED_CURRENT_INITIAL_ACTIVATION_CURSOR_COMMITMENT": (
                "hmac-sha256:" + "6" * 64
            ),
            "EXPECTED_CURRENT_INITIAL_KEY_IDENTITY": (
                "cohort-key.public-v1:" + "7" * 32
            ),
        }

    def current_authorization_document(self) -> dict:
        return {
            "kind": "v1.1-normative-profile-binding-authorization",
            "revision": "a" * 40,
            "bindingSha256": "b" * 64,
            "environmentAttributionContractSha256": (
                control.EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
            ),
            "environmentManifestBoundary": (
                control.EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY
            ),
        }

    def test_v12_authorizer_registry_is_empty_and_unfrozen_state_never_reads_private_source(
        self,
    ) -> None:
        floor = self.initialize_fixture_repository()
        binding = self.read_json("product/program.json")["normativeProfileBinding"]
        self.assertEqual(
            set(control.SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS),
            set(),
        )
        with (
            patch.multiple(
                control,
                CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
            ),
            patch(
                "harness.control._read_current_initial_authorization_private_evidence",
                side_effect=AssertionError("unfrozen verifier read private source"),
            ) as private_read,
        ):
            errors: list[str] = []
            self.assertTrue(
                control._current_normative_profile_binding_history_valid(
                    self.root,
                    binding,
                    errors,
                ),
                errors,
            )
        private_read.assert_not_called()

    def test_v11_materialization_dispositions_are_exact_and_code_owned(self) -> None:
        self.assertIn(
            control.CURRENT_INITIAL_PRIVATE_RESOURCE_PROGRAM_DISPOSITION,
            control.ALLOWED_PRIVATE_RESOURCE_DISPOSITIONS,
        )
        self.assertIn(
            control.CURRENT_INITIAL_EXPIRY_TRIGGER_PROGRAM_DISPOSITION,
            control.ALLOWED_PRIVATE_RESOURCE_DISPOSITIONS,
        )
        live_program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        for increment in live_program["increments"]:
            self.assertEqual(
                increment["cleanupBoundary"]["privateResourceDispositions"],
                [],
            )
        frozen_program = json.loads(
            subprocess.run(
                [
                    "git",
                    "show",
                    (
                        "5ce27730b982d3c78ed50d006f78ff0eea45d4a9"
                        ":product/program.json"
                    ),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        cleanup = frozen_program["increments"][0]["cleanupBoundary"]
        self.assertEqual(
            cleanup["privateResourceDispositions"],
            [
                control.CURRENT_INITIAL_PRIVATE_RESOURCE_PROGRAM_DISPOSITION,
                control.CURRENT_INITIAL_EXPIRY_TRIGGER_PROGRAM_DISPOSITION,
            ],
        )

    def test_v11_authorizer_fails_before_private_read_with_unset_or_wrong_boundary(
        self,
    ) -> None:
        with patch.multiple(
            control,
            EXPECTED_CURRENT_INITIAL_BINDING_REVISION=None,
            EXPECTED_CURRENT_INITIAL_BINDING_SHA256=None,
        ), patch(
            "harness.control._read_current_initial_authorization_private_evidence"
        ) as private_read:
            errors: list[str] = []
            self.assertFalse(
                control._validate_current_initial_binding_authorization(
                    {
                        "kind": "v1.1-normative-profile-binding-authorization",
                        "revision": None,
                        "bindingSha256": None,
                        "environmentAttributionContractSha256": (
                            control.EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
                        ),
                        "environmentManifestBoundary": (
                            control.EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY
                        ),
                    },
                    ROOT,
                    errors,
                )
            )
        self.assertIn(
            "current v1.1 binding authorization anchors are unavailable",
            errors,
        )
        private_read.assert_not_called()

        with patch.multiple(control, **self.current_authorization_anchors()), patch(
            "harness.control._read_current_initial_authorization_private_evidence"
        ) as private_read:
            document = self.current_authorization_document()
            document["environmentManifestBoundary"] = "ambient-or-post-hoc"
            errors = []
            self.assertFalse(
                control._validate_current_initial_binding_authorization(
                    document,
                    ROOT,
                    errors,
                )
            )
        self.assertEqual(
            errors,
            [
                "current v1.1 binding authorization document does not match the frozen binding"
            ],
        )
        private_read.assert_not_called()

    def test_v11_authorizer_rejects_v10_private_evidence_before_source_access(
        self,
    ) -> None:
        old_private_evidence = {
            field: "historical-v1"
            for field in control.INITIAL_BINDING_PRIVATE_EVIDENCE_FIELDS
        }
        old_private_evidence["schema"] = 1
        with patch.multiple(control, **self.current_authorization_anchors()), patch(
            "harness.control._current_initial_authorization_source_locator_parts"
        ) as source_access:
            errors: list[str] = []
            self.assertFalse(
                control._current_initial_authorization_event_window_valid(
                    old_private_evidence,
                    self.current_authorization_document(),
                    errors,
                    credential_target_name="AgentAutonomyHarness/v1/historical",
                )
            )
        self.assertEqual(
            errors,
            [
                "current v1.1 binding authorization private source does not match the frozen activation"
            ],
        )
        source_access.assert_not_called()

    def test_v11_authorization_snapshot_binds_complete_pre_activation_window(
        self,
    ) -> None:
        key = b"k" * 32
        source_identity = "11111111-1111-4111-8111-111111111111"
        authorization_identity = "22222222-2222-4222-8222-222222222222"
        source_timestamp = "2026-08-16T01:00:00Z"
        authorization_timestamp = "2026-08-16T01:05:00Z"
        document = self.current_authorization_document()
        anchors = self.current_authorization_anchors()
        surface = anchors["EXPECTED_CURRENT_INITIAL_SURFACE_IDENTITY"]
        with patch.multiple(control, **anchors):
            materialization_message = (
                control._current_initial_materialization_authorization_message()
            )
            authorization_message = (
                control._current_initial_activation_authorization_message(document)
            )
        self.assertIsInstance(authorization_message, str)
        source_event = {
            "timestamp": source_timestamp,
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "client_id": source_identity,
                "message": materialization_message,
            },
        }
        authorization_event = {
            "timestamp": authorization_timestamp,
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "client_id": authorization_identity,
                "message": authorization_message,
            },
        }
        snapshot = (
            json.dumps(source_event, separators=(",", ":"))
            + "\n"
            + json.dumps(authorization_event, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        anchors.update(
            {
                "EXPECTED_CURRENT_INITIAL_MATERIALIZATION_EVENT_COMMITMENT": (
                    control._initial_authorization_string_hmac(
                        key,
                        control.CURRENT_INITIAL_MATERIALIZATION_EVENT_HMAC_DOMAIN,
                        surface,
                        source_identity,
                        source_timestamp,
                        materialization_message,
                    )
                ),
                "EXPECTED_CURRENT_INITIAL_AUTHORIZATION_EVENT_COMMITMENT": (
                    control._initial_authorization_string_hmac(
                        key,
                        control.CURRENT_INITIAL_AUTHORIZATION_EVENT_HMAC_DOMAIN,
                        surface,
                        document["kind"],
                        document["revision"],
                        document["bindingSha256"],
                        document["environmentAttributionContractSha256"],
                        document["environmentManifestBoundary"],
                        authorization_identity,
                        authorization_timestamp,
                        authorization_message,
                    )
                ),
                "EXPECTED_CURRENT_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT": (
                    control._initial_authorization_bytes_hmac(
                        key,
                        control.CURRENT_INITIAL_AUTHORIZATION_WINDOW_HMAC_DOMAIN,
                        snapshot,
                    )
                ),
            }
        )
        private_evidence = {
            "surfaceIdentity": surface,
            "sourceEventIdentity": source_identity,
            "sourceEventTimestamp": source_timestamp,
            "authorizationEventIdentity": authorization_identity,
            "authorizationEventTimestamp": authorization_timestamp,
        }
        with patch.multiple(control, **anchors):
            errors: list[str] = []
            self.assertTrue(
                control._current_initial_authorization_snapshot_valid(
                    private_evidence,
                    document,
                    snapshot,
                    key,
                    errors,
                ),
                errors,
            )
            intervening = {
                "timestamp": "2026-08-16T01:03:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "user_message",
                    "client_id": "33333333-3333-4333-8333-333333333333",
                    "message": "unrelated natural demand",
                },
            }
            interrupted_snapshot = (
                json.dumps(source_event, separators=(",", ":"))
                + "\n"
                + json.dumps(intervening, separators=(",", ":"))
                + "\n"
                + json.dumps(authorization_event, separators=(",", ":"))
                + "\n"
            ).encode("utf-8")
            errors = []
            self.assertFalse(
                control._current_initial_authorization_snapshot_valid(
                    private_evidence,
                    document,
                    interrupted_snapshot,
                    key,
                    errors,
                )
            )
        self.assertEqual(
            errors,
            [
                "natural demand appeared before exact current v1.1 first-freeze authorization"
            ],
        )

    def test_v11_authorizer_preserves_transient_source_and_deletes_deterministic_failure(
        self,
    ) -> None:
        resource = (
            {"fixture": "private"},
            "AgentAutonomyHarness/v1.1/exact-fixture",
        )
        before_expiry = datetime(2026, 12, 31, 15, 59, 58, tzinfo=timezone.utc)
        for diagnostic in sorted(
            control.NONDESTRUCTIVE_CURRENT_INITIAL_AUTHORIZATION_SOURCE_FAILURES
        ):
            with self.subTest(diagnostic=diagnostic), patch.multiple(
                control,
                **self.current_authorization_anchors(),
            ), patch(
                "harness.control._utc_now",
                return_value=before_expiry,
            ), patch(
                "harness.control._read_current_initial_authorization_private_evidence",
                return_value=resource,
            ), patch(
                "harness.control._current_initial_authorization_event_window_valid",
                side_effect=lambda *args, **kwargs: (
                    args[2].append(diagnostic) or False
                ),
            ), patch(
                "harness.control._delete_current_initial_authorization_private_resource"
            ) as delete:
                errors: list[str] = []
                self.assertFalse(
                    control._validate_current_initial_binding_authorization(
                        self.current_authorization_document(),
                        ROOT,
                        errors,
                    )
                )
                self.assertEqual(errors, [diagnostic])
                delete.assert_not_called()

        with patch.multiple(
            control,
            **self.current_authorization_anchors(),
        ), patch(
            "harness.control._utc_now",
            return_value=before_expiry,
        ), patch(
            "harness.control._read_current_initial_authorization_private_evidence",
            return_value=resource,
        ), patch(
            "harness.control._current_initial_authorization_event_window_valid",
            side_effect=lambda *args, **kwargs: (
                args[2].append(
                    "current v1.1 binding authorization source event is invalid"
                )
                or False
            ),
        ), patch(
            "harness.control._delete_current_initial_authorization_private_resource",
            return_value=True,
        ) as delete:
            errors = []
            self.assertFalse(
                control._validate_current_initial_binding_authorization(
                    self.current_authorization_document(),
                    ROOT,
                    errors,
                )
            )
            delete.assert_called_once_with(
                resource,
                "validation-failure",
                ROOT,
                errors,
            )

    def test_v11_expiry_cleanup_not_due_does_not_read_private_source(self) -> None:
        with patch(
            "harness.control._utc_now",
            return_value=datetime(2026, 12, 31, 15, 59, 58, tzinfo=timezone.utc),
        ), patch(
            "harness.control._read_current_initial_authorization_private_evidence"
        ) as private_read:
            errors: list[str] = []
            self.assertFalse(
                control.expire_current_initial_authorization_private_evidence(
                    ROOT,
                    errors,
                )
            )
        self.assertEqual(
            errors,
            ["current v1.1 binding authorization expiry cleanup is not due"],
        )
        private_read.assert_not_called()

        with patch(
            "harness.control._utc_now",
            return_value=datetime(2026, 12, 31, 16, 0, 0, tzinfo=timezone.utc),
        ), patch(
            "harness.control._read_current_initial_authorization_private_evidence",
            return_value=None,
        ), patch(
            "harness.control._current_initial_authorization_private_resource_absent",
            return_value=True,
        ), patch(
            "harness.control._remove_current_initial_expiry_cleanup_trigger",
            return_value=True,
        ) as remove_trigger:
            errors = []
            self.assertTrue(
                control.expire_current_initial_authorization_private_evidence(
                    ROOT,
                    errors,
                ),
                errors,
            )
        remove_trigger.assert_called_once_with(ROOT, errors)

    def test_v11_current_private_cleanup_deletes_only_verified_exact_resource(
        self,
    ) -> None:
        resource = (
            {"fixture": "private"},
            "AgentAutonomyHarness/v1.1/exact-fixture",
        )
        advapi32 = MagicMock()
        advapi32.CredDeleteW.return_value = 1
        with patch.object(control.os, "name", "nt"), patch(
            "harness.control.ctypes.WinDLL",
            return_value=advapi32,
            create=True,
        ), patch(
            "harness.control.ctypes.set_last_error",
            create=True,
        ), patch(
            "harness.control._current_initial_authorization_private_resource_identity_valid",
            return_value=True,
        ), patch(
            "harness.control._current_initial_authorization_private_resource_absent",
            return_value=True,
        ), patch(
            "harness.control._remove_current_initial_expiry_cleanup_trigger",
            return_value=True,
        ) as remove_trigger:
            errors: list[str] = []
            self.assertTrue(
                control._delete_current_initial_authorization_private_resource(
                    resource,
                    "expiry",
                    ROOT,
                    errors,
                ),
                errors,
            )
        advapi32.CredDeleteW.assert_called_once_with(resource[1], 1, 0)
        remove_trigger.assert_called_once_with(ROOT, errors)

        advapi32 = MagicMock()
        with patch.object(control.os, "name", "nt"), patch(
            "harness.control.ctypes.WinDLL",
            return_value=advapi32,
            create=True,
        ), patch(
            "harness.control._current_initial_authorization_private_resource_identity_valid",
            return_value=False,
        ):
            errors = []
            self.assertFalse(
                control._delete_current_initial_authorization_private_resource(
                    resource,
                    "validation-failure",
                    ROOT,
                    errors,
                )
            )
        advapi32.CredDeleteW.assert_not_called()

    def test_v12_frozen_material_accepts_only_the_pinned_candidate_revision(self) -> None:
        binding = self.current_v12_profile_binding()
        errors: list[str] = []
        self.assertTrue(
            control._current_profile_binding_material_valid(ROOT, binding, errors),
            errors,
        )
        self.assertEqual(
            control.EXPECTED_CURRENT_PROFILE_ARTIFACT_REVISION,
            "de5dbc42fb1e265a720bb26808a31d03d032e602",
        )

        binding["frozenAtRevision"] = "f" * 40
        errors = []
        self.assertFalse(
            control._current_profile_binding_material_valid(ROOT, binding, errors)
        )
        self.assertIn(
            "frozen normative profile binding is not the code-owned v1.2 candidate",
            errors,
        )

        binding = self.current_v12_profile_binding()
        binding["profileIdentity"] = control.EXPECTED_V1_PROFILE_IDENTITY
        errors = []
        self.assertFalse(
            control._current_profile_binding_material_valid(ROOT, binding, errors)
        )
        self.assertIn(
            "frozen normative profile binding is not the code-owned v1.2 candidate",
            errors,
        )
        self.assertFalse(
            control._committed_blob(
                ROOT,
                None,
                control.EXPECTED_CURRENT_PROFILE_CANDIDATE_LOCATOR,
                control.EXPECTED_CURRENT_PROFILE_CANDIDATE_SHA256,
            )
        )

    def test_v12_uncommitted_freeze_and_unpinned_freeze_fail_closed(self) -> None:
        floor = self.initialize_fixture_repository()
        binding = self.current_v12_profile_binding()
        program = self.read_json("product/program.json")
        program["normativeProfileBinding"] = binding
        self.write_json("product/program.json", program)

        with patch.object(
            control,
            "CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION",
            floor,
        ):
            errors: list[str] = []
            self.assertFalse(
                control._current_normative_profile_binding_history_valid(
                    self.root, binding, errors
                )
            )
        self.assertIn(
            "frozen current normative profile binding must exist in committed first-parent history",
            errors,
        )

        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "fixture v1.1 freeze"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with patch.multiple(
            control,
            CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
            EXPECTED_CURRENT_INITIAL_BINDING_REVISION=None,
            EXPECTED_CURRENT_INITIAL_BINDING_SHA256=None,
        ):
            errors = []
            self.assertFalse(
                control._current_normative_profile_binding_history_valid(
                    self.root, binding, errors
                )
            )
        self.assertIn(
            "initial current frozen binding is not code-pinned to canonical history",
            errors,
        )

    def test_v12_public_freeze_anchor_never_reads_v11_private_authorization(
        self,
    ) -> None:
        floor = self.initialize_fixture_repository()
        binding = self.current_v12_profile_binding()
        program = self.read_json("product/program.json")
        program["normativeProfileBinding"] = binding
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "fixture public v1.2 freeze"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        freeze_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        binding_sha256 = hashlib.sha256(
            json.dumps(
                binding,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        with (
            patch.multiple(
                control,
                CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
                EXPECTED_CURRENT_INITIAL_BINDING_REVISION=freeze_revision,
                EXPECTED_CURRENT_INITIAL_BINDING_SHA256=binding_sha256,
            ),
            patch(
                "harness.control._current_initial_authorization_anchors_valid",
                side_effect=AssertionError("v1.2 public freeze consulted v1.1 anchors"),
            ) as private_anchors,
            patch(
                "harness.control._binding_authorization_valid",
                side_effect=AssertionError("v1.2 public freeze consulted private authorizer"),
            ) as private_authorizer,
            patch(
                "harness.control._current_public_freeze_signature_valid",
                return_value=True,
            ) as public_signature,
        ):
            errors: list[str] = []
            self.assertTrue(
                control._current_normative_profile_binding_history_valid(
                    self.root,
                    binding,
                    errors,
                ),
                errors,
            )
        private_anchors.assert_not_called()
        private_authorizer.assert_not_called()
        public_signature.assert_called_once_with(
            self.root, freeze_revision, binding, errors
        )

    def test_v12_public_freeze_requires_exact_allowed_signer_and_signed_commit(
        self,
    ) -> None:
        floor = self.initialize_fixture_repository()
        key_path = self.root / "fixture-v12-freeze-signing-key"
        subprocess.run(
            [
                "ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(key_path),
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        public_fields = key_path.with_suffix(".pub").read_text(
            encoding="ascii"
        ).split()
        allowed_signers = (
            self.root
            / control.EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_LOCATOR
        )
        allowed_signers.parent.mkdir(parents=True, exist_ok=True)
        allowed_signers.write_bytes(
            (
                control.EXPECTED_CURRENT_INITIAL_BINDING_SIGNER_PRINCIPAL
                + " "
                + public_fields[0]
                + " "
                + public_fields[1]
                + "\n"
            ).encode("ascii")
        )
        subprocess.run(
            [
                "git",
                "add",
                control.EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_LOCATOR,
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "prebind fixture v1.2 signer"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        binding = self.current_v12_profile_binding()
        program = self.read_json("product/program.json")
        program["normativeProfileBinding"] = binding
        self.write_json("product/program.json", program)
        subprocess.run(
            [
                "git",
                "add",
                "product/program.json",
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "gpg.format=ssh",
                "-c",
                f"user.signingkey={key_path}",
                "commit",
                "--quiet",
                "-S",
                "-m",
                "signed fixture v1.2 freeze",
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        freeze_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        binding_sha256 = hashlib.sha256(
            json.dumps(
                binding,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        allowed_signers_sha256 = hashlib.sha256(
            allowed_signers.read_bytes()
        ).hexdigest()
        key_blob = base64.b64decode(public_fields[1], validate=True)
        key_fingerprint = (
            "SHA256:"
            + base64.b64encode(hashlib.sha256(key_blob).digest())
            .decode("ascii")
            .rstrip("=")
        )
        anchors = {
            "CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION": floor,
            "EXPECTED_CURRENT_INITIAL_BINDING_REVISION": freeze_revision,
            "EXPECTED_CURRENT_INITIAL_BINDING_SHA256": binding_sha256,
            "EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_SHA256": (
                allowed_signers_sha256
            ),
            "EXPECTED_CURRENT_INITIAL_BINDING_SIGNING_KEY_FINGERPRINT": (
                key_fingerprint
            ),
        }
        with patch.multiple(control, **anchors):
            errors: list[str] = []
            self.assertTrue(
                control._current_normative_profile_binding_history_valid(
                    self.root, binding, errors
                ),
                errors,
            )

        with patch.multiple(
            control,
            **{
                **anchors,
                "EXPECTED_CURRENT_INITIAL_BINDING_SIGNING_KEY_FINGERPRINT": (
                    "SHA256:" + "A" * 43
                ),
            },
        ):
            errors = []
            self.assertFalse(
                control._current_normative_profile_binding_history_valid(
                    self.root, binding, errors
                )
            )
        self.assertIn(
            "current v1.2 public freeze signer identity is invalid", errors
        )

        subprocess.run(
            ["git", "commit", "--quiet", "--amend", "--no-gpg-sign", "--no-edit"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        unsigned_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        with patch.multiple(
            control,
            **{
                **anchors,
                "EXPECTED_CURRENT_INITIAL_BINDING_REVISION": unsigned_revision,
            },
        ):
            errors = []
            self.assertFalse(
                control._current_normative_profile_binding_history_valid(
                    self.root, binding, errors
                )
            )
        self.assertIn(
            "current v1.2 public freeze commit signature is invalid", errors
        )

        allowed_signers.write_bytes(
            (
                control.EXPECTED_CURRENT_INITIAL_BINDING_SIGNER_PRINCIPAL
                + ' namespaces="git" '
                + public_fields[0]
                + " "
                + public_fields[1]
                + "\n"
            ).encode("ascii")
        )
        subprocess.run(
            [
                "git",
                "add",
                control.EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_LOCATOR,
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "gpg.format=ssh",
                "-c",
                f"user.signingkey={key_path}",
                "commit",
                "--quiet",
                "--amend",
                "-S",
                "--no-edit",
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        option_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        option_sha256 = hashlib.sha256(allowed_signers.read_bytes()).hexdigest()
        with patch.multiple(
            control,
            **{
                **anchors,
                "EXPECTED_CURRENT_INITIAL_BINDING_REVISION": option_revision,
                "EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_SHA256": (
                    option_sha256
                ),
            },
        ):
            errors = []
            self.assertFalse(
                control._current_normative_profile_binding_history_valid(
                    self.root, binding, errors
                )
            )
        self.assertIn("current v1.2 public freeze commit scope is not exact", errors)

    def test_v12_public_freeze_rejects_self_bootstrapped_signer(self) -> None:
        floor = self.initialize_fixture_repository()
        key_path = self.root / "fixture-v12-self-bootstrap-key"
        subprocess.run(
            [
                "ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(key_path),
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        public_fields = key_path.with_suffix(".pub").read_text(
            encoding="ascii"
        ).split()
        allowed_signers = (
            self.root
            / control.EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_LOCATOR
        )
        allowed_signers.parent.mkdir(parents=True, exist_ok=True)
        allowed_signers.write_bytes(
            (
                control.EXPECTED_CURRENT_INITIAL_BINDING_SIGNER_PRINCIPAL
                + " "
                + public_fields[0]
                + " "
                + public_fields[1]
                + "\n"
            ).encode("ascii")
        )
        binding = self.current_v12_profile_binding()
        program = self.read_json("product/program.json")
        program["normativeProfileBinding"] = binding
        self.write_json("product/program.json", program)
        subprocess.run(
            [
                "git",
                "add",
                "product/program.json",
                control.EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_LOCATOR,
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "gpg.format=ssh",
                "-c",
                f"user.signingkey={key_path}",
                "commit",
                "--quiet",
                "-S",
                "-m",
                "self-bootstrapped fixture v1.2 freeze",
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        freeze_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        key_blob = base64.b64decode(public_fields[1], validate=True)
        anchors = {
            "CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION": floor,
            "EXPECTED_CURRENT_INITIAL_BINDING_REVISION": freeze_revision,
            "EXPECTED_CURRENT_INITIAL_BINDING_SHA256": hashlib.sha256(
                json.dumps(
                    binding,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "EXPECTED_CURRENT_INITIAL_BINDING_ALLOWED_SIGNERS_SHA256": (
                hashlib.sha256(allowed_signers.read_bytes()).hexdigest()
            ),
            "EXPECTED_CURRENT_INITIAL_BINDING_SIGNING_KEY_FINGERPRINT": (
                "SHA256:"
                + base64.b64encode(hashlib.sha256(key_blob).digest())
                .decode("ascii")
                .rstrip("=")
            ),
        }
        with patch.multiple(control, **anchors):
            errors: list[str] = []
            self.assertFalse(
                control._current_normative_profile_binding_history_valid(
                    self.root, binding, errors
                )
            )
        self.assertIn("current v1.2 public freeze commit scope is not exact", errors)

    def test_v12_revocation_cannot_reopen_its_generation(self) -> None:
        floor = self.initialize_fixture_repository()
        first = self.current_v12_profile_binding()
        program = self.read_json("product/program.json")
        program["normativeProfileBinding"] = first
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "fixture v1.1 freeze"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        program["normativeProfileBinding"] = {**first, "state": "revoked"}
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "fixture v1.1 revoke"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        successor = deepcopy(first)
        program["normativeProfileBinding"] = successor
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "fixture forbidden successor"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with patch.object(
            control,
            "CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION",
            floor,
        ):
            errors: list[str] = []
            self.assertFalse(
                control._current_normative_profile_binding_history_valid(
                    self.root, successor, errors
                )
            )
        self.assertIn(
            "revoked current cohort cannot open a successor generation",
            errors,
        )

    def test_v12_revoked_state_does_not_consult_v11_private_resource_or_trigger(
        self,
    ) -> None:
        binding = self.current_v12_profile_binding()
        binding["state"] = "revoked"
        program = self.read_json("product/program.json")
        program["status"] = "stopped"
        program["normativeProfileBinding"] = binding
        with patch.object(
            control,
            "CURRENT_PROFILE_FREEZE_ENABLED",
            True,
        ), patch(
            "harness.control._current_profile_binding_material_valid",
            return_value=True,
        ), patch(
            "harness.control._current_normative_profile_binding_history_valid",
            return_value=True,
        ), patch(
            "harness.control._current_initial_authorization_private_resource_absent",
            side_effect=AssertionError("v1.2 revocation consulted v1.1 private resource"),
        ) as private_absent, patch(
            "harness.control._current_initial_expiry_cleanup_trigger_absent",
            side_effect=AssertionError("v1.2 revocation consulted v1.1 expiry trigger"),
        ) as trigger_absent:
            errors: list[str] = []
            self.assertTrue(
                control._normative_profile_binding_valid(ROOT, program, errors),
                errors,
            )
        private_absent.assert_not_called()
        trigger_absent.assert_not_called()

    def test_v11_profile_candidate_identity_cannot_drift_before_freeze(self) -> None:
        protocol_relative = control.EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_LOCATOR
        protocol = self.read_json(protocol_relative)
        protocol["versionResolutionRule"] = "execute latest without resolving it"
        self.write_json(protocol_relative, protocol)

        errors: list[str] = []
        valid = control._current_profile_candidate_artifacts_valid(
            self.root, errors
        )

        self.assertFalse(valid)
        self.assertTrue(self.report()["criterionStates"]["G3"])
        self.assertIn(
            "code-owned current profile candidate artifact identity changed: "
            + protocol_relative,
            errors,
        )

    def test_v11_profile_candidate_cannot_disappear_before_freeze(self) -> None:
        profile_relative = control.EXPECTED_CURRENT_PROFILE_CANDIDATE_LOCATOR
        (self.root / profile_relative).unlink()

        errors: list[str] = []
        valid = control._current_profile_candidate_artifacts_valid(
            self.root, errors
        )

        self.assertFalse(valid)
        self.assertTrue(self.report()["criterionStates"]["G3"])
        self.assertIn(
            "missing current profile candidate artifact " + profile_relative,
            errors,
        )

    def test_v12_product_authority_remains_the_three_machine_jsons(self) -> None:
        acceptance = self.read_json("product/acceptance.json")
        g3 = next(item for item in acceptance["criteria"] if item["id"] == "G3")

        self.assertIn(
            "constitution, current program and current acceptance contract "
            "remain the only product authority",
            g3["statement"],
        )
        self.assertIn("verifier only enforces", g3["statement"])
        self.assertNotIn("contract and verifier remain", g3["statement"])
        self.assertEqual(
            control._criteria_contract_digest(acceptance["criteria"]),
            control.EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256,
        )
        self.assertIn("The verifier enforces current authority shape", control.__doc__)

    def test_v10_stopped_authority_bytes_are_code_pinned(self) -> None:
        errors: list[str] = []
        self.assertTrue(control._v10_historical_authority_valid(ROOT, errors), errors)

        committed_blob = control._committed_blob

        def drifted(root: Path, revision: str, locator: str, digest: str) -> bool:
            if locator == "product/acceptance.json":
                return False
            return committed_blob(root, revision, locator, digest)

        errors = []
        with patch("harness.control._committed_blob", side_effect=drifted):
            self.assertFalse(control._v10_historical_authority_valid(ROOT, errors))
        self.assertIn(
            "v1.0 historical authority identity changed: product/acceptance.json",
            errors,
        )

    def test_v11_stopped_authority_bytes_are_code_pinned(self) -> None:
        errors: list[str] = []
        self.assertTrue(control._v11_historical_authority_valid(ROOT, errors), errors)

        committed_blob = control._committed_blob

        def drifted(root: Path, revision: str, locator: str, digest: str) -> bool:
            if locator == "harness/control.py":
                return False
            return committed_blob(root, revision, locator, digest)

        errors = []
        with patch("harness.control._committed_blob", side_effect=drifted):
            self.assertFalse(control._v11_historical_authority_valid(ROOT, errors))
        self.assertIn(
            "v1.1 historical authority identity changed: harness/control.py",
            errors,
        )

    def test_v12_environment_attribution_is_acceptance_owned_and_cross_criterion(self) -> None:
        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        contract = acceptance["environmentAttribution"]
        self.assertEqual(
            contract["environmentClasses"],
            ["observed-native-minimum", "user-configured"],
        )
        self.assertEqual(
            contract["treatmentArms"],
            ["without-harness", "with-exact-harness"],
        )
        self.assertIn("task-host execution unit runs once", contract["assignmentRule"])
        self.assertIn("matched field evidence", contract["comparisonRule"])
        self.assertIn("present or unknown", contract["observedNativeMinimumRule"])
        self.assertIn("Harness repository guidance", contract["neutralWorkspaceRule"])
        self.assertIn("environment-independent", contract["historicalEvidenceRule"])
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        for criterion_id in ("O1", "O2", "O3", "O4", "O5"):
            self.assertIn(
                "environmentAttributionBinding",
                criteria[criterion_id]["operationalization"]["preRegistrationFields"],
            )
        self.assertIn("clean isolated Codex environment", criteria["O2"]["threshold"])
        self.assertIn("declared user-configured environment", criteria["O2"]["threshold"])
        self.assertIn("clean Windows checkout", criteria["O5"]["threshold"])
        self.assertIn("hosted macOS CI", criteria["O5"]["threshold"])

    def test_v11_initial_environment_is_a_starting_state_not_a_static_ceiling(self) -> None:
        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        contract = acceptance["environmentAttribution"]

        self.assertIn("starting condition", contract["initialStateRule"])
        self.assertIn("treatment-mediated lifecycle deltas", contract["initialStateRule"])
        self.assertIn("authority-and-available-source envelope", contract["comparisonRule"])
        self.assertIn("supported task-scoped override", contract["taskTimeAdaptationRule"])
        self.assertIn("smallest exact step", contract["humanInterventionRule"])
        self.assertIn("verifies the result", contract["humanInterventionRule"])
        self.assertIn(
            "initial-authority-and-available-source-envelope",
            contract["manifestFields"],
        )

    def test_v11_resolves_current_capability_identity_per_decision(self) -> None:
        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        rule = acceptance["environmentAttribution"]["versionResolutionRule"]

        self.assertIn("current suitable official or maintained bounded as-of source", rule)
        self.assertIn("bounded as-of source", rule)
        self.assertIn("exact version, commit or package identity", rule)
        self.assertIn("do not lock one historical version across tasks", rule)
        self.assertIn("unresolved mutable label", rule)
        self.assertIn("re-register or honestly stop", rule)

    def test_v11_distinguishes_human_only_actions_from_agent_work_transfer(self) -> None:
        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        contract = acceptance["environmentAttribution"]
        criteria = {item["id"]: item for item in acceptance["criteria"]}

        self.assertIn("technically or authoritatively unavoidable", contract["humanInterventionRule"])
        self.assertIn("prohibited transfer of Agent-owned work", contract["humanInterventionRule"])
        self.assertIn("all human actions", contract["burdenRule"])
        self.assertIn("legitimate human-only", contract["burdenRule"])
        self.assertIn("prohibited transfers", contract["burdenRule"])
        self.assertIn("zero prohibited transfer", criteria["G1"]["threshold"])
        self.assertIn("human-only step", criteria["G1"]["threshold"])
        self.assertIn("authorityStopAndResume", criteria["O2"]["operationalization"]["requiredMeasures"])
        self.assertIn(
            "The user grants exact Codex installation",
            criteria["O2"]["operationalization"]["humanAuthority"],
        )

    def test_v11_capability_lifecycle_covers_guidance_and_retirement(self) -> None:
        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        o3 = next(item for item in acceptance["criteria"] if item["id"] == "O3")
        lifecycle_rule = acceptance["environmentAttribution"]["lifecycleRule"]

        for verb in (
            "install",
            "configure",
            "enable",
            "disable",
            "downgrade",
            "rollback",
            "retire",
            "persist",
        ):
            self.assertIn(verb, lifecycle_rule)
        self.assertIn("availableNativeAndAuthorizedRoutes", o3["operationalization"]["preRegistrationFields"])
        self.assertIn("sourceVersionAuthorityRollbackAndCleanup", o3["operationalization"]["preRegistrationFields"])
        self.assertIn("effectiveModelProviderReasoningDelegationAndExecutionIdentity", o3["operationalization"]["requiredMeasures"])
        self.assertIn("humanOnlyVersusAgentOwnedAction", o3["operationalization"]["requiredMeasures"])
        self.assertIn("rollbackRetirementAndResidue", o3["operationalization"]["requiredMeasures"])

        program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        progression = program["progressionPolicy"]
        self.assertIn("starting-state", progression["taskTimeAdaptationDisposition"])
        self.assertIn("guides-and-verifies", progression["humanOnlyActionDisposition"])
        self.assertIn("resolve-current-suitable-source", progression["versionResolutionDisposition"])

    def test_v12_prefers_native_reasoning_routes_and_only_residual_shortfall_controls(
        self,
    ) -> None:
        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        constitution = json.loads(
            (ROOT / "product/constitution.json").read_text(encoding="utf-8")
        )
        contract = acceptance["environmentAttribution"]
        criteria = {item["id"]: item for item in acceptance["criteria"]}

        self.assertIn(
            "model-provider-reasoning-effort-delegation-and-routing-state",
            contract["manifestFields"],
        )
        self.assertIn("host-native adaptive model", contract["taskTimeAdaptationRule"])
        self.assertIn("without imposing a Harness router", contract["taskTimeAdaptationRule"])
        self.assertIn("quality, latency, cost or failure", contract["taskTimeAdaptationRule"])
        self.assertIn("narrows the claim or honestly stops", contract["taskTimeAdaptationRule"])
        self.assertIn("switch model, provider, reasoning effort", contract["lifecycleRule"])
        self.assertIn("do not turn a current model", contract["lifecycleRule"])

        shortfall_rule = contract["shortfallResolutionRule"]
        self.assertIn("is not a solved shortfall", shortfall_rule)
        self.assertIn("first reuse a sufficient native", shortfall_rule)
        self.assertIn("evidenced residual semantic gap", shortfall_rule)
        self.assertIn("narrow the claim or stop", shortfall_rule)
        self.assertIn("Do not run or persist a complete shortfall checklist", shortfall_rule)

        self.assertIn("does not create a Harness router", criteria["O3"]["statement"])
        self.assertIn("reasoning-effort mismatch", " ".join(criteria["O3"]["operationalization"]["falsifiers"]))
        self.assertIn(
            "source presence, mapping text, code existence or test count alone fails",
            criteria["O1"]["operationalization"]["passRule"],
        )
        self.assertTrue(
            any(
                "shortfall evidence is not coverage by reference" in invariant
                for invariant in constitution["fixedInvariants"]
            )
        )
        self.assertIn(
            "model-provider-reasoning-effort-and-delegation route",
            constitution["adaptiveSurfaces"],
        )

        research = (ROOT / "docs/strategy/RESEARCH-AND-POC-PLAN.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("YIYUAN-CALIBRATION@e060a08f05361cb4cc9a67be050236cdbbde1de5", research)
        self.assertIn("5b2bb49446c43b5d41bdd14fa6a844abefb7c1cc", research)
        self.assertIn("Reference, classification, admission, and implementation", research)
        for source_slice in (f"SG-{index:02d}" for index in range(1, 13)):
            self.assertIn(f"| {source_slice} ", research)

    def test_v12_shortfall_reference_cannot_be_promoted_to_solution(self) -> None:
        self.mutate(
            "product/acceptance.json",
            lambda value: value["environmentAttribution"].__setitem__(
                "shortfallResolutionRule",
                "referenced means solved",
            ),
        )

        report = self.report()

        self.assertFalse(report["valid"])
        self.assertIn("acceptance environmentAttribution is invalid", report["errors"])

    def test_v11_rejects_v10_frozen_or_revoked_binding_reuse(self) -> None:
        old_program = json.loads(
            subprocess.run(
                [
                    "git",
                    "show",
                    "910ac016f1e5963450e3cfc46f5056ab0a6b04d7:product/program.json",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__(
                "normativeProfileBinding", old_program["normativeProfileBinding"]
            ),
        )
        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=False,
            _normative_profile_binding_history_valid=lambda root, binding, errors: True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
        ):
            report = verify_product(self.root)
        self.assertFalse(report["valid"])
        self.assertIn(
            "current normative profile freeze is not enabled",
            report["errors"],
        )

    def test_v11_freeze_flag_cannot_activate_legacy_v10_mechanism(self) -> None:
        old_program = json.loads(
            subprocess.run(
                [
                    "git",
                    "show",
                    "910ac016f1e5963450e3cfc46f5056ab0a6b04d7:product/program.json",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__(
                "normativeProfileBinding", old_program["normativeProfileBinding"]
            ),
        )
        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=True,
            _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY=False,
            _current_normative_profile_binding_history_valid=lambda root, binding, errors, **kwargs: True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
        ):
            report = verify_product(self.root)
        self.assertFalse(report["valid"])
        self.assertIn(
            "frozen normative profile binding is not the code-owned v1.2 candidate",
            report["errors"],
        )

    def test_v11_freeze_flag_cannot_stop_an_unfrozen_program(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("status", "stopped"),
        )
        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=True,
            _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY=False,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
        ):
            report = verify_product(self.root)
        self.assertFalse(report["valid"])
        self.assertIn(
            "stopped current program requires its only cohort to be revoked",
            report["errors"],
        )

    def test_environment_attribution_contract_cannot_drift(self) -> None:
        self.mutate(
            "product/acceptance.json",
            lambda value: value["environmentAttribution"].__setitem__(
                "assignmentRule", "repeat one task until every arm passes"
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("acceptance environmentAttribution is invalid", report["errors"])

    def test_task_registration_rejects_placeholder_environment_binding(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        registration["preRegistrationValues"]["environmentAttributionBinding"] = (
            "fixture placeholder"
        )
        self.write_json(relative, registration)
        self.recommit_fixture_registration(program)
        self.write_json("product/program.json", program)
        report = self.report()

        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "task registration product/evidence/fixture-registration.json environment attribution binding is invalid",
            report["errors"],
        )

    def test_task_registration_rejects_environment_arm_or_manifest_mismatch(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        environment_binding = registration["preRegistrationValues"][
            "environmentAttributionBinding"
        ]
        environment_binding["treatmentArm"] = "without-harness"
        environment_binding["manifestSha256"] = "d" * 64
        self.write_json(relative, registration)
        self.recommit_fixture_registration(program)
        self.write_json("product/program.json", program)

        report = self.report()

        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "task registration product/evidence/fixture-registration.json environment attribution binding is invalid",
            report["errors"],
        )

    def test_task_registration_rejects_ambiguous_environment_manifest_json(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        registration_relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(registration_relative)
        environment_binding = registration["preRegistrationValues"][
            "environmentAttributionBinding"
        ]
        manifest_relative = environment_binding["manifestLocator"]
        manifest = self.read_json(manifest_relative)
        ambiguous = json.dumps(manifest, ensure_ascii=False, indent=2).replace(
            '"schema": 1,', '"schema": 1,\n  "schema": 1,', 1
        ) + "\n"
        (self.root / manifest_relative).write_text(ambiguous, encoding="utf-8")
        (self.root / registration_relative).unlink()
        subprocess.run(
            ["git", "add", manifest_relative, registration_relative],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "ambiguous environment manifest"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        manifest_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        committed_manifest = subprocess.run(
            ["git", "show", f"{manifest_revision}:{manifest_relative}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        environment_binding["manifestRevision"] = manifest_revision
        environment_binding["manifestSha256"] = hashlib.sha256(
            committed_manifest
        ).hexdigest()
        self.write_json(registration_relative, registration)
        subprocess.run(
            ["git", "add", registration_relative],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "bind ambiguous manifest"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        registration_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        committed_registration = subprocess.run(
            ["git", "show", f"{registration_revision}:{registration_relative}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        binding = program["increments"][0]["taskRegistration"]
        binding["sourceRevision"] = registration_revision
        binding["sha256"] = hashlib.sha256(committed_registration).hexdigest()
        self.write_json("product/program.json", program)

        report = self.report()

        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "task registration product/evidence/fixture-registration.json environment attribution binding is invalid",
            report["errors"],
        )

    def test_task_registration_rejects_boolean_environment_manifest_schema(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(
                value,
                increment,
                environment_manifest_schema=True,
            )

        self.mutate("product/program.json", activate_o1)
        report = self.report()

        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "task registration product/evidence/fixture-registration.json environment attribution binding is invalid",
            report["errors"],
        )

    def test_current_public_evidence_excludes_private_runtime_identifiers(self) -> None:
        path_patterns = (
            re.compile(r"(?i)(?<![a-z0-9+.-])[a-z]:[\\/]"),
            re.compile(r"(?i)(?:^|[\s\"'])/(?:users|home|tmp)/[^\s\"']+"),
            re.compile(
                r"(?i)(?:^|[\s\"'])(?:[\\/]{1,2})(?:users|home)[\\/]"
            ),
            re.compile(
                r"(?i)(?:^|[\s\"'])\\\\[^\\/\s\"']+[\\/]"
                r"(?:[a-z]\$[\\/])?(?:users|home)[\\/]"
            ),
            re.compile(r"(?i)(?:^|[\s\"'])/(?:private/)?var/folders/"),
            re.compile(r"(?i)codex://threads/"),
            re.compile(r"(?i)(?:auth|credentials)\.json"),
            re.compile(
                r"(?i)(?:^|[\\/])\.claude[\\/]"
                r"(?:settings|settings\.local)\.json(?:$|[\s\"'])"
            ),
            re.compile(r"(?i)\bhardlink\b"),
            re.compile(r"(?i)\bmsg_[a-z0-9_-]{8,}\b"),
            re.compile(
                r"(?i)\b(?:thread|session|message|event)_"
                r"[a-z0-9][a-z0-9._:-]{7,}\b"
            ),
            re.compile(
                r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                r"[0-9a-f]{4}-[0-9a-f]{12}\b"
            ),
        )
        private_id_fragments = ("thread", "session", "message", "event")
        private_id_suffixes = ("id", "ids", "ref", "refs", "handle", "token")
        private_key_pattern = re.compile(
            r'(?i)"(?:thread|session|message|event)"\s*:'
            r'|"[^"\\]*(?:thread|session|message|event)[^"\\]*'
            r'(?:ids?|refs?|handle|token)"\s*:'
        )

        def findings(value: object, location: str = "$") -> list[str]:
            result: list[str] = []
            if isinstance(value, dict):
                for key, item in value.items():
                    folded = key.casefold()
                    compact = re.sub(r"[^a-z0-9]", "", folded)
                    if (
                        compact in private_id_fragments
                        and isinstance(item, str)
                        and item
                    ) or (
                        any(fragment in compact for fragment in private_id_fragments)
                        and compact.endswith(private_id_suffixes)
                    ):
                        result.append(f"{location}.{key}: private host identifier key")
                    result.extend(findings(item, f"{location}.{key}"))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    result.extend(findings(item, f"{location}[{index}]"))
            elif isinstance(value, str):
                for pattern in path_patterns:
                    if pattern.search(value):
                        result.append(f"{location}: {pattern.pattern}")
                        break
            return result

        sanitized_control = {
            "taskIdentity": fixture_task_identity("public-example"),
            "source": {"identity": "sha256:" + ("a" * 64)},
            "sessionDigest": "b" * 64,
            "eventType": "SessionStart",
            "reference": "https://example.com/tmp/reference",
            "claimLimits": ["sanitized public evidence only"],
        }
        self.assertEqual(findings(sanitized_control), [])
        for private_control in (
            {"sourceThreadId": "01234567-89ab-4cde-8fab-0123456789ab"},
            {"locator": "C:/Users/example/private-record.jsonl"},
            {"locator": r"\Users\example\private-record.jsonl"},
            {"locator": r"\\HOST\Users\example\private-record.jsonl"},
            {"locator": r"\\HOST\C$\Users\example\private-record.jsonl"},
            {"locator": "/home/example/private-record.jsonl"},
            {"locator": "/private/var/folders/aa/private-record.jsonl"},
            {"locator": "codex://threads/private"},
            {"locator": "auth.json"},
            {"locator": "~/.claude/settings.json"},
            {"topology": "credential hardlink"},
            {"locator": "msg_opaqueprivate123"},
            {"locator": "session_01JPRIVATEHOSTVALUE"},
            {"locator": "event_opaqueprivate123"},
            {"session": "opaque-host-session"},
            {"eventRef": "opaque-host-event"},
        ):
            self.assertTrue(findings(private_control), private_control)

        violations: list[str] = []
        evidence_root = ROOT / "product/evidence"
        if evidence_root.exists():
            self.assertFalse(control._link_or_reparse(evidence_root), evidence_root)
        allowed_evidence_parents = {
            evidence_root,
            evidence_root / "environment-manifests",
        }
        for path in sorted(evidence_root.rglob("*")):
            self.assertFalse(control._link_or_reparse(path), path)
            if path.is_dir():
                continue
            self.assertIn(path.parent, allowed_evidence_parents, path)
            self.assertEqual(path.suffix, ".json", path)
            raw = path.read_bytes()
            self.assertLessEqual(len(raw), control.MAX_DOCUMENT_BYTES, path)
            decoded = raw.decode("utf-8")
            self.assertIsNone(private_key_pattern.search(decoded), path)
            for pattern in path_patterns:
                self.assertIsNone(pattern.search(decoded), f"{path}: {pattern.pattern}")

            def unique_object(pairs: list[tuple[str, object]]) -> dict:
                document: dict[str, object] = {}
                for key, item in pairs:
                    self.assertNotIn(key, document, f"duplicate key in {path}: {key}")
                    document[key] = item
                return document

            document = json.loads(decoded, object_pairs_hook=unique_object)
            violations.extend(
                f"{path.relative_to(ROOT).as_posix()} {item}"
                for item in findings(document)
            )
        self.assertEqual(violations[:20], [], f"private evidence remains: {violations[:20]}")

    def test_terminal_cohort_requires_proactive_context_lifecycle_coverage(
        self,
    ) -> None:
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        o4 = criteria["O4"]
        self.assertIn("startingAuthorityGoalAndCarrierState", o4["operationalization"]["preRegistrationFields"])
        self.assertIn("carrierSignalProvenanceAndUnknownRule", o4["operationalization"]["requiredMeasures"])
        self.assertIn("destinationVerificationBeforeSourceRelease", o4["operationalization"]["requiredMeasures"])
        self.assertIn("native compaction recovery", o4["threshold"])

    def test_all_outcomes_bind_one_frozen_profile_and_cohort_protocol(self) -> None:
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        for criterion_id in ("O1", "O2", "O3", "O4", "O5"):
            with self.subTest(criterion_id=criterion_id):
                fields = criteria[criterion_id]["operationalization"][
                    "preRegistrationFields"
                ]
                self.assertIn("normativeProfileIdentity", fields)
                self.assertIn("cohortProtocolIdentity", fields)
                self.assertIn("profileSha256", fields)
                self.assertIn("cohortProtocolSha256", fields)
                self.assertNotIn("enrollmentSurfaceAndCursor", fields)
                self.assertNotIn("naturalDemandEventAndPrivateBinding", fields)

    def test_controlled_conformance_separates_delivery_from_field_validation(self) -> None:
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        profile = (ROOT / "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.2.md").read_text(
            encoding="utf-8"
        )
        protocol = json.loads(
            (ROOT / "docs/CONTROLLED-CONFORMANCE-PROTOCOL-V1.2.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            "subordinate operands or evidence",
            criteria["G3"]["statement"],
        )
        self.assertIn("immutable subordinate", profile)
        self.assertIn(
            "lifecyclePhaseApplicabilityAndOwner",
            criteria["O1"]["operationalization"]["preRegistrationFields"],
        )
        self.assertIn(
            "sufficient native or external reuse",
            criteria["O1"]["operationalization"]["passRule"],
        )
        self.assertIn("Natural tasks are optional", acceptance["progressRule"])
        self.assertIn("not require a bespoke Harness mechanism", acceptance["progressRule"])
        self.assertIn("immutable stopped history", acceptance["progressRule"])
        self.assertIn("No private source-capture key", profile)
        self.assertIn("not a feature backlog", profile)
        self.assertIn("or a static perfect score", acceptance["progressRule"])
        self.assertEqual(
            protocol["scenarioEligibilityRule"],
            "acceptance-mapped-controlled-or-field-unit-with-no-invented-natural-demand",
        )
        self.assertEqual(
            protocol["registrationRule"],
            "committed-criterion-scoped-registration-and-validator-before-outcome-bearing-execution",
        )
        self.assertIn("later-separate-field-evidence", protocol["fieldValidationRule"])
        self.assertNotIn("preResponseCaptureRule", protocol)
        self.assertNotIn("hmacDomain", protocol)

    def test_terminal_contract_prevents_sample_selection_and_duplicate_tasks(self) -> None:
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        o2 = criteria["O2"]["operationalization"]
        self.assertIn("scenarioIdentityAndClass", o2["preRegistrationFields"])
        self.assertIn("exactCodexVersionAndEnvironmentClass", o2["preRegistrationFields"])
        self.assertGreaterEqual(o2["minimumSampleCount"], 4)
        self.assertIn("cannot be represented as independent natural tasks", acceptance["environmentAttribution"]["assignmentRule"])
        self.assertIn("comparative real-task value", criteria["O5"]["threshold"])

    def test_terminal_release_protocol_separates_authorization_and_execution(self) -> None:
        program = self.read_json("product/program.json")
        user = program["authorityBoundary"]["userOwns"]
        agent = program["authorityBoundary"]["agentOwnsWithinBoundedAuthority"]
        self.assertIn("release-authorization", user)
        self.assertIn("publication-authorization", user)
        self.assertIn("authorized-release-execution", agent)
        self.assertIn("authorized-publication-execution", agent)
        acceptance = self.read_json("product/acceptance.json")
        o5 = next(item for item in acceptance["criteria"] if item["id"] == "O5")
        fields = o5["operationalization"]["preRegistrationFields"]
        self.assertIn("releaseCandidateAndTagDerivationRule", fields)
        self.assertNotIn("releaseCandidateCommitAndTag", fields)
        self.assertIn("namedHumanReleaseAuthorizationRule", fields)
        self.assertIn("immutableTagPublicationAndVerificationProtocol", fields)
        self.assertIn("no post-tag product mutation", o5["operationalization"]["passRule"])
        self.assertIn(
            "not an unknowable future commit", o5["operationalization"]["passRule"]
        )

    def test_task_topology_lifecycle_is_agent_owned(self) -> None:
        constitution = self.read_json("product/constitution.json")
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}

        self.assertIn(
            "task-topology-selection-reconciliation-merge-release-and-cleanup",
            constitution["collaborationModel"]["agentObligations"],
        )
        self.assertTrue(
            any(
                invariant.startswith("task topology is demand-driven:")
                for invariant in constitution["fixedInvariants"]
            )
        )
        o4 = criteria["O4"]
        self.assertEqual(o4["name"], "continuous self-correction and carrier control")
        self.assertIn("code topology", o4["metric"])
        self.assertIn(
            "startingAuthorityGoalAndCarrierState",
            o4["operationalization"]["preRegistrationFields"],
        )
        self.assertIn(
            "destinationVerificationBeforeSourceRelease",
            o4["operationalization"]["requiredMeasures"],
        )
        self.assertIn("destination or final-state reconciliation", o4["operationalization"]["passRule"])

    def test_context_carrier_fitness_and_transition_is_agent_owned(self) -> None:
        constitution = self.read_json("product/constitution.json")
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}

        self.assertIn(
            "context-carrier-fitness-observation-and-proactive-transition",
            constitution["collaborationModel"]["agentObligations"],
        )
        self.assertTrue(
            any(
                invariant.startswith("conversation-carrier fitness is Agent-owned:")
                for invariant in constitution["fixedInvariants"]
            )
        )
        o4 = criteria["O4"]["operationalization"]
        self.assertIn("startingAuthorityGoalAndCarrierState", o4["preRegistrationFields"])
        self.assertIn("carrierSignalProvenanceAndUnknownRule", o4["requiredMeasures"])
        self.assertIn("divergenceDetectionBeforeFurtherMaterialEffect", o4["requiredMeasures"])
        self.assertIn("destinationVerificationBeforeSourceRelease", o4["requiredMeasures"])
        self.assertIn("destination or final-state reconciliation", o4["passRule"])

    def test_public_cli_reports_the_same_contract(self) -> None:
        completed = self.run_cli(root=ROOT)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        live_program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["release"], "v1.2")
        self.assertEqual(report["programStatus"], live_program["status"])
        self.assertEqual(report["activeIncrement"], live_program["activeIncrementId"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"], {"verified": 1, "total": 5})
        self.assertTrue(report["valid"], report["errors"])

    def test_source_carrier_release_preflight_fails_closed_and_tracks_binding(self) -> None:
        frozen = {
            "normativeProfileBinding": {
                "state": "frozen",
                "cohortActivation": {"source": "fixture-live-source"},
            }
        }
        self.assertEqual(
            control._source_carrier_release_preflight(frozen, True),
            {
                "allowed": False,
                "state": "retain-live-source-verification",
                "reason": (
                    "frozen-cohort-source-remains-required-for-live-verifiability"
                ),
                "scope": "live-cohort-source-dependency-only",
            },
        )
        self.assertEqual(
            control._source_carrier_release_preflight(
                {
                    "normativeProfileBinding": {
                        "state": "frozen",
                        "cohortActivation": None,
                    }
                },
                True,
            ),
            {
                "allowed": True,
                "state": "release-eligible",
                "reason": "no-live-frozen-cohort-source-dependency",
                "scope": "live-cohort-source-dependency-only",
            },
        )
        for state in ("unfrozen", "revoked"):
            with self.subTest(state=state):
                self.assertEqual(
                    control._source_carrier_release_preflight(
                        {"normativeProfileBinding": {"state": state}}, True
                    ),
                    {
                        "allowed": True,
                        "state": "release-eligible",
                        "reason": "no-live-frozen-cohort-source-dependency",
                        "scope": "live-cohort-source-dependency-only",
                    },
                )
        self.assertEqual(
            control._source_carrier_release_preflight(frozen, False),
            {
                "allowed": False,
                "state": "unknown-stop-before-release",
                "reason": "authority-verification-failed",
                "scope": "live-cohort-source-dependency-only",
            },
        )

    def test_missing_live_source_blocks_carrier_release(self) -> None:
        errors: list[str] = []
        snapshot = control._read_stable_initial_authorization_snapshot(
            self.root / "absent-live-source.jsonl",
            str(self.root),
            errors,
            generation_label="current v1.1 binding",
        )
        self.assertIsNone(snapshot)
        self.assertEqual(
            errors,
            ["current v1.1 binding authorization source event is unavailable"],
        )
        self.assertFalse(
            control._source_carrier_release_preflight(
                {"normativeProfileBinding": {"state": "frozen"}},
                authority_valid=False,
            )["allowed"]
        )

    def test_evidence_git_cache_is_bounded_to_one_verification_context(self) -> None:
        token = control._EVIDENCE_GIT_CACHE.set({})
        try:
            with patch("harness.control.subprocess.Popen", wraps=subprocess.Popen) as run:
                self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
                self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
                self.assertEqual(run.call_count, 1)
        finally:
            control._EVIDENCE_GIT_CACHE.reset(token)

        with patch("harness.control.subprocess.Popen", wraps=subprocess.Popen) as run:
            self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
            self.assertEqual(run.call_count, 1)

    def test_evidence_git_uses_absolute_binary_and_sanitized_configuration(self) -> None:
        class CompletedProcess:
            def __init__(self) -> None:
                self.stdout = BytesIO(b"observed")

            def poll(self) -> int:
                return 0

            def kill(self) -> None:
                raise AssertionError("completed process must not be killed")

            def wait(self) -> int:
                return 0

        completed = CompletedProcess()
        with (
            patch.dict(
                os.environ,
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "core.fsmonitor",
                    "GIT_CONFIG_VALUE_0": "malicious-command",
                },
            ),
            patch("harness.control.subprocess.Popen", return_value=completed) as run,
        ):
            self.assertEqual(
                control._evidence_git(self.root, "rev-parse", "HEAD"),
                b"observed",
            )
        command = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertTrue(Path(command[0]).is_absolute())
        self.assertNotEqual(command[0].casefold(), "git")
        self.assertIn("core.fsmonitor=false", command)
        self.assertIn(f"core.hooksPath={os.devnull}", command)
        self.assertIn("diff.external=", command)
        self.assertNotIn("GIT_CONFIG_COUNT", environment)
        self.assertEqual(environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)

    def test_public_tag_lookup_cannot_load_repository_url_or_tls_overrides(self) -> None:
        self.initialize_fixture_repository()
        subprocess.run(
            [
                "git",
                "config",
                f"url.https://attacker.invalid/.insteadOf",
                control.EXPECTED_PUBLIC_REMOTE,
            ],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "http.sslVerify", "false"],
            cwd=self.root,
            check=True,
        )

        class CompletedProcess:
            def __init__(self) -> None:
                self.stdout = BytesIO(b"")

            def poll(self) -> int:
                return 0

            def kill(self) -> None:
                raise AssertionError("completed process must not be killed")

            def wait(self) -> int:
                return 0

        with patch(
            "harness.control.subprocess.Popen",
            return_value=CompletedProcess(),
        ) as run:
            self.assertEqual(
                control._evidence_git(
                    self.root,
                    "ls-remote",
                    "--tags",
                    control.EXPECTED_PUBLIC_REMOTE,
                    "refs/tags/v1.1.0",
                ),
                b"",
            )
        command = run.call_args.args[0]
        process_cwd = Path(run.call_args.kwargs["cwd"])
        environment = run.call_args.kwargs["env"]
        self.assertNotEqual(process_cwd, self.root)
        self.assertFalse((process_cwd / ".git").exists())
        self.assertEqual(environment["GIT_CEILING_DIRECTORIES"], str(process_cwd))
        self.assertIn("http.sslVerify=true", command)
        self.assertIn("credential.helper=", command)
        self.assertIn("protocol.file.allow=never", command)
        self.assertIn(control.EXPECTED_PUBLIC_REMOTE, command)

    def test_evidence_git_rejects_repository_local_executable(self) -> None:
        local_git = self.root / "git.exe"
        local_git.write_bytes(b"not executable")
        with (
            patch("harness.control.shutil.which", return_value=str(local_git)),
            patch("harness.control.subprocess.Popen") as run,
        ):
            self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
        run.assert_not_called()

    def test_evidence_git_rejects_untrusted_external_path_binary(self) -> None:
        external_git = self.root.parent / "untrusted-git.exe"
        external_git.write_bytes(b"not executable")
        try:
            with (
                patch("harness.control.shutil.which", return_value=str(external_git)),
                patch("harness.control.subprocess.Popen") as run,
            ):
                self.assertIsNone(
                    control._evidence_git(self.root, "rev-parse", "HEAD")
                )
            run.assert_not_called()
        finally:
            external_git.unlink()

    def test_evidence_git_rejects_path_shaped_like_nested_program_files(self) -> None:
        shaped_git = self.root.parent / "attacker" / "Program Files" / "Git" / "cmd" / "git.exe"
        shaped_git.parent.mkdir(parents=True, exist_ok=True)
        shaped_git.write_bytes(b"not executable")
        try:
            with (
                patch("harness.control.shutil.which", return_value=str(shaped_git)),
                patch("harness.control.subprocess.Popen") as run,
            ):
                self.assertIsNone(
                    control._evidence_git(self.root, "rev-parse", "HEAD")
                )
            run.assert_not_called()
        finally:
            shaped_git.unlink()
            shaped_git.parent.rmdir()
            shaped_git.parent.parent.rmdir()
            shaped_git.parent.parent.parent.rmdir()

    def test_evidence_git_rejects_non_system_drive_install_shape(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows drive provenance only")

        def alternate_system_directory(buffer, size) -> int:
            del size
            buffer.value = "D:\\Windows\\System32"
            return len(buffer.value)

        with (
            patch.object(
                control.ctypes.windll.kernel32,
                "GetSystemDirectoryW",
                side_effect=alternate_system_directory,
            ),
            patch("harness.control.subprocess.Popen") as run,
        ):
            self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
        run.assert_not_called()

    def test_evidence_git_stdout_is_hard_bounded_and_process_is_stopped(self) -> None:
        class OversizedProcess:
            def __init__(self) -> None:
                self.stdout = BytesIO(b"x" * (control.MAX_GIT_OUTPUT_BYTES + 1))
                self.killed = False

            def poll(self) -> int | None:
                return -9 if self.killed else None

            def kill(self) -> None:
                self.killed = True

            def wait(self) -> int:
                return -9 if self.killed else 0

        process = OversizedProcess()
        with patch("harness.control.subprocess.Popen", return_value=process):
            self.assertIsNone(control._evidence_git(self.root, "show", "HEAD:large"))
        self.assertTrue(process.killed)

    def test_plain_cli_exposes_program_and_completion_states(self) -> None:
        completed = self.run_cli(json_output=False, root=ROOT)
        report = verify_product(ROOT)
        hosted_unavailable = self.hosted_private_authorization_source_is_unavailable(
            report
        )
        live_program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            completed.returncode,
            1 if hosted_unavailable else 0,
            completed.stderr,
        )
        self.assertIn(
            (
                f"v1.2: {live_program['status']}, "
                f"{report['completionState']} (1/5 outcomes)"
            ),
            completed.stdout,
        )
        if hosted_unavailable:
            self.assertIn(
                "revoked current v1.1 expiry cleanup trigger absence is unverifiable",
                completed.stderr,
            )
        else:
            self.assertEqual(completed.stderr, "")

    def test_codex_session_start_adapter_projects_live_authority(self) -> None:
        payload = self.codex_session_start_payload(source="resume")
        context = self.render_codex_fixture_context(payload)
        self.assertIsNotNone(context)
        projection = json.loads(context)
        live_program = json.loads(
            (self.root / "product/program.json").read_text(encoding="utf-8")
        )
        self.assertEqual(projection["adapter"], ADAPTER_ID)
        self.assertEqual(projection["event"], {"name": "SessionStart", "source": "resume"})
        self.assertEqual(projection["program"]["status"], live_program["status"])
        self.assertEqual(
            projection["authorityPaths"],
            [
                "product/constitution.json",
                "product/program.json",
                "product/acceptance.json",
            ],
        )
        self.assertEqual(projection["remainingContextCapacity"], "unknown")
        self.assertEqual(
            projection["verification"]["sourceCarrierRelease"],
            {
                "allowed": True,
                "state": "release-eligible",
                "reason": "no-live-frozen-cohort-source-dependency",
                "scope": "live-cohort-source-dependency-only",
            },
        )
        self.assertIn(
            "confirm-source-carrier-release-preflight-before-archive-or-release",
            projection["beforeMutation"],
        )
        self.assertEqual(projection["repositoryCheckpoint"]["state"], "unknown")
        self.assertEqual(projection["projectionBudget"]["characters"], len(context))
        self.assertLessEqual(len(context), 3072)
        self.assertEqual(
            projection["nextRoute"],
            "select-smallest-causally-justified-product-delivery-increment-from-current-authority",
        )
        self.assertNotIn("transcript_path", context)
        self.assertNotIn(payload["session_id"], context)

    def test_codex_session_start_adapter_supports_native_continuity_events(self) -> None:
        for source in ("startup", "resume", "clear", "compact"):
            with self.subTest(source=source):
                output = session_start_hook_output(
                    self.root, self.codex_session_start_payload(source=source)
                )
                self.assertEqual(output["continue"], True)
                self.assertEqual(output["suppressOutput"], True)
                context = json.loads(output["hookSpecificOutput"]["additionalContext"])
                self.assertEqual(context["event"]["source"], source)

    def test_codex_session_start_adapter_projects_exact_active_increment(self) -> None:
        self.mutate("product/program.json", self.activate_program)
        context = self.render_codex_fixture_context(
            self.codex_session_start_payload(source="compact")
        )
        projection = json.loads(context)
        self.assertEqual(projection["nextRoute"], "continue-current-active-increment")
        self.assertEqual(projection["currentWork"]["state"], "active")
        self.assertEqual(projection["currentWork"]["workItemState"], "active")
        self.assertRegex(projection["currentWork"]["identitySha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(FIXTURE_INCREMENT_ID, context)
        self.assertNotIn(FIXTURE_WORK_ID, context)
        self.assertNotIn("cleanupPaths", context)
        self.assertLessEqual(len(context), 3072)

    def test_common_projection_does_not_copy_unbounded_active_work_prose(self) -> None:
        def activate_long_work(program: dict) -> None:
            increment = self.activate_program(program)
            for field in ("observedProblem", "hypothesis", "falsifier", "stopCondition"):
                increment[field] = field + ":" + ("x" * 10000)

        self.mutate("product/program.json", activate_long_work)
        context = self.render_codex_fixture_context(
            self.codex_session_start_payload(source="compact")
        )
        projection = json.loads(context)
        self.assertEqual(projection["currentWork"]["state"], "active")
        self.assertNotIn(FIXTURE_INCREMENT_ID, context)
        self.assertNotIn("observedProblem", projection["currentWork"])
        self.assertNotIn("hypothesis", projection["currentWork"])
        self.assertLessEqual(len(context), 3072)

    def test_common_projection_has_a_bounded_second_level_fallback(self) -> None:
        context = _serialize_bounded(
            {
                "schema": 1,
                "adapter": "fixture-adapter",
                "role": "derived-read-only-continuation-context",
                "event": {"name": "SessionStart", "source": "compact"},
                "authorityPaths": ["product/program.json"],
                "verification": {
                    "valid": True,
                    "completionState": "in-progress",
                    "errors": ["verification:" + ("x" * 10000)],
                },
                "repositoryCheckpoint": {"state": "observed"},
                "program": {"status": "active"},
                "currentWork": {
                    "id": FIXTURE_INCREMENT_ID,
                    "workItem": {"id": FIXTURE_WORK_ID, "state": "active"},
                    "taskRegistration": "registration:" + ("x" * 10000),
                },
                "claimBoundary": "fixture claim boundary",
            }
        )
        projection = json.loads(context)
        self.assertLessEqual(len(context), 3072)
        self.assertEqual(
            projection["projectionBudget"]["state"], "fallback-overflow"
        )
        self.assertRegex(projection["currentWork"]["identitySha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(FIXTURE_INCREMENT_ID, context)
        self.assertNotIn("registration:" + ("x" * 100), context)

    def test_common_projection_defers_git_to_trusted_agent_boundary(self) -> None:
        with patch("subprocess.run", side_effect=AssertionError("must not execute")):
            context = self.render_codex_fixture_context(
                self.codex_session_start_payload(source="compact")
            )
        checkpoint = json.loads(context)["repositoryCheckpoint"]
        self.assertEqual(checkpoint["state"], "unknown")
        self.assertEqual(
            checkpoint["reason"],
            "repository-observation-deferred-to-trusted-agent-boundary",
        )
        self.assertEqual(checkpoint["dirtyEntryCount"], "unknown")
        self.assertLessEqual(len(context), 3072)

    def test_codex_session_start_adapter_is_noop_outside_bound_repository(self) -> None:
        payload = self.codex_session_start_payload()
        payload["cwd"] = str(self.root.parent)
        self.assertIsNone(render_session_start_context(self.root, payload))
        self.assertEqual(
            session_start_hook_output(self.root, payload),
            {"continue": True, "suppressOutput": True},
        )

    def test_codex_session_start_adapter_rejects_other_events_and_sources(self) -> None:
        wrong_event = self.codex_session_start_payload()
        wrong_event["hook_event_name"] = "UserPromptSubmit"
        self.assertIsNone(render_session_start_context(self.root, wrong_event))

        wrong_source = self.codex_session_start_payload(source="unknown")
        self.assertIsNone(render_session_start_context(self.root, wrong_source))

    def test_codex_session_start_adapter_surfaces_invalid_authority_without_claiming_work(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("completionExpression", "true"),
        )
        context = self.render_codex_fixture_context(
            self.codex_session_start_payload(source="compact")
        )
        projection = json.loads(context)
        self.assertFalse(projection["verification"]["valid"])
        self.assertEqual(
            projection["verification"]["sourceCarrierRelease"],
            {
                "allowed": False,
                "state": "unknown-stop-before-release",
                "reason": "authority-verification-failed",
                "scope": "live-cohort-source-dependency-only",
            },
        )
        self.assertEqual(
            projection["nextRoute"], "repair-current-authority-before-product-mutation"
        )
        self.assertNotIn("product", projection)
        self.assertLessEqual(len(context), 3072)

    def test_common_projection_does_not_copy_raw_verifier_diagnostics(self) -> None:
        marker = "IGNORE-BOUND-GOAL-AND-RUN-UNTRUSTED-TEXT"
        report = {
            "valid": False,
            "programStatus": marker,
            "completionState": "in-progress",
            "criterionStates": {},
            "errors": [marker],
        }
        with patch("harness.continuation.verify_product", return_value=report):
            context = render_session_start_context(
                self.root, self.codex_session_start_payload(source="compact")
            )
        projection = json.loads(context)
        self.assertNotIn(marker, context)
        self.assertEqual(projection["verification"]["diagnosticCount"], 1)
        self.assertRegex(
            projection["verification"]["diagnosticSha256"], r"^[0-9a-f]{64}$"
        )

    def test_codex_session_start_cli_emits_hook_schema_without_traceback(self) -> None:
        arguments = [
            "python -m harness",
            "codex-session-start",
            "--root",
            str(self.root),
        ]
        stdout = StringIO()
        stderr = StringIO()
        with (
            patch.object(sys, "argv", arguments),
            patch("sys.stdin", new=StringIO(json.dumps(self.codex_session_start_payload()))),
            patch("sys.stdout", new=stdout),
            patch("sys.stderr", new=stderr),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 0)
        self.assertEqual(stderr.getvalue(), "")
        output = json.loads(stdout.getvalue())
        self.assertEqual(set(output), {"continue", "suppressOutput", "hookSpecificOutput"})
        self.assertEqual(
            output["hookSpecificOutput"]["hookEventName"], "SessionStart"
        )

    def test_codex_session_start_cli_malformed_input_is_nonblocking_noop(self) -> None:
        arguments = [
            "python -m harness",
            "codex-session-start",
            "--root",
            str(self.root),
        ]
        stdout = StringIO()
        with (
            patch.object(sys, "argv", arguments),
            patch("sys.stdin", new=StringIO("not-json")),
            patch("sys.stdout", new=stdout),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"continue": True, "suppressOutput": True},
        )

    def test_codex_session_start_cli_oversized_input_is_nonblocking_noop(self) -> None:
        arguments = [
            "python -m harness",
            "codex-session-start",
            "--root",
            str(self.root),
        ]
        stdout = StringIO()
        with (
            patch.object(sys, "argv", arguments),
            patch("sys.stdin", new=StringIO("x" * 65_537)),
            patch("sys.stdout", new=stdout),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"continue": True, "suppressOutput": True},
        )

    def test_current_v11_expiry_cli_is_bounded_and_reports_not_due(self) -> None:
        arguments = [
            "python -m harness",
            "expire-current-cohort-private-evidence",
            "--root",
            str(self.root),
        ]
        stdout = StringIO()
        stderr = StringIO()

        def not_due(root, errors):
            self.assertEqual(root, self.root)
            errors.append("current v1.1 binding authorization expiry cleanup is not due")
            return False

        with (
            patch.object(sys, "argv", arguments),
            patch(
                "harness.__main__.expire_current_initial_authorization_private_evidence",
                side_effect=not_due,
            ),
            patch("sys.stdout", new=stdout),
            patch("sys.stderr", new=stderr),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 4)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("expiry cleanup is not due", stderr.getvalue())

    def test_codex_plugin_projection_is_thin_native_first_and_runtime_free(self) -> None:
        manifest = json.loads(
            (CODEX_PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["name"], "agent-autonomy-harness-codex")
        payload_identity = hashlib.sha256()
        payload_files = (
            "skills/deliver-demand-driven-outcome/SKILL.md",
            "skills/deliver-demand-driven-outcome/agents/openai.yaml",
            "skills/deliver-demand-driven-outcome/references/demand-to-capability-profile.md",
        )
        for relative in payload_files:
            payload_identity.update(relative.encode("utf-8"))
            payload_identity.update(b"\0")
            payload_identity.update((CODEX_PLUGIN_ROOT / relative).read_bytes())
            payload_identity.update(b"\0")
        self.assertEqual(
            manifest["version"],
            "1.2.0-conformance-candidate.1+codex.payload-"
            f"{payload_identity.hexdigest()[:12]}",
        )
        self.assertFalse((CODEX_PLUGIN_ROOT / "plugin.json").exists())
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("apps", manifest)
        self.assertEqual(
            manifest["interface"]["defaultPrompt"],
            [
                "Tell me the result you want. I will own the capability route, continuity, verification, and cleanup."
            ],
        )
        self.assertEqual(manifest["interface"]["capabilities"], ["Interactive", "Read"])
        self.assertNotIn("hooks", manifest)
        self.assertFalse((CODEX_PLUGIN_ROOT / "hooks/hooks.json").exists())
        self.assertFalse((CODEX_PLUGIN_ROOT / "scripts/carrier_hook.py").exists())
        self.assertFalse((CODEX_PLUGIN_ROOT / "scripts/enrollment_hook.py").exists())
        candidate_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                CODEX_PLUGIN_ROOT / ".codex-plugin/plugin.json",
                *(CODEX_PLUGIN_ROOT / relative for relative in payload_files),
            )
        ).lower()
        self.assertNotIn("cc switch", candidate_text)

    def test_codex_plugin_skill_is_implicit_thin_and_profile_bound(self) -> None:
        skill_root = (
            CODEX_PLUGIN_ROOT / "skills/deliver-demand-driven-outcome"
        )
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        interface = (skill_root / "agents/openai.yaml").read_text(
            encoding="utf-8"
        )
        projected_profile = (
            skill_root / "references/demand-to-capability-profile.md"
        ).read_bytes()

        self.assertLessEqual(len(skill.splitlines()), 60)
        self.assertNotIn("TODO", skill)
        self.assertIn("do not use for simple conversation", skill.lower())
        self.assertIn("read\n`references/demand-to-capability-profile.md` completely", skill)
        self.assertIn("Do not teach or expose capability", skill)
        self.assertIn("Treat remaining\n   capacity as unknown", skill)
        self.assertIn("allow_implicit_invocation: true", interface)
        self.assertNotIn("dependencies:", interface)
        self.assertEqual(
            projected_profile,
            (ROOT / "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.2.md").read_bytes(),
        )
        self.assertFalse((CODEX_PLUGIN_ROOT / ".mcp.json").exists())
        self.assertFalse((CODEX_PLUGIN_ROOT / ".app.json").exists())

    def test_codex_workspace_marketplace_exposes_only_the_thin_projection(
        self,
    ) -> None:
        marketplace = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["name"], "agent-autonomy-harness")
        self.assertEqual(
            marketplace["interface"], {"displayName": "Agent Autonomy Harness"}
        )
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "agent-autonomy-harness-codex")
        self.assertEqual(
            entry["source"],
            {
                "source": "local",
                "path": "./adapters/agent-autonomy-harness-codex",
            },
        )
        self.assertEqual(
            entry["policy"],
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        )
        source = (ROOT / entry["source"]["path"]).resolve(strict=True)
        self.assertEqual(source, CODEX_PLUGIN_ROOT.resolve(strict=True))
        self.assertNotEqual(source, ROOT.resolve(strict=True))

    def test_claude_reference_adapter_preserves_common_projection_semantics(
        self,
    ) -> None:
        codex = json.loads(
            self.render_codex_fixture_context(
                self.codex_session_start_payload(source="compact")
            )
        )
        claude = json.loads(
            self.render_claude_fixture_context(
                self.claude_session_start_payload(source="compact")
            )
        )
        self.assertEqual(claude["adapter"], CLAUDE_ADAPTER_ID)
        self.assertEqual(
            claude["referenceHostSubstrate"]["version"], "2.1.232"
        )
        self.assertIn(
            "Commercial Terms and Privacy Policy",
            claude["referenceHostSubstrate"]["licenseOrTerms"],
        )
        self.assertIn(
            "package README.md",
            claude["referenceHostSubstrate"]["licenseOrTerms"],
        )
        for projection in (codex, claude):
            projection.pop("adapter")
            projection.pop("referenceHostSubstrate")
            projection.pop("projectionBudget")
        self.assertEqual(claude, codex)

    def test_package_exports_explicit_host_adapters_and_keeps_codex_aliases(
        self,
    ) -> None:
        import harness

        self.assertIs(
            harness.render_codex_session_start_context,
            render_session_start_context,
        )
        self.assertIs(
            harness.render_claude_session_start_context,
            render_claude_session_start_context,
        )
        self.assertIs(
            harness.render_session_start_context,
            render_session_start_context,
        )
        self.assertIs(harness.session_start_hook_output, session_start_hook_output)

    def test_claude_reference_adapter_supports_native_continuity_events(self) -> None:
        for source in ("startup", "resume", "clear", "compact"):
            with self.subTest(source=source):
                context = self.render_claude_fixture_context(
                    self.claude_session_start_payload(source=source)
                )
                projection = json.loads(context)
                self.assertEqual(
                    projection["event"], {"name": "SessionStart", "source": source}
                )

    def test_claude_reference_adapter_is_noop_for_unsupported_input(self) -> None:
        outside = self.claude_session_start_payload()
        outside["cwd"] = str(self.root.parent)
        self.assertIsNone(render_claude_session_start_context(self.root, outside))
        wrong_event = self.claude_session_start_payload()
        wrong_event["hook_event_name"] = "UserPromptSubmit"
        self.assertIsNone(render_claude_session_start_context(self.root, wrong_event))

    def test_claude_plugin_projection_is_thin_skill_hook_and_payload_bound(self) -> None:
        manifest = json.loads(
            (CLAUDE_PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(
                encoding="utf-8"
            )
        )
        hooks = json.loads(
            (CLAUDE_PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "agent-autonomy-harness-claude")
        payload_identity = hashlib.sha256()
        payload_files = (
            "hooks/hooks.json",
            "scripts/session_start.py",
            "skills/deliver-demand-driven-task/SKILL.md",
            "skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
        )
        for relative in payload_files:
            payload_identity.update(relative.encode("utf-8"))
            payload_identity.update(b"\0")
            payload_identity.update((CLAUDE_PLUGIN_ROOT / relative).read_bytes())
            payload_identity.update(b"\0")
        self.assertEqual(
            manifest["version"],
            "0.2.0-candidate.7+claude.payload-"
            f"{payload_identity.hexdigest()[:12]}",
        )
        self.assertFalse((CLAUDE_PLUGIN_ROOT / "CLAUDE.md").exists())
        for component in ("commands", "agents", "mcpServers"):
            self.assertNotIn(component, manifest)
        self.assertNotIn("skills", manifest)
        self.assertTrue(
            (CLAUDE_PLUGIN_ROOT / "skills/deliver-demand-driven-task/SKILL.md").is_file()
        )
        self.assertEqual(set(hooks["hooks"]), {"SessionStart"})
        handlers = hooks["hooks"]["SessionStart"]
        self.assertEqual(len(handlers), 1)
        command = handlers[0]["hooks"][0]
        self.assertEqual(command["type"], "command")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", json.dumps(command))
        self.assertIn(".runtime/UNMATERIALIZED/python", command["command"])
        self.assertNotRegex(command["command"], r"(^|\s)(python|python3|git)(\s|$)")
        self.assertLessEqual(command["timeout"], 5)
        self.assertNotIn(str(ROOT), json.dumps(hooks))

    def test_claude_plugin_skill_preserves_its_exact_historical_method(self) -> None:
        claude_skill_root = CLAUDE_PLUGIN_ROOT / "skills/deliver-demand-driven-task"
        claude_skill = (claude_skill_root / "SKILL.md").read_text(encoding="utf-8")

        self.assertEqual(
            hashlib.sha256((claude_skill_root / "SKILL.md").read_bytes()).hexdigest(),
            "abb5906eeface94100b278e4ac182c39893a6be86a5de52577318164dc77103f",
        )
        self.assertEqual(
            (
                claude_skill_root
                / "references/demand-to-capability-profile.md"
            ).read_bytes(),
            (ROOT / "docs/DEMAND-TO-CAPABILITY-PROFILE.md").read_bytes(),
        )
        self.assertIn("Use implicitly", claude_skill)
        self.assertIn("do not use for simple conversation", claude_skill.lower())
        self.assertFalse((CLAUDE_PLUGIN_ROOT / ".mcp.json").exists())
        self.assertFalse((CLAUDE_PLUGIN_ROOT / "CLAUDE.md").exists())

    def test_claude_plugin_launcher_projects_from_nested_harness_cwd(self) -> None:
        nested = self.root / "docs/nested"
        nested.mkdir(parents=True)
        payload = self.claude_session_start_payload(source="compact")
        payload["cwd"] = str(nested)
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(CLAUDE_PLUGIN_ROOT / "scripts/session_start.py"),
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        projection = json.loads(completed.stdout)
        self.assertEqual(projection["adapter"], CLAUDE_ADAPTER_ID)
        self.assertEqual(projection["event"]["source"], "compact")
        self.assertNotIn("transcript_path", completed.stdout)
        self.assertNotIn(payload["session_id"], completed.stdout)

    def test_claude_plugin_launcher_is_silent_on_unsupported_or_drift(self) -> None:
        payload = self.claude_session_start_payload()
        payload["cwd"] = str(self.root.parent)
        for case in ("outside-root", "runtime-drift"):
            with self.subTest(case=case):
                if case == "runtime-drift":
                    payload["cwd"] = str(self.root)
                    with (self.root / "harness/control.py").open(
                        "a", encoding="utf-8"
                    ) as handle:
                        handle.write("\n# unreviewed runtime drift\n")
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        str(CLAUDE_PLUGIN_ROOT / "scripts/session_start.py"),
                    ],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stdout, "")

    def test_claude_plugin_launcher_is_silent_on_oversized_input(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(CLAUDE_PLUGIN_ROOT / "scripts/session_start.py"),
            ],
            input="x" * 65_537,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_plain_cli_sends_errors_to_stderr(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("id", "invalid-program"),
        )
        completed = self.run_cli(json_output=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ERROR: program id must be", completed.stderr)
        self.assertNotIn("ERROR:", completed.stdout)

    def test_cli_delegates_root_resolution_to_fail_closed_verifier(self) -> None:
        report = {
            "productId": "agent-autonomy-harness",
            "release": None,
            "programStatus": None,
            "valid": False,
            "completionState": "in-progress",
            "activeIncrement": None,
            "outcomes": {"verified": 0, "total": 5},
            "guardrails": {"passed": 0, "total": 4},
            "criterionStates": {},
            "errors": ["verifier failed closed: OSError"],
        }
        arguments = ["python -m harness", "verify", "--root", "unresolvable", "--json"]
        with (
            patch("harness.__main__.Path.resolve", side_effect=OSError("fixture")),
            patch("harness.__main__.verify_product", return_value=report) as verifier,
            patch.object(sys, "argv", arguments),
            patch("sys.stdout", new=StringIO()),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 1)
        verifier.assert_called_once()

    def test_release_id_drift_fails_closed(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("id", "renamed-program"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program id must be harness-product-program-v1.2", report["errors"])

    def test_coordinated_release_rename_cannot_self_promote(self) -> None:
        def rename_program(value: dict) -> None:
            value["release"] = "v9.9"
            value["id"] = "harness-product-program-v9.9"

        def rename_acceptance(value: dict) -> None:
            value["release"] = "v9.9"
            value["id"] = "harness-product-acceptance-v9.9"

        self.mutate("product/program.json", rename_program)
        self.mutate("product/acceptance.json", rename_acceptance)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("program release must be v1.2", report["errors"])

    def test_authority_json_rejects_duplicate_keys_and_nonfinite_constants(self) -> None:
        path = self.root / "product" / "program.json"
        baseline = path.read_text(encoding="utf-8")
        variants = {
            "duplicate-key": baseline.replace(
                '"status": "ready",',
                '"status": "ready",\n  "status": "ready",',
                1,
            ),
            "nonfinite-constant": baseline.replace(
                '"schema": 1,',
                '"schema": 1,\n  "nonStandard": NaN,',
                1,
            ),
        }
        for label, content in variants.items():
            with self.subTest(label=label):
                path.write_text(content, encoding="utf-8")
                report = self.report()
                self.assertFalse(report["valid"])
                self.assertIn("cannot read product program: invalid JSON", report["errors"])

    def test_authority_json_has_code_owned_byte_and_structure_limits(self) -> None:
        path = self.root / "product" / "program.json"
        path.write_text(
            '{"oversized":"' + ("x" * control.MAX_JSON_BYTES) + '"}',
            encoding="utf-8",
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "cannot read product program: byte limit exceeded",
            report["errors"],
        )

        nested: object = "leaf"
        for _ in range(control.MAX_JSON_DEPTH + 1):
            nested = {"child": nested}
        path.write_text(json.dumps(nested), encoding="utf-8")
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "cannot read product program: JSON resource limit exceeded",
            report["errors"],
        )

    def test_verifier_diagnostic_count_is_hard_bounded(self) -> None:
        errors: list[str] = []
        for index in range(control.MAX_VERIFICATION_DIAGNOSTICS * 4):
            control._error(errors, f"diagnostic-{index}")
        self.assertEqual(len(errors), control.MAX_VERIFICATION_DIAGNOSTICS)
        self.assertEqual(errors[-1], control.DIAGNOSTIC_LIMIT_MESSAGE)

    def test_verification_has_global_file_and_cumulative_byte_budgets(self) -> None:
        with patch("harness.control.MAX_VERIFICATION_FILES", 1):
            report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("verification file limit exceeded", report["errors"])

        with patch("harness.control.MAX_VERIFICATION_TOTAL_BYTES", 1):
            report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "verification cumulative byte limit exceeded", report["errors"]
        )

    def test_evidence_locator_reference_count_is_hard_bounded(self) -> None:
        locators = [
            "product/evidence/"
            + "".join(
                "A" if bit == "1" else "a" for bit in f"{index:09b}"
            )
            + ".json"
            for index in range(control.MAX_EVIDENCE_LOCATOR_REFERENCES + 1)
        ]
        criteria = {
            "O1": {"assessment": "verified", "evidence": locators},
        }
        errors: list[str] = []
        states, valid, _ = control._evidence_states(
            self.root, criteria, {}, {}, {}, errors
        )
        self.assertFalse(valid)
        self.assertFalse(states["O1"])
        self.assertIn("evidence locator reference limit exceeded", errors)

    def test_authority_schema_must_be_literal_integer_one(self) -> None:
        for relative, label in (
            ("product/constitution.json", "constitution"),
            ("product/program.json", "program"),
            ("product/acceptance.json", "acceptance"),
        ):
            with self.subTest(relative=relative):
                self.mutate(relative, lambda value: value.__setitem__("schema", True))
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(f"{label} schema must be integer 1", report["errors"])
                if relative == "product/acceptance.json":
                    self.reset_acceptance_fixture()
                else:
                    shutil.copy2(ROOT / relative, self.root / relative)

    def test_authority_documents_reject_undeclared_top_level_fields(self) -> None:
        variants = (
            (
                "product/constitution.json",
                "currentAuthorityOverride",
                True,
                "constitution",
            ),
            ("product/program.json", "completionState", "accepted", "program"),
            ("product/acceptance.json", "accepted", True, "acceptance"),
        )
        for relative, field, value, label in variants:
            with self.subTest(relative=relative, field=field):
                self.mutate(relative, lambda document: document.__setitem__(field, value))
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(
                    f"{label} top-level fields must match the code-owned schema",
                    report["errors"],
                )
                if relative == "product/acceptance.json":
                    self.reset_acceptance_fixture()
                else:
                    shutil.copy2(ROOT / relative, self.root / relative)

    def test_planning_active_limits_must_be_literal_integer_one(self) -> None:
        def boolean_limits(value: dict) -> None:
            value["planningModel"]["maxActiveIncrements"] = True
            value["planningModel"]["maxActiveWorkItems"] = True

        self.mutate("product/constitution.json", boolean_limits)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution planningModel is invalid", report["errors"])

    def test_work_state_semantics_cannot_self_disable(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value["planningModel"]["workStateSemantics"].__setitem__(
                "cancelled", "may have executed"
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution planningModel is invalid", report["errors"])

    def test_planning_model_cannot_disable_causality_or_add_workflow(self) -> None:
        variants = (
            (
                "remove causal prerequisites",
                lambda value: value["planningModel"].__setitem__(
                    "incrementRequires", ["none"]
                ),
            ),
            (
                "disable replanning",
                lambda value: value["planningModel"].__setitem__(
                    "replanWhen", ["never"]
                ),
            ),
            (
                "inject workflow",
                lambda value: value["planningModel"].__setitem__(
                    "mandatoryWorkflow", "plan-worktree-review"
                ),
            ),
        )
        for label, mutate_planning_model in variants:
            with self.subTest(label=label):
                self.mutate("product/constitution.json", mutate_planning_model)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(
                    "constitution planningModel is invalid", report["errors"]
                )
                shutil.copy2(
                    ROOT / "product/constitution.json",
                    self.root / "product/constitution.json",
                )

    def test_collaboration_model_cannot_add_user_or_process_burden(self) -> None:
        def inject_workflow(value: dict) -> None:
            model = value["collaborationModel"]
            model["userContributions"].append("skill-and-workflow-selection")
            model["agentObligations"].append("mandatory-external-methodology")
            model["requiredWorkflow"] = "brainstorm-plan-worktree-subagents-review"

        self.mutate("product/constitution.json", inject_workflow)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution collaborationModel is invalid", report["errors"])

    def test_product_form_cannot_collapse_into_a_catalog_or_host_product(self) -> None:
        variants = (
            ("identity", "codex-skill-catalog"),
            ("durableOutputs", ["host-plugin"]),
            ("portableCore", "fixed-plugin-list"),
            ("referenceDelivery", "codex-only-runtime"),
        )
        for field, replacement in variants:
            with self.subTest(field=field):
                self.mutate(
                    "product/constitution.json",
                    lambda value: value["productForm"].__setitem__(
                        field, replacement
                    ),
                )
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn("constitution productForm is invalid", report["errors"])
                shutil.copy2(
                    ROOT / "product/constitution.json",
                    self.root / "product/constitution.json",
                )

    def test_product_form_and_o5_keep_delivery_shape_and_os_claims_bounded(
        self,
    ) -> None:
        constitution = self.read_json("product/constitution.json")
        acceptance = self.read_json("product/acceptance.json")
        product_form = constitution["productForm"]
        durable_outputs = product_form["durableOutputs"]

        self.assertEqual(product_form, control.EXPECTED_PRODUCT_FORM)
        self.assertEqual(
            durable_outputs,
            [
                "portable-demand-to-outcome-collaboration-semantics",
                "open-minimum-quality-evidence-and-conformance-contract",
                "adaptive-thin-reference-projections",
            ],
        )
        for delivery_shape in (
            "methodology",
            "cli",
            "skill",
            "plugin",
            "mcp",
            "adapter",
            "service",
        ):
            self.assertNotIn(delivery_shape, durable_outputs)
        self.assertIn(
            "delivery-form-and-operating-system-neutral",
            product_form["portableCore"],
        )
        self.assertIn(
            "delivery form and projection shape", constitution["adaptiveSurfaces"]
        )
        self.assertIn(
            "operating-system-specific adapter and evidence mechanism",
            constitution["adaptiveSurfaces"],
        )

        o5 = next(item for item in acceptance["criteria"] if item["id"] == "O5")
        operationalization = o5["operationalization"]
        self.assertEqual(
            operationalization["comparisonDesign"],
            "clean-release-reproduction-and-bounded-portability",
        )
        self.assertIn("clean Windows checkout", o5["threshold"])
        self.assertIn("Windows-hosted WSL Linux checkout", o5["threshold"])
        self.assertIn("hosted macOS CI", o5["threshold"])
        self.assertIn("exact tested host", o5["threshold"])
        self.assertIn("distinct-Agent equivalence", o5["threshold"])
        self.assertIn(
            "environmentAndOperatingSystemIdentity",
            operationalization["preRegistrationFields"],
        )
        self.assertIn(
            "WindowsWslAndHostedMacEvidenceSeparation",
            operationalization["requiredMeasures"],
        )
        self.assertIn(
            "exactLiveCodexScope",
            operationalization["requiredMeasures"],
        )
        self.assertIn("public non-private contract checks", o5["threshold"])
        self.assertIn("named-human authorization", o5["operationalization"]["passRule"])
        self.assertIn("hosted macOS as CI-only", o5["operationalization"]["passRule"])

        environment_digest = hashlib.sha256(
            json.dumps(
                acceptance["environmentAttribution"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            environment_digest, control.EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
        )

    def test_fixed_invariants_and_bootstrap_guards_cannot_self_disable(self) -> None:
        variants = (
            (
                "fixedInvariants",
                ["tests and artifact counts are product outcomes"],
                "constitution fixedInvariants are invalid",
            ),
            (
                "bootstrapGuards",
                ["self-declaration is sufficient evidence"],
                "constitution bootstrapGuards are invalid",
            ),
            (
                "adaptiveSurfaces",
                ["fixed capability catalog"],
                "constitution adaptiveSurfaces are invalid",
            ),
        )
        for field, replacement, expected_error in variants:
            with self.subTest(field=field):
                self.mutate(
                    "product/constitution.json",
                    lambda value: value.__setitem__(field, replacement),
                )
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(expected_error, report["errors"])
                shutil.copy2(
                    ROOT / "product/constitution.json",
                    self.root / "product/constitution.json",
                )

    def test_frozen_v02_profile_artifacts_are_bound_to_historical_revision(self) -> None:
        errors: list[str] = []
        self.assertEqual(
            control.FROZEN_V02_PROFILE_ARTIFACT_REVISION,
            "0dbcb0af34197e5c35c75d69a1aeacf4fd91b404",
        )
        self.assertTrue(
            control._frozen_v02_profile_artifacts_valid(ROOT, errors), errors
        )
        relative = "docs/DEMAND-TO-CAPABILITY-PROFILE.md"
        with patch.object(control, "_committed_blob", return_value=False):
            errors = []
            self.assertFalse(
                control._frozen_v02_profile_artifacts_valid(ROOT, errors)
            )
        self.assertIn(
            "frozen v0.2 historical profile artifact is unavailable or changed: "
            + relative,
            errors,
        )

    def test_code_owned_policy_booleans_cannot_be_replaced_by_integers(self) -> None:
        variants = (
            (
                "product/program.json",
                lambda value: value["progressionPolicy"].__setitem__(
                    "userMustNotInventTasks", 1
                ),
                "program progressionPolicy is invalid",
            ),
            (
                "product/constitution.json",
                lambda value: value["historicalEvidenceBoundary"].__setitem__(
                    "productAuthority", 0
                ),
                "constitution historicalEvidenceBoundary is invalid",
            ),
        )
        for relative, mutation, expected_error in variants:
            with self.subTest(relative=relative):
                self.mutate(relative, mutation)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(expected_error, report["errors"])
                shutil.copy2(ROOT / relative, self.root / relative)

    def test_acceptance_release_must_match_program(self) -> None:
        self.mutate(
            "product/acceptance.json",
            lambda value: value.__setitem__("release", "v9.9"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program and acceptance releases must match", report["errors"])

    def test_completion_expression_cannot_drift(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("completionExpression", "O1"),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn("program completionExpression is invalid", report["errors"])

    def test_product_purpose_and_progress_semantics_cannot_self_downgrade(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value.update(
                {
                    "purpose": "Maximize plans, inventories, and process artifacts.",
                    "successDefinition": "Success means all local tests are green.",
                }
            ),
        )
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__(
                "purpose", "Produce governance files without real outcomes."
            ),
        )
        self.mutate(
            "product/acceptance.json",
            lambda value: value.__setitem__(
                "progressRule", "Every passing test counts as product progress."
            ),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution purpose is invalid", report["errors"])
        self.assertIn("constitution successDefinition is invalid", report["errors"])
        self.assertIn("program purpose is invalid", report["errors"])
        self.assertIn("acceptance progressRule is invalid", report["errors"])

    def test_criteria_must_be_exact_and_unique(self) -> None:
        def duplicate(value: dict) -> None:
            value["criteria"].append(deepcopy(value["criteria"][0]))

        self.mutate("product/acceptance.json", duplicate)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn("duplicate acceptance criterion O1", report["errors"])

    def test_criteria_reject_undeclared_self_promotion_fields(self) -> None:
        variants = (
            ("O1", {"accepted": True, "verified": True}),
            ("G1", {"passed": True}),
        )
        for criterion_id, additions in variants:
            with self.subTest(criterion_id=criterion_id):
                def self_promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == criterion_id
                    )
                    criterion.update(additions)

                self.mutate("product/acceptance.json", self_promote)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G2"])
                self.assertIn(
                    f"criterion {criterion_id} fields must match the code-owned schema",
                    report["errors"],
                )
                self.reset_acceptance_fixture()

    def test_malformed_criterion_id_fails_without_traceback(self) -> None:
        def malformed(value: dict) -> None:
            value["criteria"][1]["id"] = []

        self.mutate("product/acceptance.json", malformed)
        completed = self.run_cli()
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertFalse(report["valid"])

    def test_outcomes_require_exact_operationalization_fields(self) -> None:
        def remove(value: dict) -> None:
            value["criteria"][0]["operationalization"].pop("passRule")

        self.mutate("product/acceptance.json", remove)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "criterion O1 requires the exact operationalization fields",
            report["errors"],
        )

    def test_release_criteria_semantics_cannot_self_downgrade(self) -> None:
        def self_accept(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["threshold"] = "Agent self-declaration is sufficient."
            criterion["operationalization"]["passRule"] = "The Agent declares success."
            criterion["operationalization"]["falsifiers"] = ["none"]
            criterion["operationalization"]["humanAuthority"] = (
                "The Agent owns acceptance."
            )

        self.mutate("product/acceptance.json", self_accept)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "acceptance criteria contract identity is invalid",
            report["errors"],
        )

    def test_outcome_sample_floor_and_comparison_design_are_code_owned(self) -> None:
        def dilute(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O2")
            criterion["operationalization"]["minimumSampleCount"] = 2

        self.mutate("product/acceptance.json", dilute)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "criterion O2 minimumSampleCount must be at least 4",
            report["errors"],
        )

        self.reset_acceptance_fixture()

        def change_design(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O5")
            criterion["operationalization"]["comparisonDesign"] = "unrelated-host-tasks"

        self.mutate("product/acceptance.json", change_design)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("criterion O5 comparisonDesign is invalid", report["errors"])

    def test_outcome_operationalization_lists_are_typed_and_unique(self) -> None:
        def duplicate(value: dict) -> None:
            fields = value["criteria"][0]["operationalization"]["requiredMeasures"]
            fields.append(fields[0])

        self.mutate("product/acceptance.json", duplicate)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "criterion O1 operationalization requiredMeasures is invalid",
            report["errors"],
        )

    def test_guardrails_cannot_self_declare_outcome_operationalization(self) -> None:
        def add(value: dict) -> None:
            guardrail = next(item for item in value["criteria"] if item["id"] == "G1")
            guardrail["operationalization"] = deepcopy(
                value["criteria"][0]["operationalization"]
            )

        self.mutate("product/acceptance.json", add)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "guardrail G1 cannot declare operationalization",
            report["errors"],
        )

    def test_active_program_requires_exactly_one_active_increment(self) -> None:
        def close(value: dict) -> None:
            increment = self.activate_program(value)
            increment["state"] = "planned"

        self.mutate("product/program.json", close)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("active program must have exactly one active increment", report["errors"])

    def test_clean_active_fixture_is_valid(self) -> None:
        self.mutate("product/program.json", self.activate_program)
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])

    def test_outcome_increment_can_observe_source_before_validator_implementation(self) -> None:
        def activate_o2(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O2")
            increment["workItems"][0]["acceptanceIds"].append("O2")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o2)
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["criterionStates"]["G4"])
        self.assertFalse(report["criterionStates"]["O2"])

    def test_outcome_increment_requires_content_addressed_task_registration(
        self,
    ) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.freeze_program_profile(value)

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "outcome-bearing increment increment.fixture-current requires an exact "
            "taskRegistration binding",
            report["errors"],
        )

    def test_outcome_registration_is_forbidden_until_profile_freeze(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "outcome-bearing increment increment.fixture-current requires a frozen normative profile",
            report["errors"],
        )

    def test_task_registration_rejects_noncanonical_task_identity(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(
                value,
                increment,
                task_identity="natural-task.sha256:" + "a" * 64,
            )

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "task registration product/evidence/fixture-registration.json shape is invalid",
            report["errors"],
        )

    def test_task_registration_binds_execution_after_immutable_registration(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        registration["scenarioEvidenceAndStopRule"][
            "executionStartsAfter"
        ] = "post-result favorable registration"
        self.write_json(relative, registration)
        self.recommit_fixture_registration(program)
        self.write_json("product/program.json", program)

        report = self.report()

        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(f"task registration {relative} shape is invalid", report["errors"])

    def test_current_registration_rejects_natural_task_identity(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(
                value,
                increment,
                task_identity="natural-task.public-v1:" + "a" * 32,
            )

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "task registration product/evidence/fixture-registration.json shape is invalid",
            report["errors"],
        )

    def test_task_registration_rejects_unrecognized_evidence_class(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        registration["scenarioEvidenceAndStopRule"]["evidenceClass"] = (
            "favorable-post-hoc-scenario"
        )
        self.write_json(relative, registration)
        self.recommit_fixture_registration(program)
        self.write_json("product/program.json", program)

        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(f"task registration {relative} shape is invalid", report["errors"])

    def test_task_registration_profile_or_cohort_protocol_drift_fails_closed(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        registration["preRegistrationValues"]["cohortProtocolIdentity"] = (
            "cohort-protocol.drift"
        )
        self.write_json(relative, registration)
        self.recommit_fixture_registration(program)
        self.write_json("product/program.json", program)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(f"task registration {relative} shape is invalid", report["errors"])

    def test_registration_revision_must_strictly_descend_from_profile_freeze(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)
            value["normativeProfileBinding"]["frozenAtRevision"] = increment[
                "taskRegistration"
            ]["sourceRevision"]

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current taskRegistration must strictly descend from the frozen profile and cohort protocol",
            report["errors"],
        )

    def test_registration_revision_must_be_in_canonical_head_history(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        side_revision = program["increments"][0]["taskRegistration"][
            "sourceRevision"
        ]
        canonical_revision = subprocess.run(
            ["git", "rev-parse", f"{side_revision}^"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "restore", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "switch", "--quiet", "--detach", canonical_revision],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.write_json(relative, registration)
        self.write_json("product/program.json", program)

        report = self.report()

        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current taskRegistration identity or frozen-profile binding mismatch",
            report["errors"],
        )

    def test_registration_parent_must_already_contain_frozen_binding(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(
                value,
                increment,
                commit_profile_binding=False,
            )
            self.write_json("product/program.json", value)
            subprocess.run(
                ["git", "add", "product/program.json"],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                [
                    "git",
                    "commit",
                    "--quiet",
                    "-m",
                    "retrospectively freeze fixture profile binding",
                ],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current taskRegistration must have one parent containing the exact frozen normative profile binding",
            report["errors"],
        )

    def test_registration_merge_commit_cannot_supply_ambiguous_freeze_parent(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        manifest_revision = registration["preRegistrationValues"][
            "environmentAttributionBinding"
        ]["manifestRevision"]
        subprocess.run(
            ["git", "restore", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "switch",
                "--quiet",
                "-c",
                "fixture-merge-parent",
                manifest_revision,
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        marker = self.root / "docs/FIXTURE-MERGE-PARENT.md"
        marker.write_text("fixture merge parent\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "docs/FIXTURE-MERGE-PARENT.md"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "fixture merge parent"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "switch",
                "--quiet",
                "-c",
                "fixture-merge-base",
                manifest_revision,
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "merge",
                "--quiet",
                "--no-ff",
                "--no-commit",
                "fixture-merge-parent",
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.write_json(relative, registration)
        subprocess.run(
            ["git", "add", relative],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "ambiguous registration merge"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        source_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        committed_registration = subprocess.run(
            ["git", "show", f"{source_revision}:{relative}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        binding = program["increments"][0]["taskRegistration"]
        binding["sourceRevision"] = source_revision
        binding["sha256"] = hashlib.sha256(committed_registration).hexdigest()
        self.write_json("product/program.json", program)

        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current taskRegistration must have one parent containing the exact frozen normative profile binding",
            report["errors"],
        )

    def test_registration_chronology_does_not_trust_git_commit_dates(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        original = control._evidence_git

        def reject_commit_date_reads(
            root: Path, *args: str, **kwargs: object
        ) -> bytes | None:
            self.assertNotIn("--format=%cI", args)
            self.assertNotIn("--format=%aI", args)
            return original(root, *args, **kwargs)

        with patch("harness.control._evidence_git", side_effect=reject_commit_date_reads):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])

    def test_frozen_profile_binding_cannot_return_to_unfrozen(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        program["normativeProfileBinding"] = deepcopy(
            control.UNFROZEN_NORMATIVE_PROFILE_BINDING
        )
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "reset frozen profile"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        report = self.report()

        self.assertFalse(report["valid"])
        self.assertIn(
            "frozen normative profile binding cannot return to unfrozen",
            report["errors"],
        )

    def test_revoked_profile_preserves_first_freeze_and_rejects_same_activation(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        program["normativeProfileBinding"]["state"] = "revoked"
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "revoke fixture cohort"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        with patch(
            "harness.control._initial_authorization_private_resource_absent",
            return_value=True,
        ), patch(
            "harness.control._successor_authorization_private_resource_absent",
            return_value=True,
        ):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])

        program["normativeProfileBinding"]["state"] = "frozen"
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "reactivate fixture cohort"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "successor cohort generation violates its single zero-outcome boundary",
            report["errors"],
        )

    def test_revoked_zero_outcome_profile_can_start_one_successor_cohort(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(program)

        report = self.report(bind_successor=False)
        self.assertFalse(report["valid"])
        self.assertIn(
            "successor cohort binding is not code-pinned to canonical history",
            report["errors"],
        )

        report = self.report()
        self.assertTrue(report["valid"], report["errors"])

    def test_successor_cohort_rejects_any_prior_registration(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        program["increments"] = [{"taskRegistration": {"fixture": "prior"}}]
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "record fixture registration"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        program["increments"] = []
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(program)

        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "successor cohort generation violates its single zero-outcome boundary",
            report["errors"],
        )

    def test_successor_cohort_rejects_reused_private_key_identity(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(
            program,
            reuse_activation_fields=("keyIdentity", "keyFingerprint"),
        )

        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "successor cohort generation violates its single zero-outcome boundary",
            report["errors"],
        )

    def test_successor_cohort_rejects_reused_surface_identity(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(
            program,
            reuse_activation_fields=("surfaceIdentity",),
        )

        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "successor cohort generation violates its single zero-outcome boundary",
            report["errors"],
        )

    def test_successor_cohort_rejects_reused_activation_cursor(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(
            program,
            reuse_activation_fields=("activationCursorCommitment",),
        )

        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "successor cohort generation violates its single zero-outcome boundary",
            report["errors"],
        )

    def test_active_successor_requires_predecessor_private_resource_absence(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(program)

        def predecessor_present(errors: list[str]) -> bool:
            errors.append("fixture predecessor resource still exists")
            return False

        with patch(
            "harness.control._initial_authorization_private_resource_absent",
            side_effect=predecessor_present,
        ) as predecessor_absent:
            report = self.report()

        self.assertFalse(report["valid"])
        predecessor_absent.assert_called_once()

    def test_revoked_successor_requires_its_private_resource_absence(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(program)
        self.revoke_program_profile(program, "revoke successor fixture cohort")

        def successor_present(errors: list[str]) -> bool:
            errors.append("fixture successor resource still exists")
            return False

        with patch(
            "harness.control._initial_authorization_private_resource_absent",
            return_value=True,
        ) as predecessor_absent, patch(
            "harness.control._successor_authorization_private_resource_absent",
            side_effect=successor_present,
            create=True,
        ) as successor_absent:
            report = self.report()

        self.assertFalse(report["valid"])
        predecessor_absent.assert_called_once()
        successor_absent.assert_called_once()

    def test_successor_cohort_generation_is_single_use(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.revoke_program_profile(program)
        self.start_successor_program_cohort(program)
        self.revoke_program_profile(program, "revoke restarted fixture cohort")
        self.start_successor_program_cohort(program)

        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "successor cohort generation violates its single zero-outcome boundary",
            report["errors"],
        )

    def test_frozen_profile_binding_cannot_move_history_floor(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        marker = self.root / "docs/FIXTURE-LATER-REVISION.md"
        marker.write_text("# Later fixture revision\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "docs/FIXTURE-LATER-REVISION.md"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "later fixture revision"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        later_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        program["normativeProfileBinding"]["frozenAtRevision"] = later_revision
        self.write_json("product/program.json", program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "move frozen history floor"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        report = self.report()

        self.assertFalse(report["valid"])
        self.assertIn(
            "frozen normative profile binding changed within a generation",
            report["errors"],
        )

    def test_normative_binding_fails_when_fixed_history_floor_is_unavailable(self) -> None:
        self.initialize_fixture_repository()
        with patch.multiple(
            control,
            CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION="f" * 40,
        ):
            report = verify_product(self.root)

        self.assertFalse(report["valid"])
        self.assertIn(
            "current normative profile binding history floor is unavailable",
            report["errors"],
        )

    def test_binding_history_cannot_hide_transition_behind_foreign_program_id(self) -> None:
        self.initialize_fixture_repository()
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        frozen = self.read_json("product/program.json")

        foreign = deepcopy(frozen)
        foreign["id"] = "foreign-program"
        foreign["normativeProfileBinding"]["state"] = "revoked"
        self.write_json("product/program.json", foreign)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "hide fixture revocation"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.write_json("product/program.json", frozen)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "restore fixture program id"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        report = self.report()

        self.assertFalse(report["valid"])
        self.assertIn(
            "v1 normative profile binding history is incomplete",
            report["errors"],
        )

    def test_uncommitted_first_freeze_fails_closed(self) -> None:
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program, commit_binding=False)
        self.write_json("product/program.json", program)

        report = self.report()

        self.assertFalse(report["valid"])
        self.assertIn(
            "frozen normative profile binding must exist in committed first-parent history",
            report["errors"],
        )

    def test_first_freeze_requires_independent_human_source_authorization(self) -> None:
        floor = self.initialize_fixture_repository()
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        freeze_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        binding_sha256 = hashlib.sha256(
            json.dumps(
                program["normativeProfileBinding"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=True,
            _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY=True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
            NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
            EXPECTED_V1_PROFILE_ARTIFACT_REVISION=floor,
            EXPECTED_V1_INITIAL_BINDING_REVISION=freeze_revision,
            EXPECTED_V1_INITIAL_BINDING_SHA256=binding_sha256,
            EXPECTED_V1_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID=None,
            SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS={},
        ):
            report = verify_product(self.root)

        self.assertFalse(report["valid"])
        self.assertIn(
            "initial frozen normative profile binding has no code-owned source authorization validator",
            report["errors"],
        )

    def test_binding_authorizer_cannot_clear_history_errors(self) -> None:
        floor = self.initialize_fixture_repository()
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        freeze_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        binding_sha256 = hashlib.sha256(
            json.dumps(
                program["normativeProfileBinding"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        replacement = self.read_json("product/program.json")
        replacement["normativeProfileBinding"]["cohortActivation"][
            "surfaceIdentity"
        ] = "enrollment-surface.public-v1:" + "9" * 32
        self.write_json("product/program.json", replacement)
        validator_called = False

        def malicious_authorizer(document, root, errors):
            nonlocal validator_called
            validator_called = True
            errors.clear()
            return True

        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=True,
            _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY=True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
            NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
            EXPECTED_V1_PROFILE_ARTIFACT_REVISION=floor,
            EXPECTED_V1_INITIAL_BINDING_REVISION=freeze_revision,
            EXPECTED_V1_INITIAL_BINDING_SHA256=binding_sha256,
            EXPECTED_V1_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID=(
                "fixture-malicious-binding-authorizer"
            ),
            SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS={
                "fixture-malicious-binding-authorizer": malicious_authorizer
            },
        ):
            report = verify_product(self.root)

        self.assertFalse(report["valid"])
        self.assertFalse(validator_called)
        self.assertIn(
            "current normative profile binding differs from its active generation",
            report["errors"],
        )

    def test_side_branch_freeze_cannot_poison_canonical_first_parent(self) -> None:
        self.initialize_fixture_repository()
        base_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "switch", "--quiet", "-c", "fixture-side-freeze"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        subprocess.run(
            ["git", "switch", "--quiet", base_branch],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "merge",
                "--quiet",
                "--no-ff",
                "-s",
                "ours",
                "fixture-side-freeze",
                "-m",
                "merge side freeze without adopting it",
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        report = self.report()

        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(
            self.read_json("product/program.json")["normativeProfileBinding"]["state"],
            "unfrozen",
        )

    def test_dropped_first_freeze_cannot_be_replaced_with_a_new_activation(self) -> None:
        floor = self.initialize_fixture_repository()
        base_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "switch", "--quiet", "-c", "fixture-first-freeze"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        first_program = self.read_json("product/program.json")
        self.freeze_program_profile(first_program)
        first_freeze_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        first_binding_sha256 = hashlib.sha256(
            json.dumps(
                first_program["normativeProfileBinding"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        subprocess.run(
            ["git", "switch", "--quiet", base_branch],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        replacement_program = self.read_json("product/program.json")
        self.freeze_program_profile(replacement_program, commit_binding=False)
        replacement_program["normativeProfileBinding"]["cohortActivation"][
            "surfaceIdentity"
        ] = "enrollment-surface.public-v1:" + "9" * 32
        self.write_json("product/program.json", replacement_program)
        subprocess.run(
            ["git", "add", "product/program.json"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "replacement freeze fixture"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=True,
            _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY=True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
            NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
            EXPECTED_V1_PROFILE_ARTIFACT_REVISION=floor,
            EXPECTED_V1_INITIAL_BINDING_REVISION=first_freeze_revision,
            EXPECTED_V1_INITIAL_BINDING_SHA256=first_binding_sha256,
            EXPECTED_V1_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID=(
                "fixture-initial-binding-authorization"
            ),
            SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS={
                "fixture-initial-binding-authorization": (
                    lambda document, root, errors: document.get("revision")
                    == first_freeze_revision
                    and document.get("bindingSha256") == first_binding_sha256
                )
            },
        ):
            report = verify_product(self.root)

        self.assertFalse(report["valid"])
        self.assertIn(
            "initial frozen normative profile binding is not code-pinned to canonical history",
            report["errors"],
        )

    def test_normative_binding_history_has_a_finite_revision_bound(self) -> None:
        self.initialize_fixture_repository()
        for index in range(3):
            program_path = self.root / "product/program.json"
            program_path.write_text(
                program_path.read_text(encoding="utf-8").rstrip()
                + (" " * (index + 1))
                + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "product/program.json"],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "commit", "--quiet", "-m", f"fixture program format {index}"],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        floor = subprocess.run(
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        with patch.multiple(
            control,
            CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION=floor,
            MAX_NORMATIVE_BINDING_HISTORY_REVISIONS=2,
        ):
            report = verify_product(self.root)

        self.assertFalse(report["valid"])
        self.assertIn(
            "current normative profile binding history exceeds its inspection bound",
            report["errors"],
        )

    def test_frozen_cohort_protocol_bytes_are_content_addressed(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        protocol = self.read_json("docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json")
        protocol["stopRule"] = "post-selected favorable tasks only"
        self.write_json("docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json", protocol)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "frozen cohort protocol identity or source revision mismatch",
            report["errors"],
        )

    def test_initially_committed_postselection_protocol_is_rejected(self) -> None:
        self.initialize_fixture_repository()
        protocol_locator = "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json"
        protocol = self.read_json(protocol_locator)
        protocol["stopRule"] = "post-selected favorable tasks only"
        self.write_json(protocol_locator, protocol)
        subprocess.run(
            ["git", "add", protocol_locator],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "malicious cohort protocol"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        profile_locator = "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md"
        profile_blob = subprocess.run(
            ["git", "show", f"{revision}:{profile_locator}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        protocol_blob = subprocess.run(
            ["git", "show", f"{revision}:{protocol_locator}"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        program = self.read_json("product/program.json")
        program["normativeProfileBinding"] = {
            "state": "frozen",
            "profileIdentity": control.EXPECTED_V1_PROFILE_IDENTITY,
            "locator": profile_locator,
            "sha256": hashlib.sha256(profile_blob).hexdigest(),
            "cohortProtocolIdentity": control.EXPECTED_V1_COHORT_PROTOCOL_IDENTITY,
            "cohortProtocolLocator": protocol_locator,
            "cohortProtocolSha256": hashlib.sha256(protocol_blob).hexdigest(),
            "frozenAtRevision": revision,
            "cohortActivation": {
                "surfaceIdentity": "enrollment-surface.public-v1:" + "1" * 32,
                "activationCursorCommitment": "hmac-sha256:" + "2" * 64,
                "keyIdentity": "cohort-key.public-v1:" + "3" * 32,
                "keyFingerprint": "sha256:" + "4" * 64,
                "sourceMessageRule": control.EXPECTED_SOURCE_MESSAGE_RULE,
                "hmacDomain": control.EXPECTED_HMAC_DOMAIN,
                "surfaceTransitionRule": control.EXPECTED_SURFACE_TRANSITION_RULE,
                "keyRetentionRule": control.EXPECTED_KEY_RETENTION_RULE,
            },
        }
        self.write_json("product/program.json", program)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "frozen normative profile binding is not the code-owned v1 candidate",
            report["errors"],
        )

    def test_initially_committed_flexible_scenario_strata_are_rejected(self) -> None:
        self.initialize_fixture_repository(protocol_strata=["favorable-fixture-stratum"])
        program = self.read_json("product/program.json")
        self.freeze_program_profile(program)
        self.write_json("product/program.json", program)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "code-owned v1 candidate artifact identity changed: "
            "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json",
            report["errors"],
        )

    def test_duplicate_task_identity_across_outcome_increments_fails_closed(
        self,
    ) -> None:
        def activate_two(value: dict) -> None:
            first = self.ensure_increment(value, state="completed")
            first["acceptanceIds"].append("O1")
            first["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, first)
            second = deepcopy(first)
            second["id"] = "increment.fixture-second"
            second["state"] = "active"
            second["correctionClass"] = "fixture-second-correction"
            second["workItems"][0]["id"] = "work.fixture-second"
            second["workItems"][0]["state"] = "active"
            value["increments"].append(second)
            value["status"] = "active"
            value["activeIncrementId"] = second["id"]
            self.bind_fixture_registration(
                value,
                second,
                task_identity=fixture_task_identity("fixture-current"),
                registration_id="registration.fixture-second",
                relative="product/evidence/fixture-second-registration.json",
            )

        self.mutate("product/program.json", activate_two)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            f"taskIdentity {fixture_task_identity('fixture-current')} is reused across outcome registrations",
            report["errors"],
        )

    def test_postfreeze_registration_cannot_be_orphaned_or_deleted(self) -> None:
        first_path = "product/evidence/fixture-registration.json"

        def omit_first(value: dict) -> None:
            first = self.ensure_increment(value, state="completed")
            first["acceptanceIds"].append("O1")
            first["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(
                value,
                first,
                task_identity=fixture_task_identity("fixture-first"),
            )
            second = deepcopy(first)
            second["id"] = "increment.fixture-second"
            second["state"] = "active"
            second["correctionClass"] = "fixture-second-correction"
            second["workItems"][0]["id"] = "work.fixture-second"
            second["workItems"][0]["state"] = "active"
            self.bind_fixture_registration(
                value,
                second,
                task_identity=fixture_task_identity("fixture-second"),
                registration_id="registration.fixture-second",
                relative="product/evidence/fixture-second-registration.json",
            )
            value["increments"] = [second]
            value["status"] = "active"
            value["activeIncrementId"] = second["id"]

        self.mutate("product/program.json", omit_first)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "every post-freeze conformance registration artifact must bind exactly one outcome increment",
            report["errors"],
        )

        (self.root / first_path).unlink()
        subprocess.run(
            ["git", "add", first_path],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "delete unfavorable registration"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "cohort registration artifacts are append-only and cannot be deleted, renamed or copied",
            report["errors"],
        )

    def test_task_registration_rejects_drift_or_missing_criterion_fields(self) -> None:
        def activate_o5(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].extend(["O1", "O5"])
            increment["workItems"][0]["acceptanceIds"].extend(["O1", "O5"])
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o5)
        baseline = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"

        registration = self.read_json(relative)
        registration["preRegistrationValues"].pop("normativeProfileIdentity")
        self.write_json(relative, registration)
        self.recommit_fixture_registration(baseline)
        self.write_json("product/program.json", baseline)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            f"task registration {relative} shape is invalid",
            report["errors"],
        )

        self.bind_fixture_registration(baseline, baseline["increments"][0])
        self.write_json("product/program.json", baseline)
        registration = self.read_json(relative)
        registration["claimLimits"].append("unbound post-registration drift")
        self.write_json(relative, registration)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current taskRegistration identity or frozen-profile binding mismatch",
            report["errors"],
        )

    def test_task_registration_binds_current_acceptance_contract(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        registration["acceptanceAuthority"]["criteriaContractSha256"] = "0" * 64
        self.write_json(relative, registration)
        self.recommit_fixture_registration(program)
        self.write_json("product/program.json", program)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            f"task registration {relative} shape is invalid",
            report["errors"],
        )

    def test_task_registration_locator_is_canonical_and_non_nested(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)
            increment["taskRegistration"]["locator"] = (
                "product/evidence/nested/fixture-registration.json"
            )

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current has invalid taskRegistration locator",
            report["errors"],
        )

    def test_outcome_neutral_increment_rejects_registration_binding(self) -> None:
        def bind(value: dict) -> None:
            increment = self.activate_program(value)
            increment["taskRegistration"] = {
                "locator": "product/evidence/fixture-registration.json",
                "sha256": "0" * 64,
            }

        self.mutate("product/program.json", bind)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "outcome-neutral increment increment.fixture-current must bind null "
            "taskRegistration",
            report["errors"],
        )

    def test_current_release_has_only_the_pre_measurement_o1_and_o2_validators(self) -> None:
        o1_expected_prefix = (
            frozenset({"O1"}),
            frozenset({O1_LIFECYCLE_INCREMENT_ID}),
            O1_LIFECYCLE_VALIDATOR_LOCATOR,
        )
        o2_expected_prefix = (
            frozenset({"O2"}),
            frozenset({O2_CODEX_INCREMENT_ID}),
            O2_CODEX_VALIDATOR_LOCATOR,
        )
        self.assertEqual(
            set(SUPPORTED_EVIDENCE_VALIDATORS),
            {O1_LIFECYCLE_VALIDATOR_KIND, O2_CODEX_VALIDATOR_KIND},
        )
        self.assertEqual(
            set(SUPPORTED_PRE_MEASUREMENT_VALIDATORS),
            {O1_LIFECYCLE_VALIDATOR_KIND, O2_CODEX_VALIDATOR_KIND},
        )
        self.assertEqual(
            SUPPORTED_EVIDENCE_VALIDATORS[O1_LIFECYCLE_VALIDATOR_KIND][:-1],
            o1_expected_prefix,
        )
        self.assertIs(
            SUPPORTED_EVIDENCE_VALIDATORS[O1_LIFECYCLE_VALIDATOR_KIND][-1],
            validate_o1_lifecycle_evidence,
        )
        self.assertEqual(
            SUPPORTED_PRE_MEASUREMENT_VALIDATORS[O1_LIFECYCLE_VALIDATOR_KIND][:-1],
            o1_expected_prefix,
        )
        self.assertIs(
            SUPPORTED_PRE_MEASUREMENT_VALIDATORS[O1_LIFECYCLE_VALIDATOR_KIND][-1],
            validate_o1_lifecycle_registration,
        )
        self.assertEqual(
            SUPPORTED_EVIDENCE_VALIDATORS[O2_CODEX_VALIDATOR_KIND][:-1],
            o2_expected_prefix,
        )
        self.assertIs(
            SUPPORTED_EVIDENCE_VALIDATORS[O2_CODEX_VALIDATOR_KIND][-1],
            validate_o2_codex_evidence,
        )
        self.assertEqual(
            SUPPORTED_PRE_MEASUREMENT_VALIDATORS[O2_CODEX_VALIDATOR_KIND][:-1],
            o2_expected_prefix,
        )
        self.assertIs(
            SUPPORTED_PRE_MEASUREMENT_VALIDATORS[O2_CODEX_VALIDATOR_KIND][-1],
            validate_o2_codex_registration,
        )

    def test_outcome_registration_requires_code_owned_pre_measurement_validator(
        self,
    ) -> None:
        def register(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", register)
        report = self.report(auto_bind_task_validators=False)
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current has no code-owned "
            "pre-measurement validator: test-validator",
            report["errors"],
        )

    def test_program_cannot_post_bind_a_different_pre_measurement_validator(
        self,
    ) -> None:
        def register(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", register)
        program = self.read_json("product/program.json")
        program["increments"][0]["taskRegistration"]["preMeasurementValidator"][
            "kind"
        ] = "late-validator"
        self.write_json("product/program.json", program)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "task registration product/evidence/fixture-registration.json shape is invalid",
            report["errors"],
        )

    def test_pre_measurement_validator_must_precede_registration_and_not_drift(
        self,
    ) -> None:
        def register(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", register)
        baseline = self.read_json("product/program.json")
        binding = baseline["increments"][0]["taskRegistration"]
        registration = self.read_json(binding["locator"])
        registration["preMeasurementValidator"]["revision"] = "0" * 40
        binding["preMeasurementValidator"] = deepcopy(
            registration["preMeasurementValidator"]
        )
        self.write_json(binding["locator"], registration)
        self.recommit_fixture_registration(baseline)
        self.write_json("product/program.json", baseline)
        late = self.report()
        self.assertFalse(late["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current pre-measurement validator must be "
            "committed before task registration",
            late["errors"],
        )

        validator_revision = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%H",
                "--",
                binding["preMeasurementValidator"]["locator"],
            ],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        registration = self.read_json(binding["locator"])
        registration["preMeasurementValidator"]["revision"] = validator_revision
        binding["preMeasurementValidator"] = deepcopy(
            registration["preMeasurementValidator"]
        )
        self.write_json(binding["locator"], registration)
        self.recommit_fixture_registration(baseline)
        self.write_json("product/program.json", baseline)
        validator_path = self.root / binding["preMeasurementValidator"]["locator"]
        validator_path.write_text("def drifted():\n    return False\n", encoding="utf-8")
        drifted = self.report()
        self.assertFalse(drifted["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current pre-measurement validator code "
            "identity has drifted",
            drifted["errors"],
        )

    def test_pre_measurement_validator_fails_closed_and_cannot_clear_core_errors(
        self,
    ) -> None:
        def register(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", register)
        program = self.read_json("product/program.json")
        validator_binding = program["increments"][0]["taskRegistration"][
            "preMeasurementValidator"
        ]
        spec_prefix = (
            frozenset({"O1"}),
            frozenset({FIXTURE_INCREMENT_ID}),
            validator_binding["locator"],
        )
        with patch(
            "harness.control.SUPPORTED_PRE_MEASUREMENT_VALIDATORS",
            {"test-validator": (*spec_prefix, lambda *args: False)},
        ):
            rejected = self.report()
        self.assertFalse(rejected["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current pre-measurement validator did not "
            "return true: test-validator",
            rejected["errors"],
        )

        called = False

        def malicious(*args: object) -> bool:
            nonlocal called
            called = True
            errors = args[-1]
            assert isinstance(errors, list)
            errors.clear()
            return True

        program["increments"][0]["taskRegistration"]["preMeasurementValidator"][
            "locator"
        ] = "harness/not_task_validator.py"
        registration_locator = program["increments"][0]["taskRegistration"]["locator"]
        registration = self.read_json(registration_locator)
        registration["preMeasurementValidator"][
            "locator"
        ] = "harness/not_task_validator.py"
        self.write_json(registration_locator, registration)
        self.recommit_fixture_registration(program)
        self.write_json("product/program.json", program)
        with patch(
            "harness.control.SUPPORTED_PRE_MEASUREMENT_VALIDATORS",
            {"test-validator": (*spec_prefix, malicious)},
        ):
            invalid = self.report()
        self.assertFalse(invalid["criterionStates"]["G4"])
        self.assertFalse(called)
        self.assertIn(
            "increment increment.fixture-current preMeasurementValidator identity is invalid",
            invalid["errors"],
        )

    def test_evidence_must_reuse_registered_pre_measurement_validator_identity(
        self,
    ) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(
            criterion_ids=["O1"], validator_kind="different-validator"
        )
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            {
                "different-validator": (
                    frozenset({"O1"}),
                    frozenset({FIXTURE_INCREMENT_ID}),
                    "harness/task_validator_fixture.py",
                    lambda document, criterion_id, root, errors: True,
                )
            },
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "criterion O1 evidence validator does not reuse the pre-measurement "
            "validator bound to increment increment.fixture-current",
            report["errors"],
        )

    def test_evidence_validator_cannot_clear_core_verifier_errors(self) -> None:
        self.map_outcome_to_latest_work("O1")
        self.write_json(
            "product/evidence/bound.json",
            self.evidence_document(criterion_ids=["O1"]),
        )

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        self.mutate(
            "product/program.json",
            lambda value: value["progressionPolicy"].__setitem__(
                "readyState", "invalid-fixture-value"
            ),
        )
        called = False

        def malicious(document, criterion_id, root, errors) -> bool:
            nonlocal called
            called = True
            errors.clear()
            return True

        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(malicious),
        ):
            report = self.report()
        self.assertTrue(called)
        self.assertFalse(report["valid"])
        self.assertIn("program progressionPolicy is invalid", report["errors"])

    def test_active_increment_id_must_match(self) -> None:
        def mismatch(value: dict) -> None:
            self.activate_program(value)
            value["activeIncrementId"] = "increment.missing"

        self.mutate("product/program.json", mismatch)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("activeIncrementId must identify the active increment", report["errors"])

    def test_only_one_work_item_may_be_active(self) -> None:
        def duplicate_work(value: dict) -> None:
            increment = self.activate_program(value)
            other = deepcopy(increment["workItems"][0])
            other["id"] = "work.second"
            increment["workItems"].append(other)

        self.mutate("product/program.json", duplicate_work)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.fixture-current has more than one active work item",
            report["errors"],
        )

    def test_active_program_cannot_queue_planned_increment(self) -> None:
        def queue(value: dict) -> None:
            self.activate_program(value)
            planned = self.increment_fixture()
            planned["id"] = "increment.queued"
            planned["correctionClass"] = "queued-correction"
            planned["workItems"][0]["id"] = "work.queued"
            value["increments"].append(planned)

        self.mutate("product/program.json", queue)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "current program cannot queue planned increment increment.queued",
            report["errors"],
        )

    def test_active_increment_cannot_queue_planned_work_item(self) -> None:
        def queue(value: dict) -> None:
            increment = self.activate_program(value)
            planned = deepcopy(increment["workItems"][0])
            planned["id"] = "work.queued"
            planned["state"] = "planned"
            increment["workItems"].append(planned)

        self.mutate("product/program.json", queue)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "current increment cannot queue planned work item work.queued",
            report["errors"],
        )

    def test_active_increment_requires_exactly_one_active_work_item(self) -> None:
        def stall(value: dict) -> None:
            increment = self.activate_program(value)
            increment["workItems"][0]["state"] = "stopped"

        self.mutate("product/program.json", stall)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "active increment increment.fixture-current must have exactly one active work item",
            report["errors"],
        )

    def test_increment_requires_a_correction_class(self) -> None:
        def remove(value: dict) -> None:
            self.activate_program(value).pop("correctionClass")

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.fixture-current requires a correctionClass",
            report["errors"],
        )

    def test_work_acceptance_must_be_contained_by_increment(self) -> None:
        def exceed(value: dict) -> None:
            increment = self.activate_program(value)
            increment["workItems"][0]["acceptanceIds"].append("G1")

        self.mutate("product/program.json", exceed)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "work item work.fixture-current "
            "acceptanceIds exceed increment "
            "increment.fixture-current",
            report["errors"],
        )

    def test_program_graph_rejects_capability_added_requirements(self) -> None:
        variants = (
            (
                "increment workflow",
                lambda increment: increment.__setitem__(
                    "mandatoryWorkflow", "external-methodology"
                ),
                "increment increment.fixture-current fields must match the code-owned schema",
            ),
            (
                "work human round trip",
                lambda increment: increment["workItems"][0].__setitem__(
                    "humanRoundTrip", "user-selects-tool"
                ),
                "work item work.fixture-current fields must match the code-owned schema",
            ),
            (
                "cleanup shifted to user",
                lambda increment: increment["cleanupBoundary"].__setitem__(
                    "userCleanupRequired", True
                ),
                "increment increment.fixture-current requires the exact cleanup boundary fields",
            ),
        )
        for label, mutate_increment, expected_error in variants:
            with self.subTest(label=label):
                self.mutate(
                    "product/program.json",
                    lambda value: mutate_increment(self.activate_program(value)),
                )
                report = self.report()
                self.assertFalse(report["criterionStates"]["G4"])
                self.assertIn(expected_error, report["errors"])
                self.reset_program_fixture()

    def test_empty_ready_current_graph_is_valid_but_not_product_progress(self) -> None:
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_malformed_work_state_fails_without_traceback(self) -> None:
        def malformed(value: dict) -> None:
            self.activate_program(value)["workItems"][0]["state"] = []

        self.mutate("product/program.json", malformed)
        completed = self.run_cli()
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertFalse(report["valid"])
        self.assertIn(
            "work item work.fixture-current has invalid state",
            report["errors"],
        )

    def test_active_work_operations_must_stay_inside_agent_authority(self) -> None:
        def exceed(value: dict) -> None:
            self.activate_program(value)["workItems"][0]["operationIds"].append("release")

        self.mutate("product/program.json", exceed)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "work item work.fixture-current exceeds agent authority",
            report["errors"],
        )

    def test_explicitly_granted_consumer_configuration_is_agent_executed(self) -> None:
        def add_granted_configuration(value: dict) -> None:
            self.activate_program(value)["workItems"][0]["operationIds"].append(
                "bounded-consumer-configuration-after-explicit-grant"
            )

        self.mutate("product/program.json", add_granted_configuration)
        report = self.report()
        self.assertTrue(report["criterionStates"]["G1"], report["errors"])
        program = json.loads((self.root / "product/program.json").read_text())
        self.assertIn("new-trust", program["authorityBoundary"]["userOwns"])

    def test_stopped_work_cannot_hide_an_authority_violation(self) -> None:
        def hide(value: dict) -> None:
            work = self.activate_program(value)["workItems"][0]
            work["state"] = "stopped"
            work["operationIds"].append("release")

        self.mutate("product/program.json", hide)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "work item work.fixture-current exceeds agent authority",
            report["errors"],
        )

    def test_cancelled_work_does_not_claim_an_authority_attempt(self) -> None:
        def cancel_before_execution(value: dict) -> None:
            increment = self.ensure_increment(value, state="cancelled")
            work = increment["workItems"][0]
            work["state"] = "cancelled"
            work["operationIds"].append("release")

        self.mutate("product/program.json", cancel_before_execution)
        report = self.report()
        self.assertTrue(report["criterionStates"]["G1"], report["errors"])
        self.assertNotIn(
            "work item work.fixture-current exceeds agent authority",
            report["errors"],
        )

    def test_authority_boundary_rejects_undeclared_fields(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value["authorityBoundary"].__setitem__(
                "agentMayPublishWithoutHumanAuthority", True
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "program authorityBoundary fields must match the code-owned schema",
            report["errors"],
        )

    def test_human_authority_cannot_be_removed(self) -> None:
        def remove(value: dict) -> None:
            value["authorityBoundary"]["userOwns"].remove("new-trust")

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program userOwns omits a mandatory human authority", report["errors"])

    def test_user_authority_cannot_absorb_agent_work(self) -> None:
        def add(value: dict) -> None:
            value["authorityBoundary"]["userOwns"].append(
                "skill-and-workflow-selection"
            )

        self.mutate("product/program.json", add)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "program userOwns contains an undeclared human authority",
            report["errors"],
        )

    def test_agent_authority_cannot_silently_drop_owned_operations(self) -> None:
        def remove(value: dict) -> None:
            value["authorityBoundary"]["agentOwnsWithinBoundedAuthority"].remove(
                "git-push"
            )

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "program agent authority must equal the code-owned operation set",
            report["errors"],
        )

    def test_agent_authority_cannot_claim_human_only_release(self) -> None:
        def add(value: dict) -> None:
            value["authorityBoundary"]["agentOwnsWithinBoundedAuthority"].append(
                "release-authorization"
            )

        self.mutate("product/program.json", add)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("agent authority overlaps a human-only authority", report["errors"])

    def test_process_loss_budget_fields_are_exact(self) -> None:
        def remove(value: dict) -> None:
            del self.activate_program(value)["processLossBudget"][
                "stopOnUnboundedResidue"
            ]

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current requires the exact process-loss budget fields",
            report["errors"],
        )

    def test_same_correction_class_must_stop_before_recurrence(self) -> None:
        def loosen(value: dict) -> None:
            self.activate_program(value)["processLossBudget"][
                "maxSameClassUserCorrectionBeforeStop"
            ] = 2

        self.mutate("product/program.json", loosen)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "same-class user correction budget must stop before recurrence",
            report["errors"],
        )

    def test_prohibited_agent_work_transfer_budget_is_always_zero(self) -> None:
        def loosen(value: dict) -> None:
            self.activate_program(value)["processLossBudget"][
                "maxProhibitedAgentWorkTransfers"
            ] = 1

        self.mutate("product/program.json", loosen)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "prohibited Agent-work transfer budget must be zero",
            report["errors"],
        )

    def test_increments_cannot_repeat_a_correction_class(self) -> None:
        def repeat(value: dict) -> None:
            first = self.ensure_increment(value, state="completed")
            duplicate = deepcopy(first)
            duplicate["id"] = "increment.repeated-correction"
            duplicate["workItems"][0]["id"] = "work.repeated-correction"
            value["increments"].append(duplicate)

        self.mutate("product/program.json", repeat)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increments repeat correctionClass: fixture-correction",
            report["errors"],
        )

    def test_nonadjacent_correction_recurrence_is_also_rejected(self) -> None:
        def repeat(value: dict) -> None:
            first = self.ensure_increment(value, state="completed")
            middle = deepcopy(first)
            middle["id"] = "increment.middle-correction"
            middle["correctionClass"] = "middle-correction"
            middle["workItems"][0]["id"] = "work.middle-correction"
            last = deepcopy(first)
            last["id"] = "increment.repeated-nonadjacent-correction"
            last["workItems"][0]["id"] = "work.repeated-nonadjacent-correction"
            value["increments"].extend([middle, last])

        self.mutate("product/program.json", repeat)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increments repeat correctionClass: fixture-correction",
            report["errors"],
        )

    def test_outcome_neutral_work_budget_cannot_exceed_one(self) -> None:
        def loosen(value: dict) -> None:
            self.activate_program(value)["processLossBudget"][
                "maxConsecutiveOutcomeNeutralWorkItems"
            ] = 2

        self.mutate("product/program.json", loosen)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("outcome-neutral work budget must be zero or one", report["errors"])

    def test_cancelled_and_stopped_work_count_toward_process_loss(self) -> None:
        baseline = self.read_json("product/program.json")
        for terminal_state in ("cancelled", "stopped"):
            with self.subTest(terminal_state=terminal_state):
                program = deepcopy(baseline)
                increment = self.activate_program(program)
                first = increment["workItems"][0]
                first["state"] = terminal_state
                second = deepcopy(first)
                second["id"] = f"work.after-{terminal_state}"
                second["state"] = "active"
                increment["workItems"].append(second)
                self.write_json("product/program.json", program)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G4"])
                self.assertIn(
                    "increment increment.fixture-current exceeds its "
                    "outcome-neutral work budget",
                    report["errors"],
                )

    def test_ready_program_cannot_accumulate_closed_outcome_neutral_queue(self) -> None:
        def queue(value: dict) -> None:
            first = self.ensure_increment(value, state="completed")
            second = deepcopy(first)
            second["id"] = "increment.second-neutral"
            second["correctionClass"] = "second-neutral-correction"
            second["workItems"][0]["id"] = "work.second-neutral"
            value["increments"].append(second)

        self.mutate("product/program.json", queue)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "closed outcome-neutral increment must leave the current graph: increment.fixture-current",
            report["errors"],
        )
        self.assertIn(
            "closed outcome-neutral increment must leave the current graph: increment.second-neutral",
            report["errors"],
        )

    def test_ready_program_retains_completed_validated_outcome_binding(self) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(criterion_ids=["O1"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["criterionStates"]["O1"])
        self.assertTrue(report["criterionStates"]["G4"])

    def test_cancelled_or_stopped_increment_cannot_retain_outcome_binding(self) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(criterion_ids=["O1"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        baseline = self.read_json("product/program.json")
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            for state in ("cancelled", "stopped"):
                with self.subTest(state=state):
                    program = deepcopy(baseline)
                    program["increments"][0]["state"] = state
                    self.write_json("product/program.json", program)
                    report = self.report()
                    self.assertFalse(report["criterionStates"]["O1"])
                    self.assertFalse(report["criterionStates"]["G4"])
                    self.assertIn(
                        "only a completed increment may retain validated outcome "
                        f"binding: {FIXTURE_INCREMENT_ID}",
                        report["errors"],
                    )

    def test_outcome_label_without_validated_evidence_cannot_reset_neutral_count(self) -> None:
        def label_arbitrage(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            first = increment["workItems"][0]
            first["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)
            first["state"] = "completed"
            second = deepcopy(first)
            second["id"] = "work.second-labeled-neutral-item"
            second["state"] = "active"
            increment["workItems"].append(second)

        self.mutate("product/program.json", label_arbitrage)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "increment increment.fixture-current exceeds its outcome-neutral work budget",
            report["errors"],
        )

    def test_invalid_process_graph_suppresses_outcome_and_cannot_reuse_its_evidence(self) -> None:
        def reuse_evidence(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            first = increment["workItems"][0]
            first["acceptanceIds"].append("O1")
            self.bind_fixture_registration(value, increment)
            first["state"] = "completed"
            second = deepcopy(first)
            second["id"] = "work.second-labeled-item"
            third = deepcopy(first)
            third["id"] = "work.third-labeled-item"
            third["state"] = "active"
            increment["workItems"].extend([second, third])

        self.mutate("product/program.json", reuse_evidence)
        evidence = self.evidence_document(criterion_ids=["O1"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertEqual(report["outcomes"]["verified"], 0)
        self.assertTrue(report["criterionStates"]["G2"], report["errors"])
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current exceeds its outcome-neutral work budget",
            report["errors"],
        )

    def test_declared_repository_residue_fails_closed(self) -> None:
        residue = self.root / ".tmp"
        residue.mkdir()
        (residue / "leftover.txt").write_text("residue", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository cleanup residue remains: .tmp", report["errors"])

    def test_undeclared_conventional_residue_fails_closed_repository_wide(self) -> None:
        cache = self.root / "unlisted" / "__pycache__"
        cache.mkdir(parents=True)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "repository cleanup residue remains: unlisted/__pycache__",
            report["errors"],
        )

    def test_conventional_residue_file_fails_closed_with_empty_graph(self) -> None:
        residue = self.root / ".tmp"
        residue.write_text("residue", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository cleanup residue remains: .tmp", report["errors"])

    def test_wider_temporary_process_residue_patterns_fail_closed(self) -> None:
        for relative in (".pytest_cache/state", "logs/task.log", "patch.orig"):
            with self.subTest(relative=relative):
                target = self.root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("residue", encoding="utf-8")
                report = self.report()
                expected = ".pytest_cache" if relative.startswith(".pytest_cache/") else relative
                self.assertFalse(report["criterionStates"]["G4"])
                self.assertIn(
                    f"repository cleanup residue remains: {expected}", report["errors"]
                )
                target.unlink()
                if target.parent != self.root:
                    target.parent.rmdir()

    def test_repository_residue_enumeration_error_fails_closed(self) -> None:
        real_scandir = os.scandir
        fixture_root = self.root.resolve()

        def unreadable_root(path):
            if Path(path).resolve() == fixture_root:
                raise PermissionError("fixture access denied")
            return real_scandir(path)

        with patch("harness.control.os.scandir", side_effect=unreadable_root):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository residue cannot be enumerated", report["errors"])

    def test_repository_residue_scan_has_entry_and_depth_limits(self) -> None:
        with patch("harness.control.MAX_REPOSITORY_WALK_ENTRIES", 1):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository residue scan entry limit exceeded", report["errors"])

        with patch("harness.control.MAX_REPOSITORY_WALK_DEPTH", 0):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository residue scan depth limit exceeded", report["errors"])

    def test_dangling_cleanup_symlink_is_residue(self) -> None:
        self.mutate("product/program.json", self.activate_program)
        link = self.root / ".tmp"
        try:
            link.symlink_to(self.root / "missing-target", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("cleanup path cannot traverse a link or reparse point: .tmp", report["errors"])

    def test_cleanup_locator_cannot_traverse(self) -> None:
        def traverse(value: dict) -> None:
            self.activate_program(value)["cleanupBoundary"][
                "repositoryTemporaryPaths"
            ] = ["../outside"]

        self.mutate("product/program.json", traverse)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("invalid repository cleanup path: '../outside'", report["errors"])

    def test_private_resource_disposition_must_be_public_safe_and_code_owned(self) -> None:
        def expose_private_locator(value: dict) -> None:
            self.activate_program(value)["cleanupBoundary"][
                "privateResourceDispositions"
            ] = [r"C:\\Users\\person\\.codex\\private-evidence.json"]

        self.mutate("product/program.json", expose_private_locator)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current requires exact privacy-safe "
            "private resource dispositions",
            report["errors"],
        )

    def test_initial_binding_private_source_rejects_boolean_schema_alias(self) -> None:
        private_evidence = {
            "schema": True,
            "kind": "agent-autonomy-harness-v1-provisional-cohort-private-evidence",
            "surfaceIdentity": (
                "enrollment-surface.public-v1:f0e705cf4cc54e13afdc993442811187"
            ),
            "activationCursorCommitment": (
                "hmac-sha256:e6038957ab84aea02af9c45ee8e19277"
                "e9cf14045634345571ed0b62d866003a"
            ),
            "keyIdentity": "cohort-key.public-v1:2d81fdcaa26da32778089bb53198e190",
            "keyFingerprint": (
                "sha256:6d0edc4c500afdb7cc3a3e35a5805b21"
                "87feb8fb7958c90f0a21e4101721a0e3"
            ),
            "sourceKind": "codex-rollout-user-event-v1",
            "disposition": (
                "authorized-retain-through-v1-accepted-or-stopped-no-later-than-"
                "2026-12-31T23:59:59+08:00-delete-and-revoke-on-withdrawal-"
                "expiry-stop-or-validation-failure"
            ),
        }
        errors: list[str] = []

        self.assertFalse(
            control._initial_authorization_event_window_valid(
                private_evidence,
                {
                    "kind": "initial-normative-profile-binding-authorization",
                    "revision": control.EXPECTED_V1_INITIAL_BINDING_REVISION,
                    "bindingSha256": control.EXPECTED_V1_INITIAL_BINDING_SHA256,
                },
                errors,
            )
        )
        self.assertIn(
            "initial binding authorization private source does not match the frozen activation",
            errors,
        )

    def test_initial_authorization_snapshot_binds_event_identity_time_and_window(
        self,
    ) -> None:
        key = b"k" * 32
        activation_identity = "11111111-1111-4111-8111-111111111111"
        authorization_identity = "22222222-2222-4222-8222-222222222222"
        activation_timestamp = "2026-08-15T01:00:00+00:00"
        authorization_timestamp = "2026-08-15T01:00:01+00:00"
        authorization_message = "fixture exact authorization"
        private_evidence = {
            "surfaceIdentity": "enrollment-surface.public-v1:fixture",
            "sourceEventIdentity": activation_identity,
            "sourceEventTimestamp": activation_timestamp,
        }

        def encoded(event: dict) -> bytes:
            return (
                json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")

        activation = {
            "timestamp": activation_timestamp,
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "client_id": activation_identity,
                "message": "授权！",
            },
        }
        authorization = {
            "timestamp": authorization_timestamp,
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "client_id": authorization_identity,
                "message": authorization_message,
            },
        }
        snapshot = encoded(activation) + encoded(authorization)
        event_commitment = fixture_private_hmac(
            key,
            control.INITIAL_AUTHORIZATION_EVENT_HMAC_DOMAIN,
            private_evidence["surfaceIdentity"],
            activation_identity,
            authorization_identity,
            "2026-08-15T01:00:01Z",
            authorization_message,
        )
        window_commitment = fixture_private_bytes_hmac(
            key,
            control.INITIAL_AUTHORIZATION_WINDOW_HMAC_DOMAIN,
            snapshot,
        )
        patches = {
            "EXPECTED_INITIAL_BINDING_AUTHORIZATION_MESSAGE_SHA256": hashlib.sha256(
                authorization_message.encode("utf-8")
            ).hexdigest(),
            "EXPECTED_INITIAL_AUTHORIZATION_EVENT_COMMITMENT": event_commitment,
            "EXPECTED_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT": window_commitment,
        }
        with patch.multiple(control, **patches):
            errors: list[str] = []
            self.assertTrue(
                control._initial_authorization_snapshot_valid(
                    private_evidence,
                    snapshot,
                    bytearray(key),
                    errors,
                ),
                errors,
            )

            changed_id = deepcopy(authorization)
            changed_id["payload"]["client_id"] = (
                "33333333-3333-4333-8333-333333333333"
            )
            errors = []
            self.assertFalse(
                control._initial_authorization_snapshot_valid(
                    private_evidence,
                    encoded(activation) + encoded(changed_id),
                    bytearray(key),
                    errors,
                )
            )

            changed_time = deepcopy(authorization)
            changed_time["timestamp"] = "2026-08-15T01:00:02+00:00"
            errors = []
            self.assertFalse(
                control._initial_authorization_snapshot_valid(
                    private_evidence,
                    encoded(activation) + encoded(changed_time),
                    bytearray(key),
                    errors,
                )
            )

            inserted = encoded(
                {
                    "timestamp": "2026-08-15T01:00:00.500000+00:00",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "client_id": "44444444-4444-4444-8444-444444444444",
                        "message": "an intervening demand",
                    },
                }
            )
            errors = []
            self.assertFalse(
                control._initial_authorization_snapshot_valid(
                    private_evidence,
                    encoded(activation) + inserted + encoded(authorization),
                    bytearray(key),
                    errors,
                )
            )

    def test_initial_authorization_target_and_local_source_root_are_exact(self) -> None:
        key = b"r" * 32
        target_name = "AgentAutonomyHarness/v1/exact-fixture"
        source_root = PureWindowsPath(r"C:\Users\fixture\.codex\sessions")
        target_commitment = fixture_private_hmac(
            key,
            control.INITIAL_AUTHORIZATION_TARGET_HMAC_DOMAIN,
            target_name,
        )
        root_commitment = fixture_private_hmac(
            key,
            control.INITIAL_AUTHORIZATION_SOURCE_ROOT_HMAC_DOMAIN,
            str(source_root).casefold(),
        )
        with patch.multiple(
            control,
            EXPECTED_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT=(
                target_commitment
            ),
            EXPECTED_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT=root_commitment,
        ), patch(
            "harness.control._windows_system_drive", return_value="C:"
        ), patch(
            "harness.control._windows_drive_is_fixed", return_value=True
        ):
            errors: list[str] = []
            self.assertTrue(
                control._initial_authorization_credential_target_valid(
                    target_name, bytearray(key), errors
                ),
                errors,
            )
            self.assertIsNotNone(
                control._initial_authorization_source_locator_parts(
                    r"C:\Users\fixture\.codex\sessions\2026\08\15\rollout-fixture.jsonl",
                    bytearray(key),
                    errors,
                ),
                errors,
            )

            for locator in (
                r"\\host\Users\fixture\.codex\sessions\2026\08\15\rollout-fixture.jsonl",
                r"\\?\C:\Users\fixture\.codex\sessions\2026\08\15\rollout-fixture.jsonl",
                r"\\.\C:\Users\fixture\.codex\sessions\2026\08\15\rollout-fixture.jsonl",
                r"D:\Users\fixture\.codex\sessions\2026\08\15\rollout-fixture.jsonl",
                r"C:\outside\2026\08\15\rollout-fixture.jsonl",
            ):
                with self.subTest(locator=locator):
                    locator_errors: list[str] = []
                    self.assertIsNone(
                        control._initial_authorization_source_locator_parts(
                            locator,
                            bytearray(key),
                            locator_errors,
                        )
                    )
                    self.assertTrue(locator_errors)

            replacement_errors: list[str] = []
            self.assertFalse(
                control._initial_authorization_credential_target_valid(
                    "AgentAutonomyHarness/v1/replacement-fixture",
                    bytearray(key),
                    replacement_errors,
                )
            )

    def test_initial_authorization_snapshot_rejects_replacement_and_mutation(
        self,
    ) -> None:
        source = self.root / "rollout-fixture.jsonl"
        replacement = self.root / "rollout-replacement.jsonl"
        source.write_bytes(b'{"fixture":"source"}\n')
        replacement.write_bytes(b'{"fixture":"other!"}\n')
        errors: list[str] = []
        with patch(
            "harness.control._open_initial_authorization_source",
            side_effect=lambda path: path.open("rb"),
        ), patch(
            "harness.control._initial_authorization_opened_final_path",
            side_effect=lambda stream: str(source),
        ), patch(
            "harness.control._lock_initial_authorization_source",
            return_value=control._WindowsOverlapped(),
        ), patch(
            "harness.control._unlock_initial_authorization_source",
        ):
            self.assertEqual(
                control._read_stable_initial_authorization_snapshot(
                    source,
                    str(self.root),
                    errors,
                ),
                source.read_bytes(),
                errors,
            )

        errors = []
        with patch(
            "harness.control._open_initial_authorization_source",
            side_effect=lambda path: replacement.open("rb"),
        ), patch(
            "harness.control._initial_authorization_opened_final_path",
            side_effect=lambda stream: str(replacement),
        ), patch(
            "harness.control._lock_initial_authorization_source",
            return_value=control._WindowsOverlapped(),
        ), patch(
            "harness.control._unlock_initial_authorization_source",
        ):
            self.assertIsNone(
                control._read_stable_initial_authorization_snapshot(
                    source,
                    str(self.root),
                    errors,
                )
            )
        self.assertTrue(errors)

        class MutatingStream:
            def __init__(self, path: Path) -> None:
                self.path = path
                self.stream = path.open("rb")

            def fileno(self) -> int:
                return self.stream.fileno()

            def read(self, size: int = -1) -> bytes:
                self.path.write_bytes(b'{"fixture":"mutated-longer"}\n')
                return self.stream.read(size)

            def close(self) -> None:
                self.stream.close()

        source.write_bytes(b'{"fixture":"source"}\n')
        errors = []
        with patch(
            "harness.control._open_initial_authorization_source",
            side_effect=lambda path: MutatingStream(path),
        ), patch(
            "harness.control._initial_authorization_opened_final_path",
            side_effect=lambda stream: str(source),
        ), patch(
            "harness.control._lock_initial_authorization_source",
            return_value=control._WindowsOverlapped(),
        ), patch(
            "harness.control._unlock_initial_authorization_source",
        ):
            self.assertIsNone(
                control._read_stable_initial_authorization_snapshot(
                    source,
                    str(self.root),
                    errors,
                )
            )
        self.assertTrue(errors)

    def test_initial_authorization_failure_and_crossed_expiry_delete_exact_resource(
        self,
    ) -> None:
        document = {
            "kind": "initial-normative-profile-binding-authorization",
            "revision": control.EXPECTED_V1_INITIAL_BINDING_REVISION,
            "bindingSha256": control.EXPECTED_V1_INITIAL_BINDING_SHA256,
        }
        resource = ({"fixture": "private"}, "AgentAutonomyHarness/v1/exact")
        before_expiry = datetime(2026, 12, 31, 15, 59, 58, tzinfo=timezone.utc)
        after_expiry = datetime(2026, 12, 31, 16, 0, 0, tzinfo=timezone.utc)

        def invalid_event(*args, **kwargs) -> bool:
            del kwargs
            args[-1].append("fixture private validation failed")
            return False

        with patch(
            "harness.control._utc_now", return_value=before_expiry
        ), patch(
            "harness.control._read_initial_authorization_private_evidence",
            return_value=resource,
        ), patch(
            "harness.control._initial_authorization_event_window_valid",
            side_effect=invalid_event,
        ), patch(
            "harness.control._delete_initial_authorization_private_resource",
            return_value=True,
        ) as delete:
            errors: list[str] = []
            self.assertFalse(
                control._validate_initial_binding_authorization(
                    document, self.root, errors
                )
            )
            delete.assert_called_once()
            self.assertEqual(delete.call_args.args[1], "validation-failure")

        with patch(
            "harness.control._utc_now",
            side_effect=(before_expiry, after_expiry),
        ), patch(
            "harness.control._read_initial_authorization_private_evidence",
            return_value=resource,
        ), patch(
            "harness.control._initial_authorization_event_window_valid",
            return_value=True,
        ), patch(
            "harness.control._delete_initial_authorization_private_resource",
            return_value=True,
        ) as delete:
            errors = []
            self.assertFalse(
                control._validate_initial_binding_authorization(
                    document, self.root, errors
                )
            )
            delete.assert_called_once()
            self.assertEqual(delete.call_args.args[1], "expiry")

        with patch(
            "harness.control._utc_now", return_value=before_expiry
        ), patch(
            "harness.control._read_initial_authorization_private_evidence",
            return_value=resource,
        ), patch(
            "harness.control._initial_authorization_event_window_valid",
            return_value=True,
        ), patch(
            "harness.control._delete_initial_authorization_private_resource"
        ) as delete:
            errors = []
            self.assertTrue(
                control._validate_initial_binding_authorization(
                    document, self.root, errors
                ),
                errors,
            )
            delete.assert_not_called()

    def test_initial_authorization_transient_source_failure_is_non_destructive(
        self,
    ) -> None:
        document = {
            "kind": "initial-normative-profile-binding-authorization",
            "revision": control.EXPECTED_V1_INITIAL_BINDING_REVISION,
            "bindingSha256": control.EXPECTED_V1_INITIAL_BINDING_SHA256,
        }
        resource = ({"fixture": "private"}, "AgentAutonomyHarness/v1/exact")

        for diagnostic in sorted(
            control.NONDESTRUCTIVE_INITIAL_AUTHORIZATION_SOURCE_FAILURES
        ):
            with self.subTest(diagnostic=diagnostic), patch(
                "harness.control._utc_now",
                return_value=datetime(2026, 12, 31, 15, 59, 58, tzinfo=timezone.utc),
            ), patch(
                "harness.control._read_initial_authorization_private_evidence",
                return_value=resource,
            ), patch(
                "harness.control._initial_authorization_event_window_valid",
                side_effect=lambda *args, **kwargs: (
                    args[2].append(diagnostic) or False
                ),
            ), patch(
                "harness.control._delete_initial_authorization_private_resource",
            ) as delete:
                errors: list[str] = []
                self.assertFalse(
                    control._validate_initial_binding_authorization(
                        document,
                        self.root,
                        errors,
                    )
                )
                self.assertEqual(errors, [diagnostic])
                delete.assert_not_called()

    def test_initial_authorization_unclassified_failure_remains_destructive(
        self,
    ) -> None:
        document = {
            "kind": "initial-normative-profile-binding-authorization",
            "revision": control.EXPECTED_V1_INITIAL_BINDING_REVISION,
            "bindingSha256": control.EXPECTED_V1_INITIAL_BINDING_SHA256,
        }
        resource = ({"fixture": "private"}, "AgentAutonomyHarness/v1/exact")

        with patch(
            "harness.control._utc_now",
            return_value=datetime(2026, 12, 31, 15, 59, 58, tzinfo=timezone.utc),
        ), patch(
            "harness.control._read_initial_authorization_private_evidence",
            return_value=resource,
        ), patch(
            "harness.control._initial_authorization_event_window_valid",
            return_value=False,
        ), patch(
            "harness.control._delete_initial_authorization_private_resource",
            return_value=True,
        ) as delete:
            errors: list[str] = []
            self.assertFalse(
                control._validate_initial_binding_authorization(
                    document,
                    self.root,
                    errors,
                )
            )
            delete.assert_called_once_with(resource, "validation-failure", errors)

    def test_v11_initial_private_cleanup_route_is_not_executable(self) -> None:
        errors: list[str] = []
        with patch("harness.control.ctypes.WinDLL", create=True) as win_dll:
            self.assertFalse(
                control._delete_initial_authorization_private_resource(
                    ({"fixture": "private"}, "historical-target"),
                    "validation-failure",
                    errors,
                )
            )
        win_dll.assert_not_called()
        self.assertEqual(
            errors,
            [
                "initial binding authorization private cleanup is historical and unavailable in v1.1"
            ],
        )

    def test_initial_authorization_stop_and_withdrawal_use_cleanup_route(self) -> None:
        resource = ({"fixture": "private"}, "AgentAutonomyHarness/v1/exact")
        for trigger in ("stop", "withdrawal"):
            with self.subTest(trigger=trigger), patch(
                "harness.control._read_initial_authorization_private_evidence",
                return_value=resource,
            ), patch(
                "harness.control._delete_initial_authorization_private_resource",
                return_value=True,
            ) as delete:
                errors: list[str] = []
                self.assertTrue(
                    control._revoke_initial_authorization_private_evidence(
                        trigger,
                        errors,
                    )
                )
                delete.assert_called_once_with(resource, trigger, errors)

    def test_successor_authorization_snapshot_binds_complete_zero_demand_window(
        self,
    ) -> None:
        key = b"s" * 32
        predecessor_identity = "call_0123456789ABCDEF"
        restart_identity = "11111111-1111-4111-8111-111111111111"
        authorization_identity = "22222222-2222-4222-8222-222222222222"
        predecessor_timestamp = "2026-08-16T00:00:00Z"
        restart_timestamp = "2026-08-16T00:00:01Z"
        authorization_timestamp = "2026-08-16T00:00:02Z"
        authorization_message = "fixture exact successor authorization"
        surface = "enrollment-surface.public-v1:fixture"
        private_evidence = {
            "surfaceIdentity": surface,
            "predecessorRevocationRecordIdentity": predecessor_identity,
            "predecessorRevocationRecordTimestamp": predecessor_timestamp,
            "sourceEventIdentity": restart_identity,
            "sourceEventTimestamp": restart_timestamp,
            "authorizationEventIdentity": authorization_identity,
            "authorizationEventTimestamp": authorization_timestamp,
        }

        def encoded(event: dict) -> bytes:
            return (
                json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")

        predecessor = encoded(
            {
                "timestamp": predecessor_timestamp,
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call_output",
                    "call_id": predecessor_identity,
                    "output": {"type": "computer_initialize_state", "id": "fixture"},
                },
            }
        )
        restart = encoded(
            {
                "timestamp": restart_timestamp,
                "type": "event_msg",
                "payload": {
                    "type": "user_message",
                    "client_id": restart_identity,
                    "message": "同意重启 cohort。",
                },
            }
        )
        authorization = encoded(
            {
                "timestamp": authorization_timestamp,
                "type": "event_msg",
                "payload": {
                    "type": "user_message",
                    "client_id": authorization_identity,
                    "message": authorization_message,
                },
            }
        )
        snapshot = predecessor + restart + authorization
        patches = {
            "EXPECTED_SUCCESSOR_PREDECESSOR_RECORD_COMMITMENT": (
                fixture_private_bytes_hmac(
                    key,
                    control.SUCCESSOR_PREDECESSOR_RECORD_HMAC_DOMAIN,
                    predecessor,
                )
            ),
            "EXPECTED_SUCCESSOR_RESTART_EVENT_COMMITMENT": fixture_private_hmac(
                key,
                control.SUCCESSOR_RESTART_EVENT_HMAC_DOMAIN,
                surface,
                predecessor_identity,
                restart_identity,
                restart_timestamp,
                "同意重启 cohort。",
            ),
            "EXPECTED_SUCCESSOR_BINDING_AUTHORIZATION_MESSAGE_SHA256": (
                hashlib.sha256(authorization_message.encode("utf-8")).hexdigest()
            ),
            "EXPECTED_SUCCESSOR_AUTHORIZATION_EVENT_COMMITMENT": (
                fixture_private_hmac(
                    key,
                    control.SUCCESSOR_AUTHORIZATION_EVENT_HMAC_DOMAIN,
                    surface,
                    predecessor_identity,
                    restart_identity,
                    authorization_identity,
                    authorization_timestamp,
                    authorization_message,
                )
            ),
            "EXPECTED_SUCCESSOR_AUTHORIZATION_WINDOW_COMMITMENT": (
                fixture_private_bytes_hmac(
                    key,
                    control.SUCCESSOR_AUTHORIZATION_WINDOW_HMAC_DOMAIN,
                    snapshot,
                )
            ),
        }
        with patch.multiple(control, **patches):
            errors: list[str] = []
            self.assertTrue(
                control._successor_authorization_snapshot_valid(
                    private_evidence,
                    snapshot,
                    bytearray(key),
                    errors,
                ),
                errors,
            )

            inserted = encoded(
                {
                    "timestamp": "2026-08-16T00:00:01.500000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "client_id": "33333333-3333-4333-8333-333333333333",
                        "message": "an intervening demand",
                    },
                }
            )
            errors = []
            self.assertFalse(
                control._successor_authorization_snapshot_valid(
                    private_evidence,
                    predecessor + restart + inserted + authorization,
                    bytearray(key),
                    errors,
                )
            )
            self.assertIn(
                "natural demand appeared before exact successor-freeze authorization",
                errors,
            )

            changed_predecessor = predecessor.replace(b"fixture", b"changed")
            errors = []
            self.assertFalse(
                control._successor_authorization_snapshot_valid(
                    private_evidence,
                    changed_predecessor + restart + authorization,
                    bytearray(key),
                    errors,
                )
            )

    def test_successor_authorization_failure_policy_and_expiry_cleanup(self) -> None:
        document = {
            "kind": "successor-normative-profile-binding-authorization",
            "revision": control.EXPECTED_V1_SUCCESSOR_BINDING_REVISION,
            "bindingSha256": control.EXPECTED_V1_SUCCESSOR_BINDING_SHA256,
            "predecessorRevocationRevision": (
                control.EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION
            ),
            "predecessorRevocationBindingSha256": (
                control.EXPECTED_V1_PREDECESSOR_REVOCATION_BINDING_SHA256
            ),
            "sourceWindowRule": (
                control.EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_WINDOW_RULE
            ),
        }
        resource = (
            {"fixture": "private"},
            "AgentAutonomyHarness/v1-successor/exact",
        )
        before_expiry = datetime(2026, 12, 31, 15, 59, 58, tzinfo=timezone.utc)
        after_expiry = datetime(2026, 12, 31, 16, 0, 0, tzinfo=timezone.utc)

        for diagnostic in sorted(
            control.NONDESTRUCTIVE_SUCCESSOR_AUTHORIZATION_SOURCE_FAILURES
        ):
            with self.subTest(diagnostic=diagnostic), patch(
                "harness.control._utc_now", return_value=before_expiry
            ), patch(
                "harness.control._read_successor_authorization_private_evidence",
                return_value=resource,
            ), patch(
                "harness.control._successor_authorization_event_window_valid",
                side_effect=lambda *args, **kwargs: (
                    args[2].append(diagnostic) or False
                ),
            ), patch(
                "harness.control._delete_successor_authorization_private_resource",
            ) as delete:
                errors: list[str] = []
                self.assertFalse(
                    control._validate_successor_binding_authorization(
                        document,
                        self.root,
                        errors,
                    )
                )
                self.assertEqual(errors, [diagnostic])
                delete.assert_not_called()

        with patch(
            "harness.control._utc_now", return_value=before_expiry
        ), patch(
            "harness.control._read_successor_authorization_private_evidence",
            return_value=resource,
        ), patch(
            "harness.control._successor_authorization_event_window_valid",
            return_value=False,
        ), patch(
            "harness.control._delete_successor_authorization_private_resource",
            return_value=True,
        ) as delete:
            errors = []
            self.assertFalse(
                control._validate_successor_binding_authorization(
                    document,
                    self.root,
                    errors,
                )
            )
            delete.assert_called_once_with(resource, "validation-failure", errors)

        self.assertFalse(
            hasattr(control, "expire_successor_authorization_private_evidence")
        )
        errors = []
        self.assertFalse(
            control._delete_successor_authorization_private_resource(
                resource,
                "expiry",
                errors,
            )
        )
        self.assertEqual(
            errors,
            [
                "successor binding authorization private cleanup is historical and unavailable in v1.1"
            ],
        )

    def test_successor_expiry_trigger_definition_is_exact_and_s4u(self) -> None:
        expected_python = self.root / "python.exe"
        expected_root = self.root
        expected_user_sid = "S-1-5-21-111111111-222222222-333333333-1001"

        def task_xml(
            *,
            logon_type: str = "S4U",
            arguments: str | None = None,
            user_sid: str = expected_user_sid,
            run_level: str = "LeastPrivilege",
            enabled: str = "true",
            disallow_on_battery: str = "false",
            stop_on_battery: str = "false",
            include_battery_settings: bool = True,
            canonical_windows_export: bool = False,
            idle_stop: str = "true",
            idle_restart: str = "false",
            extra_settings: str = "",
            extra_trigger: str = "",
            extra_action: str = "",
        ):
            battery_settings = (
                f"<DisallowStartIfOnBatteries>{disallow_on_battery}</DisallowStartIfOnBatteries>"
                f"<StopIfGoingOnBatteries>{stop_on_battery}</StopIfGoingOnBatteries>"
                if include_battery_settings
                else ""
            )
            trigger_enabled = "" if canonical_windows_export else "<Enabled>true</Enabled>"
            principal_run_level = (
                "" if canonical_windows_export else f"<RunLevel>{run_level}</RunLevel>"
            )
            settings_defaults = (
                (
                    "<IdleSettings>"
                    f"<StopOnIdleEnd>{idle_stop}</StopOnIdleEnd>"
                    f"<RestartOnIdle>{idle_restart}</RestartOnIdle>"
                    "</IdleSettings>"
                )
                if canonical_windows_export
                else (
                    "<RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>"
                    f"<Enabled>{enabled}</Enabled>"
                )
            )
            return control.ET.fromstring(
                f"""
                <Task>
                  <Triggers><TimeTrigger><StartBoundary>{control.SUCCESSOR_EXPIRY_TASK_START_BOUNDARY}</StartBoundary>{trigger_enabled}</TimeTrigger>{extra_trigger}</Triggers>
                  <Principals><Principal><UserId>{user_sid}</UserId><LogonType>{logon_type}</LogonType>{principal_run_level}</Principal></Principals>
                  <Settings>
                    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
                    {battery_settings}
                    <StartWhenAvailable>true</StartWhenAvailable>
                    {settings_defaults}
                    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
                    {extra_settings}
                  </Settings>
                  <Actions><Exec>
                    <Command>{expected_python}</Command>
                    <Arguments>{arguments or control.SUCCESSOR_EXPIRY_TASK_ARGUMENTS}</Arguments>
                    <WorkingDirectory>{expected_root}</WorkingDirectory>
                  </Exec>{extra_action}</Actions>
                </Task>
                """
            )

        errors: list[str] = []
        self.assertTrue(
            control._successor_expiry_task_definition_valid(
                task_xml(),
                expected_python,
                expected_root,
                expected_user_sid,
                errors,
            ),
            errors,
        )
        errors = []
        self.assertTrue(
            control._successor_expiry_task_definition_valid(
                task_xml(canonical_windows_export=True),
                expected_python,
                expected_root,
                expected_user_sid,
                errors,
            ),
            errors,
        )
        current_task = task_xml(arguments=control.CURRENT_INITIAL_EXPIRY_TASK_ARGUMENTS)
        errors = []
        self.assertTrue(
            control._current_initial_expiry_task_definition_valid(
                current_task,
                expected_python,
                expected_root,
                expected_user_sid,
                errors,
            ),
            errors,
        )
        errors = []
        self.assertFalse(
            control._current_initial_expiry_task_definition_valid(
                task_xml(),
                expected_python,
                expected_root,
                expected_user_sid,
                errors,
            )
        )
        self.assertEqual(
            errors,
            ["current v1.1 binding authorization expiry cleanup trigger is invalid"],
        )
        for invalid in (
            task_xml(logon_type="InteractiveToken"),
            task_xml(arguments="-B -m harness verify"),
            task_xml(user_sid="S-1-5-18"),
            task_xml(run_level="HighestAvailable"),
            task_xml(enabled="false"),
            task_xml(disallow_on_battery="true"),
            task_xml(stop_on_battery="true"),
            task_xml(include_battery_settings=False),
            task_xml(canonical_windows_export=True, idle_stop="false"),
            task_xml(canonical_windows_export=True, idle_restart="true"),
            task_xml(
                canonical_windows_export=True,
                extra_settings="<RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>",
            ),
            task_xml(extra_settings="<RunOnlyIfIdle>true</RunOnlyIfIdle>"),
            task_xml(
                extra_settings=(
                    "<RestartOnFailure><Interval>PT1M</Interval><Count>99</Count>"
                    "</RestartOnFailure>"
                )
            ),
            task_xml(extra_settings="<AllowHardTerminate>false</AllowHardTerminate>"),
            task_xml(extra_trigger="<BootTrigger><Enabled>true</Enabled></BootTrigger>"),
            task_xml(extra_action="<ComHandler><ClassId>fixture</ClassId></ComHandler>"),
        ):
            errors = []
            self.assertFalse(
                control._successor_expiry_task_definition_valid(
                    invalid,
                    expected_python,
                    expected_root,
                    expected_user_sid,
                    errors,
                )
            )
            self.assertEqual(
                errors,
                ["successor binding authorization expiry cleanup trigger is invalid"],
            )

    def test_v11_successor_expiry_trigger_removal_is_not_executable(self) -> None:
        with patch("harness.control.subprocess.run") as run:
            errors: list[str] = []
            self.assertFalse(
                control._remove_successor_expiry_cleanup_trigger(errors)
            )
        run.assert_not_called()
        self.assertEqual(
            errors,
            [
                "successor binding authorization expiry cleanup trigger removal is historical and unavailable in v1.1"
            ],
        )

    def test_revoked_private_resource_absence_is_code_verified(self) -> None:
        last_error = {"value": 0}

        def set_last_error(value: int) -> int:
            previous = last_error["value"]
            last_error["value"] = value
            return previous

        def get_last_error() -> int:
            return last_error["value"]

        class FakeFunction:
            def __init__(self, callback) -> None:
                self.callback = callback
                self.argtypes = None
                self.restype = None

            def __call__(self, *args):
                return self.callback(*args)

        def absent(*args) -> int:
            del args
            control.ctypes.set_last_error(1168)
            return 0

        class AbsentAdvapi:
            CredEnumerateW = FakeFunction(absent)
            CredFree = FakeFunction(lambda value: None)

        class PresentAdvapi:
            CredEnumerateW = FakeFunction(lambda *args: 1)
            CredFree = FakeFunction(lambda value: None)

        common_patches = (
            patch.object(control, "os", SimpleNamespace(name="nt")),
            patch(
                "harness.control.ctypes.set_last_error",
                side_effect=set_last_error,
                create=True,
            ),
            patch(
                "harness.control.ctypes.get_last_error",
                side_effect=get_last_error,
                create=True,
            ),
        )
        with common_patches[0], common_patches[1], common_patches[2], patch(
            "harness.control.ctypes.WinDLL",
            return_value=AbsentAdvapi(),
            create=True,
        ):
            errors: list[str] = []
            self.assertTrue(
                control._initial_authorization_private_resource_absent(errors),
                errors,
            )

        with patch.object(control, "os", SimpleNamespace(name="nt")), patch(
            "harness.control.ctypes.set_last_error",
            side_effect=set_last_error,
            create=True,
        ), patch(
            "harness.control.ctypes.get_last_error",
            side_effect=get_last_error,
            create=True,
        ), patch(
            "harness.control.ctypes.WinDLL",
            return_value=PresentAdvapi(),
            create=True,
        ):
            errors = []
            self.assertFalse(
                control._initial_authorization_private_resource_absent(errors)
            )
            self.assertEqual(
                errors,
                ["revoked initial binding private resource still exists"],
            )

    def test_bootstrap_authority_set_cannot_self_disable(self) -> None:
        def remove(value: dict) -> None:
            value["requiredAuthorityFiles"].remove("product/acceptance.json")

        self.mutate("product/constitution.json", remove)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "requiredAuthorityFiles must equal the code-owned bootstrap set",
            report["errors"],
        )

    def test_active_authority_globs_cannot_broaden_into_archives(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value.__setitem__("activeAuthorityGlobs", ["**/*"]),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "activeAuthorityGlobs must equal the code-owned lean authority globs",
            report["errors"],
        )

    def test_active_authority_symlink_is_rejected(self) -> None:
        target = self.root / "harness" / "control-real.py"
        original = self.root / "harness" / "control.py"
        original.rename(target)
        try:
            original.symlink_to(target)
        except OSError as exc:
            target.rename(original)
            self.skipTest(f"symlink unavailable: {exc}")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertTrue(
            any("active authority cannot traverse a link or reparse point" in item for item in report["errors"]),
            report["errors"],
        )

    def test_undeclared_nested_harness_code_cannot_escape_authority_scan(self) -> None:
        nested = self.root / "harness" / "nested" / "authority.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("VALUE = 'hidden authority'\n", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "undeclared Harness authority file: harness/nested/authority.py",
            report["errors"],
        )

    def test_harness_authority_enumeration_error_fails_closed(self) -> None:
        real_scandir = os.scandir

        def unreadable_harness(path):
            if Path(path).name == "harness":
                raise PermissionError("fixture access denied")
            return real_scandir(path)

        with patch("harness.control.os.scandir", side_effect=unreadable_harness):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("Harness authority closure cannot be enumerated", report["errors"])

    def test_authority_enumeration_has_a_code_owned_entry_limit(self) -> None:
        with patch("harness.control.MAX_AUTHORITY_WALK_ENTRIES", 1):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertTrue(
            any("authority" in item and "entry limit exceeded" in item for item in report["errors"]),
            report["errors"],
        )

    def test_forbidden_predecessor_identity_is_rejected_from_current_authority(self) -> None:
        predecessor = "agent" + "-skills" + "-curated"
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("purpose", predecessor),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "forbidden predecessor identity in active authority: product/program.json",
            report["errors"],
        )

    def test_historical_evidence_is_not_current_authority(self) -> None:
        predecessor = "agent" + "-skills" + "-curated"
        self.write_json(
            "product/evidence/history.json",
            {"schema": 1, "historicalIdentity": predecessor},
        )
        report = self.report()
        self.assertTrue(report["criterionStates"]["G3"], report["errors"])
        self.assertTrue(report["valid"], report["errors"])

    def test_planned_criterion_cannot_bind_evidence(self) -> None:
        def add(value: dict) -> None:
            next(item for item in value["criteria"] if item["id"] == "O2")[
                "evidence"
            ] = ["product/evidence/self.json"]

        self.mutate("product/acceptance.json", add)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn("non-verified criterion O2 cannot bind evidence", report["errors"])

    def test_verified_criterion_requires_evidence(self) -> None:
        def promote(value: dict) -> None:
            next(item for item in value["criteria"] if item["id"] == "O2")[
                "assessment"
            ] = "verified"

        self.mutate("product/acceptance.json", promote)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("verified criterion O2 requires evidence", report["errors"])

    def test_self_declared_evidence_cannot_promote_without_code_validator(self) -> None:
        evidence = self.evidence_document(validator_kind="missing-validator")
        evidence["id"] = "self-declared-o2"
        self.write_json("product/evidence/self.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O2")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/self.json"]

        self.mutate("product/acceptance.json", promote)
        self.map_outcome_to_latest_work("O2")
        report = self.report()
        self.assertFalse(report["criterionStates"]["O2"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "criterion O2 has no code-owned evidence validator: missing-validator",
            report["errors"],
        )

    def test_weak_generic_evidence_identity_authority_or_result_fails_closed(self) -> None:
        self.map_outcome_to_latest_work("O2")

        def precede_observation_below_microsecond(value: dict) -> None:
            value["observedAt"] = "2026-08-12T03:00:00.0000009+08:00"
            value["authority"]["decidedAt"] = "2026-08-12T03:00:00.0000001+08:00"

        mutations = {
            "boolean schema": lambda value: value.__setitem__("schema", True),
            "missing work binding": lambda value: value.pop("workItemId"),
            "wrong increment binding": lambda value: value.__setitem__(
                "incrementId", "increment.other"
            ),
            "missing source locator": lambda value: value["source"].pop("locator"),
            "unnamed authority kind": lambda value: value["authority"].__setitem__(
                "kind", "user"
            ),
            "blank human name": lambda value: value["authority"].__setitem__("name", " "),
            "unaccepted human decision": lambda value: value["authority"].__setitem__(
                "decision", "rejected"
            ),
            "invalid decision time": lambda value: value["authority"].__setitem__(
                "decidedAt", "today"
            ),
            "decision precedes observation": lambda value: value["authority"].__setitem__(
                "decidedAt", "2026-08-12T02:59:59+08:00"
            ),
            "sub-microsecond decision precedes observation": (
                precede_observation_below_microsecond
            ),
            "unaccepted result": lambda value: value["result"].__setitem__(
                "accepted", False
            ),
        }
        for label, mutate_evidence in mutations.items():
            with self.subTest(label=label):
                evidence = self.evidence_document(validator_kind="missing-validator")
                mutate_evidence(evidence)
                self.write_json("product/evidence/weak.json", evidence)

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O2"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/weak.json"]

                self.mutate("product/acceptance.json", promote)
                report = self.report()
                self.assertFalse(report["criterionStates"]["O2"])
                self.assertFalse(report["criterionStates"]["G2"])
                self.assertIn(
                    "criterion O2 evidence shape is invalid: product/evidence/weak.json",
                    report["errors"],
                )
                self.assertNotIn(
                    "criterion O2 has no code-owned evidence validator: missing-validator",
                    report["errors"],
                )
                self.reset_acceptance_fixture()

    def test_evidence_validator_must_return_literal_true(self) -> None:
        for validator_result in (False, "truthy-but-not-bool"):
            with self.subTest(validator_result=validator_result):
                self.map_outcome_to_latest_work("O1")
                evidence = self.evidence_document(criterion_ids=["O1"])
                self.write_json("product/evidence/bound.json", evidence)

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O1"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/bound.json"]

                self.mutate("product/acceptance.json", promote)
                validator = (
                    lambda document, criterion_id, root, errors: validator_result
                )
                with patch(
                    "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
                    self.validator_registry(validator),
                ):
                    report = self.report()
                self.assertFalse(report["criterionStates"]["O1"])
                self.assertFalse(report["criterionStates"]["G2"])
                self.assertIn(
                    "criterion O1 evidence validator did not return true: product/evidence/bound.json",
                    report["errors"],
                )
                self.reset_program_fixture()
                self.reset_acceptance_fixture()

    def test_evidence_validator_must_bind_the_evidence_increment(self) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(criterion_ids=["O1"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(
                validator,
                increment_ids=frozenset({"increment.other-task"}),
            ),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "criterion O1 evidence validator is not bound to "
            f"increment {FIXTURE_INCREMENT_ID}: test-validator",
            report["errors"],
        )

    def test_evidence_cannot_carry_unbound_criterion_claims(self) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(criterion_ids=["O1", "O2"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "criterion O1 evidence shape is invalid: product/evidence/bound.json",
            report["errors"],
        )

    def test_distinct_evidence_files_cannot_reuse_one_identity(self) -> None:
        self.map_outcome_to_latest_work("O1")
        first = self.evidence_document(criterion_ids=["O1"])
        second = deepcopy(first)
        self.write_json("product/evidence/first.json", first)
        self.write_json("product/evidence/second.json", second)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = [
                "product/evidence/first.json",
                "product/evidence/second.json",
            ]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "duplicate evidence id typed-o2: product/evidence/second.json",
            report["errors"],
        )

    def test_malformed_evidence_fails_without_traceback(self) -> None:
        self.write_json("product/evidence/malformed.json", {"schema": 1})

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O2")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/malformed.json"]

        self.mutate("product/acceptance.json", promote)
        completed = self.run_cli()
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse(json.loads(completed.stdout)["valid"])

    def test_completed_program_without_validated_outcome_binding_is_invalid(self) -> None:
        def close(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            value["status"] = "completed"
            value["activeIncrementId"] = None
            increment["state"] = "completed"
            increment["workItems"][0]["state"] = "completed"

        self.mutate("product/program.json", close)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"]["verified"], 0)
        self.assertIn(
            "closed outcome-neutral increment must leave the current graph: increment.fixture-current",
            report["errors"],
        )

    def test_ready_program_has_no_active_increment_and_remains_in_progress(self) -> None:
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["activeIncrement"], None)
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_v11_cannot_reuse_v10_terminal_state(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("status", "stopped"),
        )
        with patch.multiple(
            control,
            CURRENT_PROFILE_FREEZE_ENABLED=False,
            _normative_profile_binding_history_valid=lambda root, binding, errors: True,
            _v10_historical_authority_valid=lambda root, errors: True,
            _v11_historical_authority_valid=lambda root, errors: True,
        ):
            report = verify_product(self.root)
        self.assertFalse(report["valid"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertIn(
            "stopped current program requires its only cohort to be revoked",
            report["errors"],
        )

    def test_obsolete_paused_program_state_is_rejected(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("status", "paused"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertIn(
            "program status must be active, ready, stopped, or completed",
            report["errors"],
        )

    def test_ready_program_cannot_report_accepted_with_all_outcomes_verified(self) -> None:
        outcome_ids = ["O1", "O2", "O3", "O4", "O5"]

        def map_all_outcomes(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            increment["acceptanceIds"].extend(outcome_ids)
            increment["workItems"][0]["acceptanceIds"].extend(outcome_ids)
            self.bind_fixture_registration(value, increment)

        self.mutate("product/program.json", map_all_outcomes)
        evidence = self.evidence_document(criterion_ids=outcome_ids)
        self.write_json("product/evidence/all-outcomes.json", evidence)

        def promote(value: dict) -> None:
            for criterion in value["criteria"]:
                if criterion["id"] in outcome_ids:
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/all-outcomes.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["programStatus"], "ready")
        self.assertEqual(report["outcomes"]["verified"], 5)
        self.assertEqual(report["completionState"], "in-progress")

    def test_terminal_completion_requires_predeclared_release_candidate(self) -> None:
        self.configure_terminal_candidate(bind_release=False)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertFalse(report["valid"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertFalse(report["criterionStates"]["O5"])
        self.assertIn(
            "terminal completion requires a predeclared release candidate binding",
            report["errors"],
        )

    def test_terminal_authorization_rejects_predecessor_product_scope(self) -> None:
        _, evidence_digest, head = self.configure_terminal_candidate()
        predecessor_scope = [
            "normative-profile",
            "thin-reference-adapters",
            "privacy-disposition",
            "claim-ceiling",
            "candidate-commit",
            "annotated-tag",
            "public-release",
        ]
        self.create_terminal_fixture_tag(
            evidence_digest,
            head,
            accepted_scope=predecessor_scope,
        )
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            self.terminal_authorization_registry(
                lambda annotation, root, errors: True
            ),
        ):
            report = self.report()
        self.assertFalse(report["valid"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertIn(
            "terminal tag annotation authorization is invalid", report["errors"]
        )
        self.assertEqual(
            control.TERMINAL_RELEASE_ANNOTATION_FORMAT,
            "harness-release-authorization-v2",
        )
        self.assertEqual(
            control.EXPECTED_TERMINAL_RELEASE_SCOPE,
            [
                "cross-host-and-cross-operating-system-equivalence",
                "portable-collaboration-semantics",
                "minimum-quality-and-evidence-conformance-contract",
                "adaptive-thin-reference-projections",
                "privacy-disposition",
                "tested-host-operating-system-runtime-and-virtualization-scope",
                "claim-ceiling",
                "candidate-commit",
                "annotated-tag",
                "public-release",
            ],
        )

    def test_terminal_authorization_rejects_public_private_source_locator(self) -> None:
        _, evidence_digest, head = self.configure_terminal_candidate()
        self.create_terminal_fixture_tag(
            evidence_digest,
            head,
            authorization_source={
                "kind": "fixture-trusted-user-event",
                "locator": "C:/Users/private/session.jsonl",
                "identity": "session_private",
                "payloadSha256": "f" * 64,
            },
        )
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            self.terminal_authorization_registry(
                lambda annotation, root, errors: True
            ),
        ):
            report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "terminal tag annotation authorization is invalid", report["errors"]
        )

    def test_terminal_tag_cannot_select_a_different_authorization_validator(self) -> None:
        _, evidence_digest, head = self.configure_terminal_candidate()
        self.create_terminal_fixture_tag(
            evidence_digest,
            head,
            authorization_validator_kind="fixture-weaker-validator",
        )
        validator = lambda document, criterion_id, root, errors: True
        terminal_registry = self.terminal_authorization_registry(
            lambda annotation, root, errors: True
        )
        terminal_registry["fixture-weaker-validator"] = (
            "harness/terminal_authorization_validator_fixture.py",
            lambda annotation, root, errors: True,
        )
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            terminal_registry,
        ):
            report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "terminal tag annotation authorization is invalid", report["errors"]
        )

    def test_terminal_candidate_waits_for_tag_then_accepts_exact_public_identity(
        self,
    ) -> None:
        _, evidence_digest, head = self.configure_terminal_candidate()
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            self.terminal_authorization_registry(
                lambda annotation, root, errors: True
            ),
        ):
            pending = self.report()
        self.assertTrue(pending["valid"], pending["errors"])
        self.assertEqual(pending["completionState"], "in-progress")
        self.assertEqual(
            pending["terminalReleaseState"],
            "candidate-clean-awaiting-authorized-tag",
        )
        self.assertFalse(pending["criterionStates"]["O5"])

        tag_object = self.create_terminal_fixture_tag(evidence_digest, head)
        original = control._evidence_git
        expected_remote_args = (
            "ls-remote",
            "--tags",
            control.EXPECTED_PUBLIC_REMOTE,
            f"refs/tags/{control.CURRENT_RELEASE}.0",
            f"refs/tags/{control.CURRENT_RELEASE}.0^{{}}",
        )

        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            unverified_authorization = self.report()
        self.assertFalse(unverified_authorization["valid"])
        self.assertIn(
            "terminal authorization validator identity is not prebound",
            unverified_authorization["errors"],
        )

        def project_public_tag(
            root: Path, *args: str, **kwargs: object
        ) -> bytes | None:
            if args[:2] == ("ls-remote", "--tags"):
                self.assertEqual(args, expected_remote_args)
                return (
                    f"{tag_object}\trefs/tags/{control.CURRENT_RELEASE}.0\n"
                    f"{head}\trefs/tags/{control.CURRENT_RELEASE}.0^{{}}\n"
                ).encode("ascii")
            return original(root, *args, **kwargs)

        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            self.terminal_authorization_registry(
                lambda annotation, root, errors: True
            ),
        ), patch(
            "harness.control._evidence_git", side_effect=project_public_tag
        ):
            accepted = self.report()
        self.assertTrue(accepted["valid"], accepted["errors"])
        self.assertEqual(accepted["completionState"], "accepted")
        self.assertEqual(accepted["terminalReleaseState"], "published-verified")
        self.assertTrue(accepted["criterionStates"]["O5"])

        def project_mismatched_public_tag(
            root: Path, *args: str, **kwargs: object
        ) -> bytes | None:
            if args[:2] == ("ls-remote", "--tags"):
                self.assertEqual(args, expected_remote_args)
                return (
                    f"{'0' * len(tag_object)}\trefs/tags/{control.CURRENT_RELEASE}.0\n"
                    f"{head}\trefs/tags/{control.CURRENT_RELEASE}.0^{{}}\n"
                ).encode("ascii")
            return original(root, *args, **kwargs)

        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            self.terminal_authorization_registry(
                lambda annotation, root, errors: True
            ),
        ), patch(
            "harness.control._evidence_git",
            side_effect=project_mismatched_public_tag,
        ):
            mismatched = self.report()
        self.assertFalse(mismatched["valid"])
        self.assertEqual(mismatched["completionState"], "in-progress")
        self.assertIn(
            "public terminal tag object or peeled commit does not match locally",
            mismatched["errors"],
        )

    def test_git_ls_remote_requires_both_exact_annotated_tag_patterns(self) -> None:
        head = self.initialize_fixture_repository()
        tag = "v-protocol-check"
        tag_ref = f"refs/tags/{tag}"
        subprocess.run(
            ["git", "tag", "-a", tag, "-m", "protocol check"],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        tag_object = subprocess.run(
            ["git", "rev-parse", tag_ref],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        with tempfile.TemporaryDirectory(dir=self.root.parent) as temporary:
            remote = Path(temporary) / "remote.git"
            subprocess.run(
                ["git", "init", "--bare", "--quiet", str(remote)],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "push", "--quiet", str(remote), tag_ref],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            single = subprocess.run(
                [
                    "git",
                    "-c",
                    "protocol.file.allow=always",
                    "ls-remote",
                    "--tags",
                    str(remote),
                    tag_ref,
                ],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
            paired = subprocess.run(
                [
                    "git",
                    "-c",
                    "protocol.file.allow=always",
                    "ls-remote",
                    "--tags",
                    str(remote),
                    tag_ref,
                    f"{tag_ref}^{{}}",
                ],
                cwd=self.root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
        self.assertEqual(single, f"{tag_object}\t{tag_ref}\n".encode("ascii"))
        self.assertEqual(
            paired,
            (
                f"{tag_object}\t{tag_ref}\n"
                f"{head}\t{tag_ref}^{{}}\n"
            ).encode("ascii"),
        )

    def test_terminal_candidate_rejects_untracked_or_ignored_residue(self) -> None:
        self.configure_terminal_candidate()
        validator = lambda document, criterion_id, root, errors: True
        terminal_registry = self.terminal_authorization_registry(
            lambda annotation, root, errors: True
        )
        extra_file = self.root / "scratch-output"
        extra_file.write_text("residue", encoding="utf-8")
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            terminal_registry,
        ):
            file_report = self.report()
        self.assertFalse(file_report["valid"])
        self.assertIn(
            "terminal release candidate must be a clean checkout with no ignored or untracked residue",
            file_report["errors"],
        )
        extra_file.unlink()

        empty_directory = self.root / "scratch-empty"
        empty_directory.mkdir()
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            terminal_registry,
        ):
            directory_report = self.report()
        self.assertFalse(directory_report["valid"])
        self.assertIn(
            "terminal checkout contains an extra directory: scratch-empty",
            directory_report["errors"],
        )
        empty_directory.rmdir()

        exclude = self.root / ".git/info/exclude"
        exclude.write_text(exclude.read_text(encoding="utf-8") + "ignored-output/\n", encoding="utf-8")
        ignored_directory = self.root / "ignored-output"
        ignored_directory.mkdir()
        (ignored_directory / "payload").write_text("residue", encoding="utf-8")
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ), patch(
            "harness.control.SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS",
            terminal_registry,
        ):
            ignored_report = self.report()
        self.assertFalse(ignored_report["valid"])
        self.assertIn(
            "terminal release candidate must be a clean checkout with no ignored or untracked residue",
            ignored_report["errors"],
        )

    def test_ready_program_cannot_erase_agent_owned_non_outcome_progression(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.pop("progressionPolicy", None),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program progressionPolicy is invalid", report["errors"])

    def test_program_cannot_reclassify_bound_product_delivery_as_missing_demand(self) -> None:
        def erase_product_demand(value: dict) -> None:
            value["progressionPolicy"].pop(
                "boundProductDeliveryDemandDisposition", None
            )

        self.mutate("product/program.json", erase_product_demand)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program progressionPolicy is invalid", report["errors"])

    def test_ready_program_cannot_retain_active_work(self) -> None:
        def invalid(value: dict) -> None:
            self.activate_program(value)
            value["status"] = "ready"

        self.mutate("product/program.json", invalid)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("ready program must have no active increment", report["errors"])
        self.assertIn("ready program must have a terminal increment graph", report["errors"])

    def test_completed_increment_cannot_retain_active_work(self) -> None:
        def invalid(value: dict) -> None:
            increment = self.activate_program(value)
            value["status"] = "completed"
            value["activeIncrementId"] = None
            increment["state"] = "completed"

        self.mutate("product/program.json", invalid)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "active work item work.fixture-current must belong to the active increment",
            report["errors"],
        )
        self.assertIn(
            "terminal increment increment.fixture-current has non-terminal work",
            report["errors"],
        )

    def test_completed_program_still_checks_repository_residue(self) -> None:
        def close(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            value["status"] = "completed"
            value["activeIncrementId"] = None
            increment["state"] = "completed"
            increment["workItems"][0]["state"] = "completed"

        self.mutate("product/program.json", close)
        (self.root / ".tmp").mkdir()
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository cleanup residue remains: .tmp", report["errors"])

    def test_empty_completed_graph_is_invalid(self) -> None:
        def empty(value: dict) -> None:
            value["status"] = "completed"
            value["activeIncrementId"] = None
            value["increments"] = []

        self.mutate("product/program.json", empty)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "only a ready or stopped program may have an empty current increment graph",
            report["errors"],
        )

    def test_increment_requires_non_empty_work_graph(self) -> None:
        def empty(value: dict) -> None:
            self.activate_program(value)["workItems"] = []

        self.mutate("product/program.json", empty)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.fixture-current must contain at least one work item",
            report["errors"],
        )

    def test_unknown_operation_alias_cannot_bypass_human_authority(self) -> None:
        def alias(value: dict) -> None:
            value["authorityBoundary"]["agentOwnsWithinBoundedAuthority"].append("publish")
            self.activate_program(value)["workItems"][0]["operationIds"].append("publish")

        self.mutate("product/program.json", alias)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program agent authority contains an unknown operation", report["errors"])
        self.assertIn(
            "work item work.fixture-current contains an unknown operation",
            report["errors"],
        )

    def test_accountable_outcome_acceptance_is_human_owned(self) -> None:
        def remove(value: dict) -> None:
            value["authorityBoundary"]["userOwns"].remove(
                "accountable-outcome-acceptance"
            )

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program userOwns omits a mandatory human authority", report["errors"])

    def test_capability_guidance_cannot_become_product_authority(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value.pop("capabilityInfluenceBoundary", None),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "constitution capabilityInfluenceBoundary is invalid",
            report["errors"],
        )

    def test_historical_milestone_cannot_become_current_authority(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value["priorRelease"].__setitem__("currentAuthority", True),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "program priorRelease must match the code-owned historical milestone",
            report["errors"],
        )

    def test_historical_milestone_identity_is_code_owned(self) -> None:
        fabricated = {
            "release": "v9.9",
            "state": "accepted-terminal-product",
            "revision": "0123456789abcdef0123456789abcdef01234567",
            "currentAuthority": False,
        }
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("priorRelease", fabricated.copy()),
        )
        self.mutate(
            "product/constitution.json",
            lambda value: value["historicalMilestones"].__setitem__(
                0,
                {**fabricated, "claimLimit": "fabricated but non-empty"},
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "program priorRelease must match the code-owned historical milestone",
            report["errors"],
        )

    def test_historical_milestone_claim_limit_is_code_owned(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value["historicalMilestones"][0].__setitem__(
                "claimLimit", "terminal product and cross-host proof"
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "constitution historical milestones must match the code-owned records",
            report["errors"],
        )

    def test_historical_failure_remains_non_authoritative_counterevidence(self) -> None:
        def erase_counterevidence(value: dict) -> None:
            value["historicalEvidenceBoundary"]["counterevidenceInput"] = False

        self.mutate("product/constitution.json", erase_counterevidence)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "constitution historicalEvidenceBoundary is invalid",
            report["errors"],
        )

    def test_declared_supporting_document_must_exist(self) -> None:
        (self.root / "README.md").unlink()
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("supporting document is missing: README.md", report["errors"])

    def test_supporting_document_set_cannot_silently_shrink(self) -> None:
        def omit_security_policy(value: dict) -> None:
            value["supportingDocuments"].remove("SECURITY.md")

        self.mutate("product/constitution.json", omit_security_policy)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "supportingDocuments must equal the code-owned semantic document set",
            report["errors"],
        )

    def test_supporting_document_set_cannot_silently_expand(self) -> None:
        (self.root / "docs" / "extra-process.md").write_text(
            "# Extra process\n", encoding="utf-8"
        )
        self.mutate(
            "product/constitution.json",
            lambda value: value["supportingDocuments"].append(
                "docs/extra-process.md"
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "supportingDocuments must equal the code-owned semantic document set",
            report["errors"],
        )

    def test_public_status_claims_match_the_v12_environment_attribution_boundary(self) -> None:
        security = (self.root / "SECURITY.md").read_text(encoding="utf-8")
        research = (
            self.root / "docs/strategy/RESEARCH-AND-POC-PLAN.md"
        ).read_text(encoding="utf-8")
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        readme_zh = (self.root / "README.zh-CN.md").read_text(encoding="utf-8")
        self.assertIn("current v1.2 environment-attribution tree", security)
        self.assertNotIn("current v0.2 tree", security)
        self.assertIn("observed-native-minimum", research)
        self.assertIn("user-configured", research)
        self.assertNotIn("At least three materially different accepted tasks", research)
        self.assertIn("terminal product proposition", " ".join(readme.split()))
        live_status = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )["status"]
        self.assertIn(f"programStatus={live_status}", readme)
        self.assertIn("DEMAND-TO-CAPABILITY-PROFILE-V1.1.md", readme)
        self.assertIn("DEMAND-TO-CAPABILITY-PROFILE-V1.2.md", readme)
        self.assertIn("continuous-correction", readme)
        self.assertIn("v1.0", readme)
        self.assertIn("stopped", readme)
        self.assertIn("宪章终极命题尚未成立", readme_zh)
        self.assertIn(f"programStatus={live_status}", readme_zh)
        self.assertIn("DEMAND-TO-CAPABILITY-PROFILE-V1.1.md", readme_zh)
        self.assertIn("DEMAND-TO-CAPABILITY-PROFILE-V1.2.md", readme_zh)
        self.assertIn("持续纠偏", readme_zh)
        self.assertIn("v1.0", readme_zh)
        self.assertIn("停止", readme_zh)
        for document in (readme, research):
            self.assertIn("starting", document.lower())
            self.assertIn("not a static capability ceiling", document)
            self.assertIn("unresolved moving target", document)
            self.assertIn("human-only", document)
        self.assertIn("起始条件", readme_zh)
        self.assertIn("移动目标", readme_zh)
        self.assertIn("只能由人完成", readme_zh)

    def test_hosted_validation_has_finite_ref_scoped_resource_limits(self) -> None:
        workflow = (self.root / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("group: validate-product-${{ github.workflow }}-${{ github.ref }}", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("timeout-minutes: 20", workflow)

    def test_continuation_is_lean_navigation_not_static_authority(self) -> None:
        continuation = (
            self.root / "docs/operations/CONTINUATION.md"
        ).read_text(encoding="utf-8")
        self.assertLess(len(continuation), 8200)
        self.assertIn("navigation aid, not product authority", continuation)
        self.assertIn("This file grants none of those actions", continuation)
        self.assertIn("sourceCarrierRelease", continuation)
        self.assertIn("sourceCarrierRelease.allowed=true", continuation)
        self.assertNotIn("The current task grants no authority", continuation)
        self.assertNotIn("Historical v0.2 accepted O5 basis", continuation)
        self.assertNotIn("45 native compactions", continuation)

    def test_empty_supporting_document_is_rejected(self) -> None:
        (self.root / "README.md").write_text("\n", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("supporting document is empty: README.md", report["errors"])

    def test_supporting_document_byte_limit_fails_closed(self) -> None:
        (self.root / "README.md").write_text(
            "x" * (control.MAX_DOCUMENT_BYTES + 1), encoding="utf-8"
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "cannot read supporting document README.md: byte limit exceeded",
            report["errors"],
        )

    def test_undeclared_product_root_json_is_rejected(self) -> None:
        self.write_json("product/extra.json", {"schema": 1})
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("undeclared product authority JSON: product/extra.json", report["errors"])

    def test_product_authority_enumeration_error_fails_closed(self) -> None:
        real_scandir = os.scandir

        def unreadable_product(path):
            if Path(path).name == "product":
                raise PermissionError("fixture access denied")
            return real_scandir(path)

        with patch("harness.control.os.scandir", side_effect=unreadable_product):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("product authority root cannot be enumerated", report["errors"])

    def test_parent_authority_symlink_is_rejected(self) -> None:
        product = self.root / "product"
        real = self.root / "product-real"
        product.rename(real)
        try:
            product.symlink_to(real, target_is_directory=True)
        except OSError as exc:
            real.rename(product)
            self.skipTest(f"directory symlink unavailable: {exc}")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertTrue(
            any("cannot traverse a link or reparse point" in item for item in report["errors"]),
            report["errors"],
        )

    def test_unicode_escaped_predecessor_identity_is_rejected_semantically(self) -> None:
        value = self.read_json("product/program.json")
        value["purpose"] = "agent" + "-skills" + "-curated"
        serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        serialized = serialized.replace(
            "agent-skills-curated", "agent\\u002dskills\\u002dcurated"
        )
        (self.root / "product/program.json").write_text(serialized, encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "forbidden predecessor semantic identity in active authority: product/program.json",
            report["errors"],
        )

    def test_evidence_criterion_ids_must_be_a_unique_string_list(self) -> None:
        self.map_outcome_to_latest_work("O2")
        for malformed in (123, {"O2": True}, "O2", ["O2", "O2"]):
            with self.subTest(malformed=malformed):
                evidence = self.evidence_document(criterion_ids=malformed)
                self.write_json("product/evidence/typed.json", evidence)

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O2"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/typed.json"]

                self.mutate("product/acceptance.json", promote)
                completed = self.run_cli()
                self.assertNotEqual(completed.returncode, 0)
                self.assertNotIn("Traceback", completed.stderr)
                report = json.loads(completed.stdout)
                self.assertFalse(report["valid"])
                self.assertIn(
                    "criterion O2 evidence shape is invalid: product/evidence/typed.json",
                    report["errors"],
                )
                self.reset_acceptance_fixture()

    def test_evidence_locator_must_be_canonical_and_non_nested(self) -> None:
        for relative in (
            "product/Evidence/typed.json",
            "product/evidence/nested/typed.json",
        ):
            with self.subTest(relative=relative):
                self.write_json(relative, {"schema": 1})

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O2"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = [relative]

                self.mutate("product/acceptance.json", promote)
                report = self.report()
                self.assertFalse(report["valid"])
                self.assertIn(
                    f"criterion O2 has invalid evidence locator: '{relative}'",
                    report["errors"],
                )
                self.reset_acceptance_fixture()

if __name__ == "__main__":
    unittest.main()
