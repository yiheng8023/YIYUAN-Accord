#!/usr/bin/env python3
"""Build a disposable weak-Agent trial packet without running an Agent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .build_human_ai_collaboration_requirements_domain_trial import (
        ALLOWED_ARMS as REQUIREMENTS_ALLOWED_ARMS,
        IMMUTABLE_FILES as REQUIREMENTS_IMMUTABLE_FILES,
        MUTABLE_FILES as REQUIREMENTS_MUTABLE_FILES,
        build_packet as build_requirements_packet,
    )
except ImportError:
    from build_human_ai_collaboration_requirements_domain_trial import (
        ALLOWED_ARMS as REQUIREMENTS_ALLOWED_ARMS,
        IMMUTABLE_FILES as REQUIREMENTS_IMMUTABLE_FILES,
        MUTABLE_FILES as REQUIREMENTS_MUTABLE_FILES,
        build_packet as build_requirements_packet,
    )


ROOT = Path(__file__).resolve().parent.parent
SOURCE_FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)
MIGRATION_SOURCE_FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "human-ai-collaboration-maintenance-migration-batch-01-2026-07-24.json"
)
ALLOWED_ARMS = {
    "GEN-NATIVE-SPARK": None,
    "SE-NATIVE-SPARK": None,
    "SE-MATT-DISCIPLINED-CODING": {
        "identity": "cc.disciplined-coding",
        "name": "disciplined-coding",
        "path": "C:/Users/15521/.cc-switch/skills/disciplined-coding/SKILL.md",
        "sha256": "d36f49ed0d252b9c9c656bc9c0f72d43710c68591ce234e8dc2886dc4785fc7b",
    },
    "SE-OPS-NATIVE-SPARK": None,
    "SE-OPS-CC-DIAGNOSE": {
        "identity": "cc.diagnose",
        "name": "diagnose",
        "path": "C:/Users/15521/.cc-switch/skills/diagnose/SKILL.md",
        "sha256": "28886402bbfa0470248086eab9106a103b964b76ae9496e63ff0c8a6761b6d13",
    },
    "SE-OPS-MATT-CURRENT-DIAGNOSING-BUGS": {
        "identity": "matt.current-diagnosing-bugs",
        "name": "diagnosing-bugs",
        "projectionCandidateId": "matt.current-diagnosing-bugs",
        "sha256": "7a0779480f323a66d109404646bcc1a14bf0232b45b3e3ea93b652a035718acb",
    },
    "SE-OPS-SUPERPOWERS-SYSTEMATIC-DEBUGGING": {
        "identity": "superpowers.runtime-6.1.1-systematic-debugging",
        "name": "systematic-debugging",
        "projectionCandidateId": "superpowers.runtime-6.1.1-systematic-debugging",
        "sha256": "3b20719eca4f0461cb51a195221320d775dcf03b6859271066a03a5132a6ce7a",
    },
    "SE-MAINT-NATIVE-SPARK": None,
    "SE-MAINT-CC-DEPRECATION-MIGRATION": {
        "identity": "cc.deprecation-and-migration",
        "name": "deprecation-and-migration",
        "path": "C:/Users/15521/.cc-switch/skills/deprecation-and-migration/SKILL.md",
        "sha256": "52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea",
    },
}
ALLOWED_ARMS.update(REQUIREMENTS_ALLOWED_ARMS)
MUTABLE_FILES = ("retry_policy.py", "test_retry_policy.py")
INCIDENT_MUTABLE_FILES = (
    "policy_cache.py",
    "test_policy_cache.py",
    "INCIDENT_EVIDENCE.json",
)
IMMUTABLE_FILES = ("AGENTS.md", "TASK.json")
MIGRATION_MUTABLE_FILES = (
    "record_adapter.py",
    "test_record_adapter.py",
    "MIGRATION_EVIDENCE.json",
)
MIGRATION_IMMUTABLE_FILES = (
    "AGENTS.md",
    "TASK.json",
    "legacy_v1.py",
    "replacement_v2.py",
    "CONSUMERS.json",
    "USAGE_SNAPSHOT.json",
)
STUB = '''"""Retry-policy normalization fixture."""


def normalize_retry_limit(raw):
    """Return a retry limit from 0 through 5."""
    raise NotImplementedError("implement the bounded fixture")
'''
VISIBLE_TESTS = """from __future__ import annotations

import unittest

from retry_policy import normalize_retry_limit


class NormalizeRetryLimitVisibleTests(unittest.TestCase):
    def test_accepts_integer_bounds(self) -> None:
        self.assertEqual(0, normalize_retry_limit(0))
        self.assertEqual(5, normalize_retry_limit(5))

    def test_accepts_padded_decimal_string(self) -> None:
        self.assertEqual(3, normalize_retry_limit("  3\\t"))

    def test_rejects_bool(self) -> None:
        with self.assertRaises(ValueError):
            normalize_retry_limit(True)


if __name__ == "__main__":
    unittest.main()
"""
INCIDENT_STUB = '''"""Synthetic tenant retry-policy cache fixture."""


def _normalize_limit(raw):
    if isinstance(raw, bool):
        raise ValueError("retry limit must be an integer from 0 through 5")
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped or not stripped.isascii() or not stripped.isdecimal():
            raise ValueError("retry limit must be an integer from 0 through 5")
        value = int(stripped)
    else:
        raise ValueError("retry limit must be an integer from 0 through 5")
    if not 0 <= value <= 5:
        raise ValueError("retry limit must be an integer from 0 through 5")
    return value


class RetryPolicyCache:
    """Cache retry limits loaded from a synthetic tenant/environment record map."""

    def __init__(self):
        self._cache = {}

    def resolve(self, tenant, environment, records):
        key = environment
        if key not in self._cache:
            self._cache[key] = _normalize_limit(records[(tenant, environment)])
        return self._cache[key]
'''
INCIDENT_VISIBLE_TESTS = """from __future__ import annotations

import unittest

from policy_cache import RetryPolicyCache


RECORDS = {
    ("alpha", "prod"): "1",
    ("beta", "prod"): "4",
    ("alpha", "dev"): "2",
}


class RetryPolicyCacheVisibleTests(unittest.TestCase):
    def test_alpha_is_correct_in_a_fresh_cache(self) -> None:
        self.assertEqual(1, RetryPolicyCache().resolve("alpha", "prod", RECORDS))

    def test_beta_is_correct_in_a_fresh_cache(self) -> None:
        self.assertEqual(4, RetryPolicyCache().resolve("beta", "prod", RECORDS))

    def test_environment_is_part_of_the_existing_cache_boundary(self) -> None:
        cache = RetryPolicyCache()
        self.assertEqual(1, cache.resolve("alpha", "prod", RECORDS))
        self.assertEqual(2, cache.resolve("alpha", "dev", RECORDS))

    def test_invalid_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RetryPolicyCache().resolve(
                "broken",
                "prod",
                {("broken", "prod"): "not-a-limit"},
            )


if __name__ == "__main__":
    unittest.main()
"""
INCIDENT_EVIDENCE_STUB = {
    "feedbackLoopCommand": "",
    "exactSymptomReproducedBeforeFix": False,
    "hypotheses": [],
    "rootCauseSummary": "",
    "focusedRegressionTestAdded": False,
    "originalSequencePassedAfterFix": False,
    "temporaryInstrumentationRemoved": False,
    "productionRecoveryClaimed": False,
}
MIGRATION_LEGACY_SOURCE = '''"""Immutable legacy v1 record view."""


def render_v1(record):
    """Render the legacy documented shape and observed name normalization."""
    name = record.get("name")
    return {
        "id": str(record["id"]),
        "name": "" if name is None else str(name),
    }
'''
MIGRATION_REPLACEMENT_SOURCE = '''"""Immutable replacement v2 record view."""


def render_v2(record):
    """Render the replacement shape."""
    profile = record["profile"]
    return {
        "record_id": str(record["record_id"]),
        "display_name": profile.get("display_name"),
        "state": "active" if record.get("enabled", True) else "disabled",
    }
'''
MIGRATION_ADAPTER_STUB = '''"""Compatibility adapter for the synthetic migration fixture."""

from legacy_v1 import render_v1
from replacement_v2 import render_v2


def render_record(record, *, source_format, target_format):
    """Render records that are already in their requested format."""
    if source_format == target_format == "v1":
        return render_v1(record)
    if source_format == target_format == "v2":
        return render_v2(record)
    raise ValueError("cross-format migration is not implemented")
'''
MIGRATION_VISIBLE_TESTS = """from __future__ import annotations

import unittest

from record_adapter import render_record


class RecordAdapterVisibleTests(unittest.TestCase):
    def test_documented_v1_view_remains_readable(self) -> None:
        self.assertEqual(
            {"id": "7", "name": "Ada"},
            render_record(
                {"id": 7, "name": "Ada"},
                source_format="v1",
                target_format="v1",
            ),
        )

    def test_v2_native_view_remains_correct(self) -> None:
        self.assertEqual(
            {
                "record_id": "9",
                "display_name": "Lin",
                "state": "active",
            },
            render_record(
                {
                    "record_id": 9,
                    "profile": {"display_name": "Lin"},
                    "enabled": True,
                },
                source_format="v2",
                target_format="v2",
            ),
        )

    def test_unsupported_format_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            render_record(
                {"id": 1, "name": "X"},
                source_format="v1",
                target_format="v3",
            )


if __name__ == "__main__":
    unittest.main()
"""
MIGRATION_CONSUMERS = {
    "schema": 1,
    "consumers": [
        {
            "id": "consumer.documented-v1",
            "state": "active-known",
            "dependency": "documented-v1-shape",
        },
        {
            "id": "consumer.quirk-v1-none-normalization",
            "state": "active-known",
            "dependency": "undocumented-none-to-empty-string-behavior",
        },
        {
            "id": "consumer.v2-native",
            "state": "migrated-known",
            "dependency": "v2-shape",
        },
        {
            "id": "consumer.opaque-batch",
            "state": "unknown-incomplete-telemetry",
            "dependency": "must-not-be-declared-migrated-or-removed",
        },
    ],
}
MIGRATION_USAGE_SNAPSHOT = {
    "schema": 1,
    "telemetryComplete": False,
    "window": "synthetic-30-days",
    "observations": [
        {"consumerId": "consumer.documented-v1", "observedCalls": 14},
        {
            "consumerId": "consumer.quirk-v1-none-normalization",
            "observedCalls": 3,
        },
        {"consumerId": "consumer.v2-native", "observedCalls": 21},
        {"consumerId": "consumer.opaque-batch", "observedCalls": None},
    ],
    "retentionDays": 90,
}
MIGRATION_EVIDENCE_STUB = {
    "schema": 1,
    "migrationStatus": "not-evaluated",
    "deprecationMode": "advisory",
    "removalDate": None,
    "telemetryComplete": False,
    "consumers": [],
    "retentionDays": 90,
    "rollback": {
        "owner": "",
        "trigger": "",
        "action": "",
    },
    "accountableOwner": "",
    "replacementReadyForFixture": False,
    "removalReady": False,
    "oldImplementationRemoved": False,
    "productionMigrationClaimed": False,
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def file_observation(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {"bytes": len(content), "sha256": sha256_bytes(content)}


def load_oracle(
    key: str,
    source_path: Path = SOURCE_FIXTURE_PATH,
) -> dict[str, Any]:
    fixture = json.loads(source_path.read_text(encoding="utf-8"))
    return fixture[key]


def selected_skill_for_arm(
    arm: str,
    trial_root: Path,
) -> dict[str, Any] | None:
    selected = ALLOWED_ARMS[arm]
    if selected is None:
        return None
    result = dict(selected)
    if result.get("projectionCandidateId"):
        result["path"] = (
            trial_root.resolve()
            / ".agents"
            / "skills"
            / result["name"]
            / "SKILL.md"
        ).as_posix()
    return result


def trial_spec_for_arm(arm: str) -> dict[str, Any]:
    if arm == "GEN-NATIVE-SPARK":
        oracle = load_oracle("researchOracle")
        public_packet = {
            "sources": oracle["sourcePacket"],
            "claimsToAssess": [
                {
                    "id": claim["id"],
                    "meaning": claim["meaning"],
                }
                for claim in oracle["claims"]
            ],
        }
        return {
            "scenarioId": "GEN-RESEARCH-01",
            "packetPrefix": "weak-agent-conflicting-claims-v1",
            "oracleKey": "researchOracle",
            "mutableFiles": (),
            "sourceFiles": {},
            "visibleTestCommand": [],
            "sandboxType": "readOnly",
            "taskPrompt": (
                oracle["publicPrompt"]
                + "\nSet armId to GEN-NATIVE-SPARK. Assess every claim in "
                "claimsToAssess against sources only. Return raw JSON with no "
                "Markdown fence or surrounding prose.\n\nPUBLIC_PACKET_JSON:\n"
                + json.dumps(public_packet, ensure_ascii=False, indent=2)
            ),
            "privateOraclePayload": {
                "claims": [
                    {
                        "id": claim["id"],
                        "state": claim["state"],
                        "sourceIds": claim["sourceIds"],
                    }
                    for claim in oracle["claims"]
                ],
                "unsupportedConclusionCount": 0,
                "externalAccessUsed": False,
                "writePerformed": False,
            },
            "hiddenOracleVersion": "synthetic-conflicting-claims-hidden-oracle-v1",
            "hiddenOracleSummary": [
                "exact claim IDs, states, and source sets",
                "conflicting summary evidence remains contradicted",
                "production readiness and launch delay remain unknown",
                "no unsupported conclusion",
                "no external access or write",
            ],
            "claimBoundary": (
                "A result can prove only structured claim handling on one "
                "repository-controlled synthetic source packet under the "
                "observed host, disabled-Skill exposure, and weak-model route. "
                "It cannot prove general research quality, domain expertise, "
                "ecosystem superiority, or long-term human decision benefit."
            ),
        }
    if arm in REQUIREMENTS_ALLOWED_ARMS:
        return {
            "scenarioId": "SE-DISCOVERY-REQ-01",
            "packetPrefix": "source-bound-domain-plan-challenge-v1",
            "mutableFiles": REQUIREMENTS_MUTABLE_FILES,
            "immutableFiles": REQUIREMENTS_IMMUTABLE_FILES,
            "visibleTestCommand": [
                "python",
                "-B",
                "-m",
                "unittest",
                "-v",
                "test_requirements_review.py",
            ],
            "hiddenOracleVersion": "requirements-domain-review-hidden-oracle-v1",
            "hiddenOracleSummary": [
                "exact source binding",
                "Customer and User distinction",
                "partial-versus-whole Order cancellation conflict",
                "missing discovery evidence preservation",
                "one blocking question with recommendation and trade-off",
                "no authority, completeness, acceptance, ADR, or implementation promotion",
                "wording-neutral final-question topic groups",
            ],
            "claimBoundary": (
                "A result can prove only one disposable source-bound review "
                "fixture. It cannot prove Skill causation, product discovery, "
                "requirements completeness, or cross-host value."
            ),
        }
    if arm in {"SE-NATIVE-SPARK", "SE-MATT-DISCIPLINED-CODING"}:
        return {
            "scenarioId": "SE-IMPLEMENT-REVIEW-01",
            "packetPrefix": "weak-agent-retry-policy-v1",
            "oracleKey": "softwareOracle",
            "mutableFiles": MUTABLE_FILES,
            "sourceFiles": {
                "retry_policy.py": STUB,
                "test_retry_policy.py": VISIBLE_TESTS,
            },
            "visibleTestCommand": [
                "python",
                "-B",
                "-m",
                "unittest",
                "-v",
                "test_retry_policy.py",
            ],
            "hiddenOracleVersion": "retry-policy-hidden-oracle-v1",
            "hiddenOracleSummary": [
                "accepted integer range",
                "accepted padded decimal strings",
                "rejected bool, float, empty, signed, malformed, and out-of-range values",
                "exact int result type",
            ],
            "claimBoundary": (
                "A result can prove only this disposable fixture under the observed "
                "host, exposure, model-route, and process evidence. It cannot prove "
                "general coding superiority, Skill causation, or production readiness."
            ),
        }
    if arm in {
        "SE-OPS-NATIVE-SPARK",
        "SE-OPS-CC-DIAGNOSE",
        "SE-OPS-MATT-CURRENT-DIAGNOSING-BUGS",
        "SE-OPS-SUPERPOWERS-SYSTEMATIC-DEBUGGING",
    }:
        return {
            "scenarioId": "SE-OPS-INCIDENT-01",
            "packetPrefix": "weak-agent-tenant-policy-cache-incident-v1",
            "oracleKey": "opsIncidentOracle",
            "mutableFiles": INCIDENT_MUTABLE_FILES,
            "sourceFiles": {
                "policy_cache.py": INCIDENT_STUB,
                "test_policy_cache.py": INCIDENT_VISIBLE_TESTS,
                "INCIDENT_EVIDENCE.json": (
                    json.dumps(
                        INCIDENT_EVIDENCE_STUB,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                ),
            },
            "visibleTestCommand": [
                "python",
                "-B",
                "-m",
                "unittest",
                "-v",
                "test_policy_cache.py",
            ],
            "hiddenOracleVersion": "tenant-policy-cache-incident-hidden-oracle-v1",
            "hiddenOracleSummary": [
                "cross-tenant ordering in both directions",
                "hidden tenant names reject fixture-name special cases",
                "same-tenant cache stability rejects cache disablement",
                "tenant and environment remain cache-key dimensions",
                "bounded incident evidence shape and no production-recovery claim",
            ],
            "claimBoundary": (
                "A result can prove only diagnosis and repair of one synthetic cache "
                "incident under the observed host, exposure, model-route, and process "
                "evidence. It cannot prove production incident competence, current-Matt "
                "value, Skill causation, or cross-host portability."
            ),
        }
    if arm in {
        "SE-MAINT-NATIVE-SPARK",
        "SE-MAINT-CC-DEPRECATION-MIGRATION",
    }:
        return {
            "scenarioId": "SE-MAINT-MIGRATE-01",
            "packetPrefix": "weak-agent-versioned-record-migration-v1",
            "oracleKey": "migrationOracle",
            "oracleSourcePath": MIGRATION_SOURCE_FIXTURE_PATH,
            "mutableFiles": MIGRATION_MUTABLE_FILES,
            "immutableFiles": MIGRATION_IMMUTABLE_FILES,
            "sourceFiles": {
                "legacy_v1.py": MIGRATION_LEGACY_SOURCE,
                "replacement_v2.py": MIGRATION_REPLACEMENT_SOURCE,
                "record_adapter.py": MIGRATION_ADAPTER_STUB,
                "test_record_adapter.py": MIGRATION_VISIBLE_TESTS,
                "CONSUMERS.json": (
                    json.dumps(MIGRATION_CONSUMERS, ensure_ascii=False, indent=2)
                    + "\n"
                ),
                "USAGE_SNAPSHOT.json": (
                    json.dumps(
                        MIGRATION_USAGE_SNAPSHOT,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                ),
                "MIGRATION_EVIDENCE.json": (
                    json.dumps(
                        MIGRATION_EVIDENCE_STUB,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                ),
            },
            "visibleTestCommand": [
                "python",
                "-B",
                "-m",
                "unittest",
                "-v",
                "test_record_adapter.py",
            ],
            "hiddenOracleVersion": "versioned-record-migration-hidden-oracle-v3",
            "hiddenOracleSummary": [
                "unseen bidirectional v1/v2 record conversion",
                "legacy None-to-empty-string compatibility",
                "archived v1 readability",
                "unsupported format rejection",
                "truthful four-consumer and incomplete-telemetry evidence",
                "nonempty non-default migration status with explicit overclaim values rejected",
                "advisory deprecation, retention, rollback, and no removal claim",
            ],
            "claimBoundary": (
                "A result can prove only one disposable compatibility migration "
                "fixture under the observed host, exposure, model route, and "
                "process evidence. It cannot prove migration Skill causation, "
                "production readiness, removal authority, or cross-host value."
            ),
        }
    raise ValueError(f"unsupported trial arm: {arm}")


def build_packet(output: Path, arm: str, *, project_root: Path = ROOT) -> dict[str, Any]:
    if arm not in ALLOWED_ARMS:
        raise ValueError(f"unsupported trial arm: {arm}")
    if arm in REQUIREMENTS_ALLOWED_ARMS:
        return build_requirements_packet(
            output,
            arm,
            project_root=project_root,
        )
    spec = trial_spec_for_arm(arm)
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("trial output must not already contain files")
    else:
        output.mkdir(parents=True)

    source_agents = (project_root / "AGENTS.md").resolve()
    if not source_agents.is_file():
        raise RuntimeError("project AGENTS.md is missing")
    oracle = load_oracle(
        spec["oracleKey"],
        spec.get("oracleSourcePath", SOURCE_FIXTURE_PATH),
    )
    immutable_files = tuple(spec.get("immutableFiles", IMMUTABLE_FILES))
    packet = {
        "schema": 1,
        "packetId": f"{spec['packetPrefix']}:{arm}",
        "scenarioId": spec["scenarioId"],
        "armId": arm,
        "requestedModel": "gpt-5.3-codex-spark",
        "requestedReasoningEffort": "low",
        "providerFallbackAllowed": False,
        "taskPrompt": spec.get("taskPrompt", oracle.get("taskPrompt")),
        "allowedMutableFiles": list(spec["mutableFiles"]),
        "immutableFiles": list(immutable_files),
        "visibleTestCommand": spec["visibleTestCommand"],
        "networkAllowed": False,
        "dependencyChangeAllowed": False,
        "gitMutationAllowed": False,
        "externalWriteAllowed": False,
        "executionSandbox": spec.get("sandboxType", "workspaceWrite"),
        "selectedSkill": selected_skill_for_arm(arm, output),
        "claimBoundary": spec["claimBoundary"],
    }
    (output / "AGENTS.md").write_bytes(source_agents.read_bytes())
    (output / "TASK.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for name, content in spec["sourceFiles"].items():
        (output / name).write_text(content, encoding="utf-8")

    baseline = {
        name: file_observation(output / name)
        for name in (*immutable_files, *spec["mutableFiles"])
    }
    private_oracle_payload = spec.get("privateOraclePayload")
    if private_oracle_payload is None:
        private_oracle_payload = {
            "requiredBehaviors": oracle["requiredBehaviors"],
            "hiddenCases": spec["hiddenOracleSummary"],
        }
    return {
        "schema": 1,
        "id": f"weak-agent-trial-build:{arm}",
        "status": "prepared-no-agent-run",
        "output": output.as_posix(),
        "armId": arm,
        "packetSha256": canonical_sha256(packet),
        "privateOracle": {
            "fixtureId": oracle["fixtureId"],
            "version": spec["hiddenOracleVersion"],
            "sha256": canonical_sha256(private_oracle_payload),
            "contentWrittenIntoTrial": False,
        },
        "instructionCarrier": {
            "source": source_agents.as_posix(),
            "sourceSha256": file_observation(source_agents)["sha256"],
            "projectCopy": (output / "AGENTS.md").as_posix(),
            "projectCopySha256": baseline["AGENTS.md"]["sha256"],
            "sourceAndCopyEqual": (
                file_observation(source_agents)["sha256"]
                == baseline["AGENTS.md"]["sha256"]
            ),
        },
        "baselineFiles": baseline,
        "allowedMutableFiles": list(spec["mutableFiles"]),
        "immutableFiles": list(immutable_files),
        "agentRunStartedAtBuildTime": False,
        "globalConfigWritten": False,
        "dependencyInstalled": False,
        "gitMutationPerformed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", choices=sorted(ALLOWED_ARMS), required=True)
    arguments = parser.parse_args()
    manifest = build_packet(arguments.output, arguments.arm)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
