"""Historical-event-neutral product-contract verification for the Harness.

The verifier enforces current authority shape, causal-program invariants,
evidence admission, human authority, and bounded process loss. The constitution,
program, and acceptance contract remain product authority. Historical release
event validators live at their accepted Git revisions; they are not carried
forward as current product authority.
"""

from __future__ import annotations

import base64
from contextvars import ContextVar
import ctypes
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
from io import BytesIO
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from threading import Timer
from types import MappingProxyType
from typing import Any, Callable, Mapping
import xml.etree.ElementTree as ET


PRODUCT_ID = "agent-autonomy-harness"
CONSTITUTION_ID = "harness-product-constitution-v1"
CURRENT_RELEASE = "v1.2"
COMPLETION_EXPRESSION = "O1 && O2 && O3 && O4 && O5"
EXPECTED_PRODUCT_PURPOSE = (
    "Provide an open, Agent-neutral, demand-driven human-Agent collaboration quality "
    "harness that transfers capability observation, discovery, selection, bounded setup "
    "and task-scoped dispatch, task-topology selection and reconciliation, "
    "context-carrier fitness and transition, recovery, verification, release, and cleanup burden from "
    "the user to the Agent while preserving human authority over goals, domain judgment, "
    "trust, cost, and irreversible effects."
)
EXPECTED_SUCCESS_DEFINITION = (
    "Across repeated real tasks entered at the goal level, a user can provide ideas, "
    "domain facts, bounded authorization, corrections, any technically or authoritatively "
    "unavoidable human-only action under exact Agent guidance, and accountable final judgment "
    "without needing to discover, select, invoke, or manage the underlying Agent, capability "
    "ecosystem, code and conversation topology, or context lifecycle; the Agent observes available capability "
    "and conversation-carrier fitness, discovers beyond its current view only for an evidenced gap, dispatches the smallest "
    "sufficient route and task carrier, performs every supported authorized mechanic, guides and verifies "
    "any unavoidable human-only step, transitions before preventable context loss, and returns accepted outcomes with fewer material orchestration interventions "
    "than an ad-hoc path."
)
EXPECTED_PROGRAM_PURPOSE = (
    "Prove the constitution's terminal product proposition through a pre-response-enrollment-"
    "controlled, environment-attributed finite repeated-natural-task cohort: sustained goal-level "
    "delivery, lower user orchestration burden than same-starting-environment source-bound ad-hoc "
    "baselines, real demand-driven capability and carrier lifecycles, and live cross-host and cross-"
    "operating-system open reference delivery. v0.2 remains an immutable bounded calibration "
    "milestone, while v1.0 and v1.1 remain immutable stopped zero-outcome attempts; none can "
    "satisfy this program by inheritance."
)
EXPECTED_PROGRESS_RULE = (
    "Only accepted real-task outcomes O1-O5 in a currently valid authority graph with G1-G4 passing count "
    "as progress. Every O1-O5 registration binds the acceptance-owned environment contract, one committed "
    "task-relevant starting manifest and authority-and-available-source envelope, one environment class and "
    "treatment arm, the exact Harness activation delta if present, and one privacy-safe pre-response source-"
    "capture resolution. Each task-host unit runs once in its pre-registered arm; O5 cross-host execution is "
    "required portability replication, not a same-host replay, and Harness-specific value claims remain no "
    "stronger than prospective same-environment matched observational evidence. Observed-native-minimum and "
    "user-configured are starting conditions rather than static capability ceilings: after demand, the Agent "
    "may adapt capabilities, configuration, models, providers and online or local execution only through "
    "current source resolution, minimum-sufficient routing, bounded authority, attributed lifecycle deltas, "
    "verification, rollback and cleanup. Before any task measurement, a new content-addressed profile and "
    "cohort protocol must be frozen and independently source-authorized under the current environment contract. "
    "Before model processing, every submitted source event on the active enrollment surface must receive a "
    "privacy-safe private capture and a pending resolution identity; before outcome-bearing execution or "
    "completion, that event must resolve to an immutable eligible-task registration or a narrow source-bound "
    "exclusion. Missing capture, unresolved eligibility, user-visible outcome text before the host completion "
    "barrier, uncontained hosted-tool bypass, late registration or omitted earlier demand stops the affected "
    "cohort rather than becoming a retrospective exclusion. The realized cohort is the earliest eligible "
    "natural-demand prefix, failures remain in place, public identities are unlinkable random identifiers, and "
    "source validators privately prove complete windows, chronology, deduplication, environment identity and "
    "criterion semantics. v1.0 and v1.1 profile, cohort, authorization, registration, outcome and ordering state "
    "are immutable stopped history and cannot be reused. Even after O1-O5 evidence passes, completionState "
    "remains in-progress until the code-owned terminal release gate verifies the clean exact candidate, "
    "predeclared O5 evidence set, named-human authorization, identical public annotated tag object and peeled "
    "commit, and empty ignored and untracked residue. Documents, tests, inventories, fixtures, research volume, "
    "prior-release evidence and environment manifests remain supporting inputs only."
)
OUTCOME_IDS = {"O1", "O2", "O3", "O4", "O5"}
GUARDRAIL_IDS = {"G1", "G2", "G3", "G4"}
EXPECTED_CRITERION_IDS = OUTCOME_IDS | GUARDRAIL_IDS
CRITERION_BASE_FIELDS = {
    "id",
    "class",
    "name",
    "statement",
    "metric",
    "threshold",
    "assessment",
}
AUTHORITY_TOP_LEVEL_FIELDS = MappingProxyType(
    {
        "constitution": frozenset(
            {
                "schema",
                "id",
                "productId",
                "purpose",
                "successDefinition",
                "productForm",
                "collaborationModel",
                "capabilityInfluenceBoundary",
                "fixedInvariants",
                "adaptiveSurfaces",
                "planningModel",
                "requiredAuthorityFiles",
                "activeAuthorityGlobs",
                "supportingDocuments",
                "historicalMilestones",
                "bootstrapGuards",
                "historicalEvidenceBoundary",
            }
        ),
        "program": frozenset(
            {
                "schema",
                "id",
                "productId",
                "release",
                "purpose",
                "constitution",
                "acceptance",
                "status",
                "activeIncrementId",
                "progressionPolicy",
                "priorRelease",
                "normativeProfileBinding",
                "terminalReleaseBinding",
                "authorityBoundary",
                "completionExpression",
                "increments",
            }
        ),
        "acceptance": frozenset(
            {
                "schema",
                "id",
                "productId",
                "release",
                "program",
                "completionExpression",
                "progressRule",
                "environmentAttribution",
                "criteria",
            }
        ),
    }
)
OUTCOME_OPERATIONALIZATION_FIELDS = {
    "sampleUnit",
    "minimumSampleCount",
    "comparisonDesign",
    "preRegistrationFields",
    "requiredMeasures",
    "passRule",
    "falsifiers",
    "humanAuthority",
}
OUTCOME_OPERATIONALIZATION_BASELINES = MappingProxyType(
    {
        "O1": (6, "finite-stratified-natural-task-cohort"),
        "O2": (6, "same-cohort-source-bound-ad-hoc-baselines"),
        "O3": (4, "real-task-route-lifecycle-cohort"),
        "O4": (4, "predeclared-carrier-fitness-and-transition-cohort"),
        "O5": (
            2,
            "same-task-live-matched-cross-host-pairs-with-bounded-cross-operating-system-coverage",
        ),
    }
)
CRITERION_CONTRACT_BASE_FIELDS = CRITERION_BASE_FIELDS - {"assessment"}
EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256 = (
    "cba7bdcf44c9e10b46665a153c8b9cfde4fa19c12356ab9c5a2d0a9c5440b292"
)
BOOTSTRAP_REQUIRED_AUTHORITY = {
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/control.py",
}
EXPECTED_AUTHORITY_GLOBS = {"harness/*.py"}
EXPECTED_REQUIRED_SUPPORTING_DOCUMENTS = frozenset(
    {
        "README.md",
        "README.zh-CN.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "SUPPORT.md",
        "SUPPORT.zh-CN.md",
        "docs/DEMAND-TO-CAPABILITY-PROFILE.md",
        "docs/architecture.md",
        "docs/strategy/PRODUCT-NORTH-STAR.md",
        "docs/strategy/RESEARCH-AND-POC-PLAN.md",
        "docs/operations/CONTINUATION.md",
        "docs/operations/HISTORY.md",
    }
)
EXCLUDED_AUTHORITY_PARTS = {
    ".git",
    ".tmp",
    "__pycache__",
    "evidence",
    "legacy",
    "fixtures",
}
REQUIRED_USER_AUTHORITY = {
    "product-direction",
    "domain-judgment",
    "new-trust",
    "new-account-or-data-boundary",
    "new-cost",
    "capability-installation-authorization",
    "account-connection-authorization",
    "persistent-activation-authorization",
    "publication-authorization",
    "release-authorization",
    "accountable-outcome-acceptance",
    "destructive-or-irreversible-action",
}
AUTHORITY_BOUNDARY_FIELDS = {
    "userOwns",
    "agentOwnsWithinBoundedAuthority",
}
HUMAN_ONLY_OPERATIONS = {
    "destructive-action",
    "irreversible-action",
    "new-account-or-data-boundary",
    "new-cost",
    "new-trust",
    "capability-installation-authorization",
    "account-connection-authorization",
    "persistent-activation-authorization",
    "publication-authorization",
    "release-authorization",
    "accountable-outcome-acceptance",
}
OPERATION_EFFECTS = {
    "repository-read": "local-read",
    "repository-edit": "bounded-local-write",
    "causal-planning": "bounded-local-write",
    "local-verification": "local-read",
    "progress-accounting": "bounded-local-write",
    "bounded-repository-cleanup": "bounded-local-delete",
    "git-commit": "bounded-local-write",
    "git-push": "bounded-external-write",
    "installed-authorized-capability-use": "bounded-capability-use",
    "human-only-action-guidance-and-post-verification": "local-read",
    "bounded-consumer-configuration-after-explicit-grant": "bounded-local-write",
    "coverage-analysis": "local-read",
    "targeted-capability-discovery": "bounded-public-read",
    "capability-static-review": "local-read",
    "inactive-exact-acquisition": "bounded-local-write",
    "same-goal-carrier-transition": "bounded-host-state-change",
    "authorized-capability-installation": "bounded-local-write",
    "authorized-account-connection": "bounded-external-write",
    "authorized-persistent-activation": "bounded-host-state-change",
    "authorized-private-evidence-materialization": "bounded-local-write",
    "authorized-private-evidence-cleanup": "bounded-local-delete",
    "authorized-publication-execution": "bounded-external-write",
    "authorized-release-execution": "bounded-external-write",
}
NORMATIVE_PROFILE_BINDING_FIELDS = {
    "state",
    "profileIdentity",
    "locator",
    "sha256",
    "cohortProtocolIdentity",
    "cohortProtocolLocator",
    "cohortProtocolSha256",
    "frozenAtRevision",
    "cohortActivation",
}
UNFROZEN_NORMATIVE_PROFILE_BINDING = {
    "state": "unfrozen",
    "profileIdentity": None,
    "locator": None,
    "sha256": None,
    "cohortProtocolIdentity": None,
    "cohortProtocolLocator": None,
    "cohortProtocolSha256": None,
    "frozenAtRevision": None,
    "cohortActivation": None,
}
CURRENT_PROFILE_FREEZE_ENABLED = False
_LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY = False
NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION = (
    "910ac016f1e5963450e3cfc46f5056ab0a6b04d7"
)
CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION = (
    "5ae71bbdd43c0c5dd5a0e120e508bccf9dd9464c"
)
MAX_NORMATIVE_BINDING_HISTORY_REVISIONS = 64
MAX_NORMATIVE_BINDING_HISTORY_BYTES = 4 * 1_048_576
EXPECTED_V1_PROFILE_IDENTITY = "harness-demand-to-capability-v1.0-candidate.5"
EXPECTED_V1_PROFILE_LOCATOR = "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md"
EXPECTED_V1_PROFILE_SHA256 = (
    "c737d2614a602acdab1f66e29b5f0f957ccb142ef26bb5b5d946131e7dd5484e"
)
EXPECTED_V1_COHORT_PROTOCOL_IDENTITY = (
    "harness-prospective-cohort-v1.0-candidate.5"
)
EXPECTED_V1_COHORT_PROTOCOL_LOCATOR = (
    "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json"
)
EXPECTED_V1_COHORT_PROTOCOL_SHA256 = (
    "73b637fbe11267c621a0f37093814586a4f5aaf0b366ab972f8bc32d0c9b2f83"
)
EXPECTED_CURRENT_PROFILE_CANDIDATE_IDENTITY = (
    "harness-demand-to-capability-v1.1-candidate.1"
)
EXPECTED_CURRENT_PROFILE_CANDIDATE_LOCATOR = (
    "docs/DEMAND-TO-CAPABILITY-PROFILE-V1.1.md"
)
EXPECTED_CURRENT_PROFILE_CANDIDATE_SHA256 = (
    "536096507101be97bd08921b194c6188ca0569bf0dec6a68d0baffc55f0189d0"
)
EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_IDENTITY = (
    "harness-prospective-cohort-v1.1-candidate.1"
)
EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_LOCATOR = (
    "docs/PROSPECTIVE-COHORT-PROTOCOL-V1.1.json"
)
EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_SHA256 = (
    "3f40b79243199a562c94b92f940e09ed3781d247ce03ab63dcd2848b5974f7fc"
)
EXPECTED_CURRENT_PROFILE_ARTIFACT_REVISION = (
    "d1bc7ea2063455f1930a5fcddbe6ed6707643c0c"
)
# A first v1.1 freeze is committed before its own revision and canonical
# binding digest can be pinned by the next code revision. Until those anchors
# and an independent source validator are registered, any attempted frozen
# program fails closed while the live unfrozen program remains valid.
EXPECTED_CURRENT_INITIAL_BINDING_REVISION: str | None = (
    "5ce27730b982d3c78ed50d006f78ff0eea45d4a9"
)
EXPECTED_CURRENT_INITIAL_BINDING_SHA256: str | None = (
    "90edd88249ae21114a9d723c703923217318494c515f4444156a0d1c13d54b2a"
)
EXPECTED_CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID: str | None = (
    "codex-windows-source-native-first-freeze-authorization-v1.1"
)
CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID = (
    "codex-windows-source-native-first-freeze-authorization-v1.1"
)
CURRENT_INITIAL_BINDING_AUTHORIZATION_EXPIRY_UTC = datetime(
    2026, 12, 31, 15, 59, 59, tzinfo=timezone.utc
)
CURRENT_INITIAL_EXPIRY_TASK_NAME = "AgentAutonomyHarness-v1.1-expiry"
CURRENT_INITIAL_EXPIRY_TASK_START_BOUNDARY = "2026-12-31T23:59:59+08:00"
CURRENT_INITIAL_EXPIRY_TASK_ARGUMENTS = (
    "-B -m harness expire-current-cohort-private-evidence"
)
# Immutable commit that contains the reviewed profile and cohort-protocol bytes.
EXPECTED_V1_PROFILE_ARTIFACT_REVISION: str | None = (
    "502c4ff7edfc6307ea5469bcb81089e13612a24a"
)
# The first frozen binding necessarily exists one commit before code can pin
# its own revision and digest. These anchors make that first freeze immutable.
EXPECTED_V1_INITIAL_BINDING_REVISION: str | None = (
    "d19d2fb9da0883a44eec887eca4072e70a93f8d7"
)
EXPECTED_V1_INITIAL_BINDING_SHA256: str | None = (
    "ee4ba7a16f15bba78efbefce1022ac6180d1c7e40e800011348df5ae21ab0eb7"
)
# A terminally revoked zero-outcome cohort may be followed by exactly one fresh
# successor generation. The revoked freeze remains immutable; these anchors
# stay unavailable until a later commit contains and independently authorizes
# the successor freeze.
EXPECTED_V1_SUCCESSOR_BINDING_REVISION: str | None = (
    "8e8e76ba65db8f625792aed7dfb9180790433459"
)
EXPECTED_V1_SUCCESSOR_BINDING_SHA256: str | None = (
    "d2cf0cdce692fb06bf59bc1002d8b6036b6d1ee79ac6a86c27c74358f157dbfa"
)
SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID = (
    "codex-windows-source-native-successor-freeze-authorization-v1"
)
EXPECTED_V1_SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID: str | None = (
    SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID
)
EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION = (
    "179d52eb8c46b55f1ee778eb6e9daf7622ae85d4"
)
EXPECTED_V1_PREDECESSOR_REVOCATION_BINDING_SHA256 = (
    "cfdc4f596e0bcf689496ce37867f95764089c5046eca9328c5291fce342a45ca"
)
EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_WINDOW_RULE = (
    "complete-source-native-window-after-predecessor-revocation-through-"
    "successor-authorization-no-eligible-demand-v1"
)
# The first frozen commit is not effective cohort activation until a named
# human independently authorizes its exact revision and canonical binding
# digest through a source that this code-owned validator can verify.
INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID = (
    "codex-windows-source-native-first-freeze-authorization-v1"
)
EXPECTED_V1_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID: str | None = (
    INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID
)
INITIAL_BINDING_AUTHORIZATION_EXPIRY_UTC = datetime(
    2026, 12, 31, 15, 59, 59, tzinfo=timezone.utc
)
SUCCESSOR_BINDING_AUTHORIZATION_EXPIRY_UTC = datetime(
    2026, 12, 31, 15, 59, 59, tzinfo=timezone.utc
)
SUCCESSOR_EXPIRY_TASK_NAME = "AgentAutonomyHarness-v1-successor-expiry"
SUCCESSOR_EXPIRY_TASK_START_BOUNDARY = "2026-12-31T23:59:59+08:00"
SUCCESSOR_EXPIRY_TASK_ARGUMENTS = (
    "-B -m harness expire-successor-cohort-private-evidence"
)
MAX_SUCCESSOR_EXPIRY_TASK_XML_BYTES = 1_048_576
NONDESTRUCTIVE_INITIAL_AUTHORIZATION_SOURCE_FAILURES = frozenset(
    {
        "initial binding authorization source event is unavailable",
        "initial binding authorization source event changed during validation",
    }
)
NONDESTRUCTIVE_SUCCESSOR_AUTHORIZATION_SOURCE_FAILURES = frozenset(
    {
        "successor binding authorization source event is unavailable",
        "successor binding authorization source event changed during validation",
        "successor binding authorization expiry cleanup trigger is unavailable",
    }
)
NONDESTRUCTIVE_CURRENT_INITIAL_AUTHORIZATION_SOURCE_FAILURES = frozenset(
    {
        "current v1.1 binding authorization source event is unavailable",
        "current v1.1 binding authorization source event changed during validation",
        "current v1.1 binding authorization expiry cleanup trigger is unavailable",
    }
)
EXPECTED_INITIAL_AUTHORIZATION_KEY_FINGERPRINT = (
    "sha256:6d0edc4c500afdb7cc3a3e35a5805b2187feb8fb7958c90f0a21e4101721a0e3"
)
EXPECTED_INITIAL_BINDING_AUTHORIZATION_MESSAGE_SHA256 = (
    "9cb3002787034afb2df433256481d4a2bcaf907a0607f2ee4ccc497e84e09b58"
)
EXPECTED_SUCCESSOR_BINDING_AUTHORIZATION_MESSAGE_SHA256 = (
    "d8c840e7bc223a79bcba1d6481a0090f219f7bb678e44d8226f13aabcce9944f"
)
INITIAL_AUTHORIZATION_TARGET_HMAC_DOMAIN = (
    "agent-autonomy-harness/private-credential-target/v1"
)
INITIAL_AUTHORIZATION_SOURCE_ROOT_HMAC_DOMAIN = (
    "agent-autonomy-harness/private-source-root/v1"
)
INITIAL_AUTHORIZATION_EVENT_HMAC_DOMAIN = (
    "agent-autonomy-harness/first-freeze-authorization-event/v1"
)
INITIAL_AUTHORIZATION_WINDOW_HMAC_DOMAIN = (
    "agent-autonomy-harness/first-freeze-source-window/v1"
)
SUCCESSOR_AUTHORIZATION_TARGET_HMAC_DOMAIN = (
    "agent-autonomy-harness/successor-private-credential-target/v1"
)
SUCCESSOR_AUTHORIZATION_SOURCE_ROOT_HMAC_DOMAIN = (
    "agent-autonomy-harness/successor-private-source-root/v1"
)
SUCCESSOR_PREDECESSOR_RECORD_HMAC_DOMAIN = (
    "agent-autonomy-harness/successor-predecessor-revocation-record/v1"
)
SUCCESSOR_RESTART_EVENT_HMAC_DOMAIN = (
    "agent-autonomy-harness/successor-restart-grant-event/v1"
)
SUCCESSOR_AUTHORIZATION_EVENT_HMAC_DOMAIN = (
    "agent-autonomy-harness/successor-freeze-authorization-event/v1"
)
SUCCESSOR_AUTHORIZATION_WINDOW_HMAC_DOMAIN = (
    "agent-autonomy-harness/successor-freeze-authorization-window/v1"
)
CURRENT_INITIAL_AUTHORIZATION_TARGET_HMAC_DOMAIN = (
    "agent-autonomy-harness/private-credential-target/v1.1"
)
CURRENT_INITIAL_AUTHORIZATION_SOURCE_ROOT_HMAC_DOMAIN = (
    "agent-autonomy-harness/private-source-root/v1.1"
)
CURRENT_INITIAL_MATERIALIZATION_EVENT_HMAC_DOMAIN = (
    "agent-autonomy-harness/materialization-grant-event/v1.1"
)
CURRENT_INITIAL_AUTHORIZATION_EVENT_HMAC_DOMAIN = (
    "agent-autonomy-harness/first-freeze-authorization-event/v1.1"
)
CURRENT_INITIAL_AUTHORIZATION_WINDOW_HMAC_DOMAIN = (
    "agent-autonomy-harness/first-freeze-source-window/v1.1"
)
INITIAL_AUTHORIZATION_CREDENTIAL_FILTER = "AgentAutonomyHarness/v1/*"
SUCCESSOR_AUTHORIZATION_CREDENTIAL_FILTER = "AgentAutonomyHarness/v1-successor/*"
CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_FILTER = "AgentAutonomyHarness/v1.1/*"
# These privacy-safe commitments are materialized from the already-authorized
# protected source during this bounded repair. Until then, the live validator
# fails closed rather than accepting an unbound private resource or event.
EXPECTED_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT: str | None = (
    "hmac-sha256:c049b95c7280c0e0e4c51eecfe0157d3e20bfdecfa35cbe5de4fe5e6cbe33c63"
)
EXPECTED_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT: str | None = (
    "hmac-sha256:389a9ef54b945a10a2eb5801129b0055a2224b2fe14aa641436430a7aa28b1a4"
)
EXPECTED_INITIAL_AUTHORIZATION_EVENT_COMMITMENT: str | None = (
    "hmac-sha256:a33a374922972043ee437072da7e017b5feac702b60d3d55f906d7ec853fdcd3"
)
EXPECTED_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT: str | None = (
    "hmac-sha256:309ae590a3686d2a35238fa62b84e5eb3350951801edfbd8a4d092cdfced481f"
)
EXPECTED_SUCCESSOR_AUTHORIZATION_KEY_FINGERPRINT = (
    "sha256:bf96b012d3a6c59a9f8cb6f4636cdf5a4860ed5fbdc1d4dbbccd093d11173e52"
)
EXPECTED_SUCCESSOR_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT = (
    "hmac-sha256:6765986f4d7255eafc72a48e0e4d21e04982cd1b65ad9bf2f0a11ecf7145284d"
)
EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_ROOT_COMMITMENT = (
    "hmac-sha256:eb280179356cc09f61d771929a96861c5729392544dbb945b64adc9f77b333bd"
)
EXPECTED_SUCCESSOR_PREDECESSOR_RECORD_COMMITMENT = (
    "hmac-sha256:6615c6b3cb8688c8a10a8c714a55cf5cfcf5f935ec07f75a3d17ac23666cf884"
)
EXPECTED_SUCCESSOR_RESTART_EVENT_COMMITMENT = (
    "hmac-sha256:22588b47b3f213cc7583825783553b8236875908f87a7b7f5c374d9892506e0c"
)
EXPECTED_SUCCESSOR_AUTHORIZATION_EVENT_COMMITMENT = (
    "hmac-sha256:56d02ba7d713b52086ee294efa96c280978b281dd80bb3989799b1e2fbf03fc4"
)
EXPECTED_SUCCESSOR_AUTHORIZATION_WINDOW_COMMITMENT = (
    "hmac-sha256:14edd891420cfad6510f735d1203fb142b84f26929b5455b103610164d7bb759"
)
EXPECTED_SUCCESSOR_SURFACE_IDENTITY = (
    "enrollment-surface.public-v1:56369773375e42299d33351024f7be64"
)
EXPECTED_SUCCESSOR_ACTIVATION_CURSOR_COMMITMENT = (
    "hmac-sha256:2eec98cf28f6a1e01ed4d73258045f0bb1097e3ba9f6ef7cdf60a2672ed6d35c"
)
EXPECTED_SUCCESSOR_KEY_IDENTITY = (
    "cohort-key.public-v1:55020ba1e3bd4a9cbefc23f167f0a13b"
)
EXPECTED_CURRENT_INITIAL_AUTHORIZATION_KEY_FINGERPRINT: str | None = (
    "sha256:9b7ec2a0f1463bee11e4ec822ef9c4c0942e36081d5954a57c0707ef3ef7fa60"
)
EXPECTED_CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT: str | None = (
    "hmac-sha256:9e6c65cf12b37d955fdd7ca3807fd1ec3252ce5334008bd7a816d9c247ebf563"
)
EXPECTED_CURRENT_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT: str | None = (
    "hmac-sha256:1b6f254d373e860bf8197b5ecdc4c991e8da2ffab6c3703a2102d5f16f08ae0c"
)
EXPECTED_CURRENT_INITIAL_MATERIALIZATION_EVENT_COMMITMENT: str | None = (
    "hmac-sha256:869e16d4dc0add134e5a2405deb000161badc39d4b4e3e74f40e8fb5223eb137"
)
EXPECTED_CURRENT_INITIAL_AUTHORIZATION_EVENT_COMMITMENT: str | None = (
    "hmac-sha256:ddf172bfc77626c07abf06d705b3cd64f27b7e7da431420854636020ae03eb80"
)
EXPECTED_CURRENT_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT: str | None = (
    "hmac-sha256:cb9fcb38e86dfdee45aa1de3502b2c984e34476d630a6a6a6192a9f6b5995a22"
)
EXPECTED_CURRENT_INITIAL_SURFACE_IDENTITY: str | None = (
    "enrollment-surface.public-v1:d2225c88f80d45ee89a1426545963fe1"
)
EXPECTED_CURRENT_INITIAL_ACTIVATION_CURSOR_COMMITMENT: str | None = (
    "hmac-sha256:da3511ce306de7001a0def71edcf8a8457fa03fd899ef0db05185027a389b9eb"
)
EXPECTED_CURRENT_INITIAL_KEY_IDENTITY: str | None = (
    "cohort-key.public-v1:c8bd6e7fce454086b9c7534fed2a8065"
)
EXPECTED_CURRENT_INITIAL_PRIVATE_EVIDENCE_DISPOSITION = (
    "authorized-retain-through-live-v1.1-claim-no-later-than-"
    "2026-12-31T23:59:59+08:00-delete-and-revoke-on-withdrawal-expiry-"
    "stop-or-deterministic-validation-failure"
)
EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY = (
    "task-specific-pre-registration-manifests-under-current-acceptance-contract-"
    "no-cohort-global-static-manifest"
)
CURRENT_INITIAL_PRIVATE_RESOURCE_PROGRAM_DISPOSITION = (
    "v1.1-cohort-private-evidence:windows-current-user-protected;"
    "retain-through-live-v1.1-claim-no-later-than-2026-12-31T23:59:59+08:00;"
    "delete-and-revoke-on-withdrawal-expiry-stop-or-deterministic-validation-failure"
)
CURRENT_INITIAL_EXPIRY_TRIGGER_PROGRAM_DISPOSITION = (
    "v1.1-expiry-trigger:windows-current-user-s4u;"
    "one-time-2026-12-31T23:59:59+08:00;"
    "remove-on-private-resource-destruction-or-expiry"
)
INITIAL_BINDING_PRIVATE_EVIDENCE_FIELDS = {
    "schema",
    "kind",
    "surfaceIdentity",
    "activationCursorCommitment",
    "keyIdentity",
    "keyFingerprint",
    "keyBase64",
    "sourceKind",
    "sourceRollout",
    "sourceEventIdentity",
    "sourceEventTimestamp",
    "disposition",
}
SUCCESSOR_BINDING_PRIVATE_EVIDENCE_FIELDS = {
    "schema",
    "kind",
    "surfaceIdentity",
    "activationCursorCommitment",
    "keyIdentity",
    "keyFingerprint",
    "keyBase64",
    "sourceKind",
    "sourceRollout",
    "sourceEventIdentity",
    "sourceEventTimestamp",
    "authorizationEventIdentity",
    "authorizationEventTimestamp",
    "predecessorRevocationRecordIdentity",
    "predecessorRevocationRecordTimestamp",
    "predecessorRevocationRevision",
    "disposition",
}
CURRENT_INITIAL_BINDING_PRIVATE_EVIDENCE_FIELDS = {
    "schema",
    "kind",
    "surfaceIdentity",
    "activationCursorCommitment",
    "keyIdentity",
    "keyFingerprint",
    "keyBase64",
    "sourceKind",
    "sourceRollout",
    "sourceEventIdentity",
    "sourceEventTimestamp",
    "authorizationEventIdentity",
    "authorizationEventTimestamp",
    "environmentAttributionContractSha256",
    "environmentManifestBoundary",
    "disposition",
}
MAX_INITIAL_AUTHORIZATION_CREDENTIAL_BYTES = 16_384
MAX_INITIAL_AUTHORIZATION_SOURCE_BYTES = 256 * 1_048_576
MAX_INITIAL_AUTHORIZATION_SOURCE_LINE_BYTES = 8 * 1_048_576
MAX_INITIAL_AUTHORIZATION_SOURCE_RECORDS = 100_000
COHORT_ACTIVATION_FIELDS = {
    "surfaceIdentity",
    "activationCursorCommitment",
    "keyIdentity",
    "keyFingerprint",
    "sourceMessageRule",
    "hmacDomain",
    "surfaceTransitionRule",
    "keyRetentionRule",
}
EXPECTED_SOURCE_MESSAGE_RULE = (
    "domain-surface-source-native-immutable-event-identity-v1"
)
EXPECTED_HMAC_DOMAIN = "agent-autonomy-harness/cohort-source-event/v1"
EXPECTED_CURRENT_SOURCE_MESSAGE_RULE = (
    "domain-surface-source-native-immutable-event-identity-v1.1"
)
EXPECTED_CURRENT_HMAC_DOMAIN = "agent-autonomy-harness/cohort-source-event/v1.1"
EXPECTED_SURFACE_TRANSITION_RULE = (
    "pre-demand-causal-trigger-source-final-cursor-destination-verified-or-stop"
)
EXPECTED_KEY_RETENTION_RULE = (
    "retain-private-evidence-through-live-claim-or-destroy-and-revoke-verifiability"
)
PUBLIC_SURFACE_IDENTITY_PATTERN = re.compile(
    r"enrollment-surface\.public-v1:[0-9a-f]{32}"
)
PUBLIC_COHORT_KEY_IDENTITY_PATTERN = re.compile(
    r"cohort-key\.public-v1:[0-9a-f]{32}"
)
SHA256_COMMITMENT_PATTERN = re.compile(r"(?:hmac-)?sha256:[0-9a-f]{64}")
COHORT_PROTOCOL_FIELDS = {
    "schema",
    "id",
    "profileIdentity",
    "cohortProtocolIdentity",
    "eligibilityRule",
    "exclusionRule",
    "taskIdentityRule",
    "strata",
    "enrollmentSurfaceRule",
    "activationRule",
    "enrollmentCursorRule",
    "sourceMessageRule",
    "hmacDomain",
    "surfaceTransitionRule",
    "keyRetentionRule",
    "naturalDemandEventRule",
    "enrollmentOrder",
    "stopRule",
    "failedOrMissingSampleDisposition",
    "measurementEventRule",
    "claimLimits",
}
CURRENT_COHORT_PROTOCOL_FIELDS = {
    "schema",
    "id",
    "profileIdentity",
    "cohortProtocolIdentity",
    "eligibilityRule",
    "exclusionRule",
    "taskIdentityRule",
    "scenarioCoverageRule",
    "enrollmentSurfaceRule",
    "activationRule",
    "enrollmentCursorRule",
    "sourceMessageRule",
    "hmacDomain",
    "surfaceTransitionRule",
    "keyRetentionRule",
    "environmentAttributionRule",
    "versionResolutionRule",
    "humanInterventionRule",
    "naturalDemandEventRule",
    "enrollmentOrder",
    "stopRule",
    "failedOrMissingSampleDisposition",
    "measurementEventRule",
    "claimLimits",
}
EXPECTED_COHORT_SCENARIO_CLASSES = (
    "zero-tool-knowledge-new-intake",
    "existing-project-continuation",
    "long-context-work",
    "residual-capability-gap",
    "consequential-human-gate",
    "honest-failure-or-recovery",
)
CANONICAL_TASK_IDENTITY_PATTERN = re.compile(
    r"natural-task\.public-v1:[0-9a-f]{32}"
)
EXPECTED_COHORT_PROTOCOL_RULES = MappingProxyType(
    {
        "eligibilityRule": "all-eligible-demands-after-source-verified-first-freeze-authorization",
        "exclusionRule": "source-fact-only-no-postmeasurement-exclusion",
        "taskIdentityRule": "random-public-id-cohort-keyed-hmac-source-binding-validator-dedup",
        "enrollmentSurfaceRule": "single-active-source-native-ordered-carrier",
        "activationRule": "first-freeze-binding-then-source-verified-exact-human-authorization-before-demand",
        "enrollmentCursorRule": "activation-or-prior-registration-cursor-no-eligible-gap",
        "sourceMessageRule": EXPECTED_SOURCE_MESSAGE_RULE,
        "hmacDomain": EXPECTED_HMAC_DOMAIN,
        "surfaceTransitionRule": EXPECTED_SURFACE_TRANSITION_RULE,
        "keyRetentionRule": EXPECTED_KEY_RETENTION_RULE,
        "naturalDemandEventRule": "source-native-event-after-authorized-activation-before-registration-required",
        "enrollmentOrder": "source-native-cursor-then-strict-git-registration-ancestry",
        "stopRule": "earliest-prefix-satisfying-current-acceptance",
        "failedOrMissingSampleDisposition": "retain-fail-closed-no-replacement",
        "measurementEventRule": "task-bound-measurement-event-after-registration-required",
    }
)
EXPECTED_CURRENT_COHORT_PROTOCOL_RULES = MappingProxyType(
    {
        "eligibilityRule": "all-eligible-demands-after-source-verified-current-freeze-authorization",
        "exclusionRule": "source-fact-only-no-postmeasurement-exclusion",
        "taskIdentityRule": "random-public-id-cohort-keyed-hmac-source-binding-validator-dedup",
        "scenarioCoverageRule": "current-acceptance-owned-no-protocol-defined-scenario-or-environment-strata",
        "enrollmentSurfaceRule": "single-active-source-native-ordered-carrier",
        "activationRule": "current-freeze-binding-then-source-verified-exact-human-authorization-before-demand",
        "enrollmentCursorRule": "activation-or-prior-registration-cursor-no-eligible-gap",
        "sourceMessageRule": EXPECTED_CURRENT_SOURCE_MESSAGE_RULE,
        "hmacDomain": EXPECTED_CURRENT_HMAC_DOMAIN,
        "surfaceTransitionRule": EXPECTED_SURFACE_TRANSITION_RULE,
        "keyRetentionRule": EXPECTED_KEY_RETENTION_RULE,
        "environmentAttributionRule": "bind-current-acceptance-contract-starting-manifest-authority-source-envelope-and-task-time-deltas",
        "versionResolutionRule": "per-decision-current-source-exact-execution-identity-before-use-or-stop",
        "humanInterventionRule": "record-all-human-actions-zero-prohibited-agent-work-transfer-minimal-guided-verified-human-only",
        "naturalDemandEventRule": "source-native-event-after-authorized-activation-before-registration-required",
        "enrollmentOrder": "source-native-cursor-then-strict-git-registration-ancestry",
        "stopRule": "earliest-prefix-satisfying-current-acceptance",
        "failedOrMissingSampleDisposition": "retain-fail-closed-no-replacement",
        "measurementEventRule": "task-bound-measurement-event-after-registration-required",
    }
)
TERMINAL_RELEASE_BINDING_FIELDS = {
    "state",
    "tag",
    "publicRemote",
    "annotationFormat",
    "o5EvidenceSetSha256",
    "authorizationValidator",
    "authorizationSourcePolicy",
}
UNREGISTERED_TERMINAL_RELEASE_BINDING = {
    "state": "unregistered",
    "tag": None,
    "publicRemote": None,
    "annotationFormat": None,
    "o5EvidenceSetSha256": None,
    "authorizationValidator": None,
    "authorizationSourcePolicy": None,
}
TERMINAL_AUTHORIZATION_VALIDATOR_BINDING_FIELDS = {
    "kind",
    "version",
    "locator",
    "revision",
    "sha256",
}
TERMINAL_AUTHORIZATION_SOURCE_POLICY_FIELDS = {
    "sourceKind",
    "publicIdentityScheme",
    "commitmentScheme",
    "privateLocatorRule",
}
EXPECTED_TERMINAL_AUTHORIZATION_PUBLIC_IDENTITY_SCHEME = "random-public-id-v1"
EXPECTED_TERMINAL_AUTHORIZATION_COMMITMENT_SCHEME = (
    "source-private-keyed-hmac-sha256-v1"
)
EXPECTED_TERMINAL_AUTHORIZATION_PRIVATE_LOCATOR_RULE = (
    "code-owned-validator-private-only-never-public"
)
TERMINAL_PUBLIC_AUTHORIZATION_IDENTITY_PATTERN = re.compile(
    r"terminal-authorization\.public-v1:[0-9a-f]{32}"
)
TERMINAL_RELEASE_ANNOTATION_FIELDS = {
    "schema",
    "format",
    "productId",
    "release",
    "candidateRevision",
    "tag",
    "publicRemote",
    "o5EvidenceSetSha256",
    "authority",
    "acceptedScope",
}
TERMINAL_RELEASE_AUTHORITY_FIELDS = {
    "kind",
    "name",
    "decision",
    "decidedAt",
    "source",
    "validator",
}
TERMINAL_RELEASE_AUTHORITY_SOURCE_FIELDS = {
    "kind",
    "publicIdentity",
    "commitment",
}
TERMINAL_RELEASE_AUTHORITY_VALIDATOR_FIELDS = {"kind", "version"}
EXPECTED_TERMINAL_RELEASE_SCOPE = [
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
]
EXPECTED_PUBLIC_REMOTE = "https://github.com/yiheng8023/agent-autonomy-harness.git"
TERMINAL_RELEASE_ANNOTATION_FORMAT = "harness-release-authorization-v2"
PROCESS_LOSS_FIELDS = {
    "maxSameClassUserCorrectionBeforeStop",
    "maxConsecutiveOutcomeNeutralWorkItems",
    "maxProhibitedAgentWorkTransfers",
    "stopOnAuthorityOrIrreversibleIncident",
    "stopOnUnboundedResidue",
}
INCREMENT_FIELDS = {
    "id",
    "state",
    "correctionClass",
    "observedProblem",
    "hypothesis",
    "falsifier",
    "stopCondition",
    "acceptanceIds",
    "taskRegistration",
    "processLossBudget",
    "cleanupBoundary",
    "workItems",
}
TASK_REGISTRATION_BINDING_FIELDS = {
    "locator",
    "sha256",
    "sourceRevision",
    "measurementNotBefore",
    "profileSha256",
    "cohortProtocolSha256",
    "preMeasurementValidator",
}
PRE_MEASUREMENT_VALIDATOR_BINDING_FIELDS = {
    "kind",
    "version",
    "locator",
    "revision",
    "sha256",
}
TASK_REGISTRATION_FIELDS = {
    "schema",
    "id",
    "registeredAt",
    "taskIdentity",
    "incrementId",
    "criterionIds",
    "preRegistrationValues",
    "acceptanceAuthority",
    "namedHumanAcceptor",
    "qualitySafetyEvidenceAndResidueFloors",
    "materialInterventionTaxonomy",
    "materialCollaborationLossTaxonomy",
    "sourceCaptureEligibilityAndStopRule",
    "claimLimits",
    "preMeasurementValidator",
}
SOURCE_CAPTURE_FIELDS = {
    "enrollmentSurfaceRule",
    "cursorWindowStartsAfter",
    "naturalDemandObservedBefore",
    "measurementStartsAfter",
    "eligibleSources",
    "ineligibleSources",
    "stopRule",
}
ENROLLMENT_SURFACE_AND_CURSOR_FIELDS = {
    "surfaceIdentity",
    "cohortKeyIdentity",
    "cohortKeyFingerprint",
    "sourceMessageRule",
    "hmacDomain",
    "cursorWindowStartCommitment",
    "naturalDemandCursorCommitment",
    "previousRegistrationTaskIdentity",
    "surfaceTransition",
}
SURFACE_TRANSITION_FIELDS = {
    "state",
    "sourceSurfaceIdentity",
    "sourceWindowStartCommitment",
    "sourceFinalCursorCommitment",
    "cause",
}
NATURAL_DEMAND_PRIVATE_BINDING_FIELDS = {
    "bindingScheme",
    "sourceKind",
    "sourceCommitment",
    "sourceMessageRule",
    "cohortKeyIdentity",
    "cohortKeyFingerprint",
}
ENVIRONMENT_ATTRIBUTION_BINDING_FIELDS = {
    "contractSha256",
    "environmentClass",
    "treatmentArm",
    "manifestLocator",
    "manifestRevision",
    "manifestSha256",
    "harnessActivationDelta",
}
HARNESS_ACTIVATION_DELTA_FIELDS = {
    "state",
    "packageIdentity",
    "packageSha256",
    "activationIdentity",
    "activationSha256",
    "taskExposureIdentity",
    "taskExposureSha256",
}
EXPECTED_PRIVATE_BINDING_SCHEME = "cohort-keyed-hmac-sha256-v1"
SOURCE_KIND_PATTERN = re.compile(r"[a-z0-9][a-z0-9.-]{0,63}")
ALLOWED_SURFACE_TRANSITION_CAUSES = {
    "source-unavailable",
    "source-capacity-boundary",
    "host-capacity-boundary",
    "authority-boundary",
}
ACCEPTANCE_AUTHORITY_FIELDS = {"locator", "criteriaContractSha256"}
TASK_REGISTRATION_VALUE_ALIASES = {
    "registeredAt",
    "taskIdentity",
    "namedHumanAcceptor",
    "qualitySafetyEvidenceAndResidueFloors",
    "materialInterventionTaxonomy",
    "materialCollaborationLossTaxonomy",
}
WORK_ITEM_FIELDS = {
    "id",
    "state",
    "acceptanceIds",
    "operationIds",
    "deliverables",
}
CLEANUP_BOUNDARY_FIELDS = {
    "repositoryTemporaryPaths",
    "privateResourceDispositions",
}
ALLOWED_PRIVATE_RESOURCE_DISPOSITIONS = {
    "v1-cohort-private-evidence:windows-user-protected;"
    "retain-through-accepted-or-stopped-no-later-than-2026-12-31T23:59:59+08:00;"
    "delete-and-revoke-on-withdrawal-expiry-stop-or-validation-failure",
    "v1-successor-expiry-trigger:windows-current-user-s4u;"
    "one-time-2026-12-31T23:59:59+08:00;"
    "remove-on-accepted-stopped-or-private-resource-destruction",
    CURRENT_INITIAL_PRIVATE_RESOURCE_PROGRAM_DISPOSITION,
    CURRENT_INITIAL_EXPIRY_TRIGGER_PROGRAM_DISPOSITION,
}
PROGRAM_STATES = {"active", "ready", "stopped", "completed"}
INCREMENT_STATES = {"planned", "active", "completed", "cancelled", "stopped"}
WORK_STATES = {"planned", "active", "completed", "cancelled", "stopped"}
TERMINAL_STATES = {"completed", "cancelled", "stopped"}
EXPECTED_WORK_STATE_SEMANTICS = {
    "planned": "bound but not current or executed",
    "active": "current and execution may have started",
    "completed": "execution finished",
    "cancelled": "bound but never active or executed",
    "stopped": "previously active or attempted, then stopped",
}
EXPECTED_PLANNING_MODEL = {
    "method": "fixed-release-acceptance-with-adaptive-causal-increments",
    "maxActiveIncrements": 1,
    "maxActiveWorkItems": 1,
    "workStateSemantics": EXPECTED_WORK_STATE_SEMANTICS,
    "incrementRequires": [
        "observed problem",
        "causal hypothesis",
        "falsifier",
        "correction class",
        "mapped acceptance criteria",
        "content-addressed task registration for outcome-bearing work",
        "finite stop condition",
        "process-loss budget",
        "cleanup boundary",
    ],
    "replanWhen": [
        "the hypothesis is falsified",
        "new evidence changes the critical path",
        "the user must reassert already-bound direction",
        "the same process-loss class recurs",
        "a phase produces no direct outcome movement",
        "authority, trust, cost, or data boundaries change",
        "the increment reaches its stop condition",
    ],
}
EXPECTED_COLLABORATION_MODEL = {
    "userContributions": [
        "ideas-and-goals",
        "domain-facts-and-judgment",
        "bounded-authorization",
        "technically-or-authoritatively-unavoidable-human-only-action-under-exact-agent-guidance",
        "corrections",
        "accountable-final-judgment",
    ],
    "agentObligations": [
        "intent-and-omission-detection",
        "available-capability-observation-and-gap-detection",
        "source-bounded-targeted-capability-discovery",
        "capability-selection-and-task-scoped-dispatch",
        "human-only-action-detection-minimal-guidance-and-post-verification",
        "task-topology-selection-reconciliation-merge-release-and-cleanup",
        "context-carrier-fitness-observation-and-proactive-transition",
        "bounded-setup-and-execution",
        "failure-recovery",
        "verification-and-claim-control",
        "task-exposure-release-cleanup-and-continuity",
        "process-loss-detection-and-replanning",
    ],
}
EXPECTED_PRODUCT_FORM = {
    "identity": "open-agent-neutral-demand-driven-human-agent-collaboration-quality-harness",
    "durableOutputs": [
        "portable-demand-to-outcome-collaboration-semantics",
        "open-minimum-quality-evidence-and-conformance-contract",
        "adaptive-thin-reference-projections",
    ],
    "portableCore": "delivery-form-and-operating-system-neutral-testable-demand-authority-capability-task-topology-and-context-carrier-lifecycle-evidence-acceptance-and-burden-semantics",
    "referenceDelivery": "codex-first-reference-slice-then-distinct-host-and-operating-system-portability-proof",
}
EXPECTED_FIXED_INVARIANTS = frozenset(
    {
        "product outcomes outrank artifact counts, test counts, inventory counts, and research volume",
        "one release has one explicit finite acceptance expression",
        "guardrails constrain delivery but never count as product progress",
        "every active work item maps to at least one release criterion",
        "only one causal increment and at most one work item may be active",
        "goal-level demand is the default entry; the user need not name a capability, product, discovery channel, or invocation syntax",
        "the portable core is not a capability catalog, capability manager, collaboration wire protocol, audit log, universal runtime, or host projection",
        "capability discovery sources and query strategies are adaptive inputs and no fixed channel can become product authority",
        "user-installed ecosystem breadth is legitimate user freedom and is not a failure explanation",
        "task-time capability and metadata exposure is minimal even when the available portfolio is broad",
        "capability lifecycle is demand-driven from the observed starting state rather than capped by it: evaluate healthy native and already-authorized routes first, add or change only for an evidenced residual gap, perform every supported authorized mechanic, guide and verify only technically or authoritatively unavoidable human steps, and disable, downgrade, roll back, retire, release, or separately justify persistence when need or fitness changes",
        "task topology is demand-driven: preserve the current healthy carrier by default; create a branch, worktree, repository fork, conversation fork, or new task only for source-bound causal necessity; the Agent owns identity, synchronization, merge or reconciliation, archive or release, and cleanup while the user retains goal, authority, trust, cost, and irreversible decisions",
        "conversation-carrier fitness is Agent-owned: use source-bound observable host and task signals to keep the current carrier only while it remains safe, choose native compaction or a verified handoff before preventable quality or capacity loss, and when reliable signals are unavailable record that limit and apply a conservative pre-declared transition rule rather than making the user guess",
        "reuse or adapt sufficient external collaboration protocols, human-allocation research, runtimes, discovery, identity, governance, provenance, and evaluation capability before composition or authoring; at each decision dynamically resolve the current suitable official or maintained source from a bounded as-of source and bind the exact execution version, commit, or package identity, license or applicable terms, maturity, and reuse boundary; never make one historical version a universal lock or execute an unresolved moving target; new implementation requires an evidenced residual semantic gap",
        "reference-host calibration or one operating-system family cannot establish Agent-neutral portability; O5 requires distinct-host and bounded cross-operating-system proof",
        "durable product results are defined by portable collaboration, evidence, and conformance semantics; methodology, documentation, CLI, API, Skill, plugin, MCP, Hook, adapter, package, service, or another carrier is a non-exhaustive adaptive projection chosen by demand and host fitness rather than mandatory product body",
        "operating-system-specific installation, authorization, protected storage, execution, rollback, cleanup, and evidence mechanisms are replaceable adapter concerns rather than portable core; portability claims name only tested operating-system families, versions, virtualization boundaries, and host or runtime combinations and never imply universal operating-system support",
        "host, model, provider, system and developer instructions, account and managed policy, consumer configuration, AGENTS.md, rules, Skills, plugins, Apps, MCP, Hooks, memory, managers, operating system, runtime, and tool or resource surfaces are explicit evaluation variables rather than universal user defaults",
        "Harness-specific value is estimated only through pre-registered matched comparisons with the same task-relevant starting environment and authority-and-available-source envelope, in which exact Harness activation is the only planned initial route and configuration difference; later Agent-selected or human-authorized capability and configuration changes are treatment-mediated lifecycle deltas that must be attributed rather than normalized away; unavoidable task differences remain explicit matching variables and limit the claim, so observational evidence is not mislabeled as single-variable causation; observed-native-minimum and user-configured evidence remain distinct and unknown or unobservable environment state is retained as unknown rather than assumed absent",
        "claims and authority transitions are zero-trust while safe reversible work uses bounded default autonomy",
        "memory, consumer projections, historical evidence, and installed payloads cannot become current product authority by existing",
        "unsupported host behavior is reported rather than simulated",
    }
)
EXPECTED_ADAPTIVE_SURFACES = frozenset(
    {
        "module and Skill shape",
        "capability discovery source and query strategy",
        "host and manager adapter sequence",
        "delivery form and projection shape",
        "operating-system-specific adapter and evidence mechanism",
        "task carrier topology and host primitive",
        "native, official, reviewed external, composed, or authored capability choice",
        "current source and exact execution-version resolution",
        "experiment design",
        "delivery order inside the active causal increment",
    }
)
EXPECTED_BOOTSTRAP_GUARDS = frozenset(
    {
        "code-owned authority identity and path validation",
        "active authority cannot include evidence archives, temporary roots, legacy roots, or symlinks",
        "verified outcomes require a code-owned evidence validator",
        "conventional repository residue is detected outside declared cleanup paths",
    }
)
ASSESSMENTS = {"planned", "computed", "verified"}
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
RELEASE = re.compile(r"^v\d+\.\d+$")
FORBIDDEN_AUTHORITY_PATTERNS = (
    re.compile(r"agent[-]skills[-]curated", re.IGNORECASE),
    re.compile(r"registry/curation[-]program[-]plan[.]json", re.IGNORECASE),
    re.compile(r"registry/program[-]acceptance[-]map[.]json", re.IGNORECASE),
)
CONVENTIONAL_RESIDUE_NAMES = {
    ".tmp",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    ".tox",
    ".nox",
    ".hypothesis",
    ".ipynb_checkpoints",
    ".ds_store",
    "thumbs.db",
}
CONVENTIONAL_RESIDUE_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".log",
    ".bak",
    ".orig",
    ".rej",
)
MAX_DOCUMENT_BYTES = 1_048_576
MAX_JSON_BYTES = MAX_DOCUMENT_BYTES
MAX_VERIFICATION_FILES = 256
MAX_VERIFICATION_TOTAL_BYTES = 16 * 1_048_576
MAX_EVIDENCE_LOCATOR_REFERENCES = 256
MAX_GIT_OUTPUT_BYTES = MAX_DOCUMENT_BYTES
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000
MAX_JSON_CONTAINER_ITEMS = 10_000
MAX_JSON_STRING_CHARACTERS = 262_144
MAX_VERIFICATION_DIAGNOSTICS = 128
MAX_AUTHORITY_WALK_ENTRIES = 4_096
MAX_REPOSITORY_WALK_ENTRIES = 100_000
MAX_REPOSITORY_WALK_DEPTH = 32
DIAGNOSTIC_LIMIT_MESSAGE = "verification diagnostic limit exceeded"
FROZEN_V02_PROFILE_ARTIFACT_SHA256 = MappingProxyType(
    {
        "docs/DEMAND-TO-CAPABILITY-PROFILE.md": (
            "1630f188f5f924fcba7f19b8431b48eac2e4a3ca6d37a5bc99cc1df085d4995a"
        ),
        "adapters/agent-autonomy-harness-codex/skills/"
        "deliver-demand-driven-task/SKILL.md": (
            "abb5906eeface94100b278e4ac182c39893a6be86a5de52577318164dc77103f"
        ),
        "adapters/agent-autonomy-harness-claude/skills/"
        "deliver-demand-driven-task/SKILL.md": (
            "abb5906eeface94100b278e4ac182c39893a6be86a5de52577318164dc77103f"
        ),
    }
)
EXPECTED_PROGRESSION_POLICY = {
    "readyState": "nonterminal-empty-graph-open-to-next-causally-justified-increment",
    "noNaturalTaskDisposition": "outcome-gate-not-program-completion-or-blocker",
    "boundProductDeliveryDemandDisposition": (
        "authorized-product-plan-delivery-is-real-demand-when-its-primary-purpose-is-the-"
        "deliverable-rather-than-exercising-or-diagnosing-the-harness"
    ),
    "agentOwnedWithoutInventedUserTask": [
        "retrospective-counterexample-analysis",
        "bounded-portfolio-curation",
        "mechanism-only-validation",
        "authority-defect-repair",
    ],
    "naturalTaskRequiredFor": [
        "outcome-verification",
        "task-time-capability-activation",
        "behavior-or-value-claim",
    ],
    "historicalFailureRole": "counterevidence-and-replanning-input-only",
    "environmentAttributionDisposition": (
        "acceptance-owned-observed-native-minimum-and-user-configured-strata-with-"
        "preregistered-matched-starting-environment-and-attributed-task-time-adaptation"
    ),
    "taskTimeAdaptationDisposition": (
        "pretask-manifest-is-starting-state-agent-executes-supported-authorized-mechanics-"
        "and-records-lifecycle-deltas"
    ),
    "humanOnlyActionDisposition": (
        "agent-detects-minimizes-guides-and-verifies-unavoidable-user-step-while-"
        "prohibited-agent-work-transfer-remains-zero"
    ),
    "versionResolutionDisposition": (
        "resolve-current-suitable-source-per-decision-bind-exact-execution-identity-and-"
        "stop-on-unresolved-moving-target-or-material-drift"
    ),
    "outcomeClaimBoundary": "O1-O5-require-current-acceptance-evidence",
    "userMustNotInventTasks": True,
}
EXPECTED_CAPABILITY_INFLUENCE_BOUNDARY = {
    "agentsMd": "execution-guidance-only",
    "skillsAndHooks": "advisory-execution-input-only",
    "selfAuthoredSkills": "replaceable-host-projections",
    "peripheralEcosystem": "replaceable-capability-input",
    "capabilityCatalogsAndDiscoveryChannels": "adaptive-source-input-only",
    "cannot": [
        "set-product-direction",
        "create-causal-work-without-observed-problem",
        "expand-authority-trust-data-cost-or-side-effects",
        "promote-evidence-acceptance-or-release-state",
        "require-user-capability-product-channel-or-invocation-selection",
        "make-a-fixed-catalog-or-discovery-channel-product-authority",
        "override-bound-user-intent-or-current-product-authority",
    ],
    "routeDeltaFields": [
        "goal",
        "input",
        "deliverable",
        "human-round-trip",
        "authority",
        "side-effect",
        "acceptance",
    ],
    "routeDeltaRule": (
        "a capability route may add a requirement only when source-bound evidence "
        "shows it is causally necessary for the bound task; otherwise reject or "
        "downgrade the route"
    ),
    "conflictRule": "bound-user-intent-and-current-product-authority-win",
    "misfitRule": "reject-or-downgrade-the-capability-route",
}
EXPECTED_HISTORICAL_EVIDENCE_BOUNDARY = {
    "role": "non-authoritative evidence and retrospective counterevidence",
    "productAuthority": False,
    "planningAuthority": False,
    "acceptanceAuthority": False,
    "runtimeAuthority": False,
    "releaseAuthority": False,
    "counterevidenceInput": True,
    "mayTriggerReplanning": True,
}
EXPECTED_V10_RELEASE = {
    "release": "v1.0",
    "state": "stopped-zero-outcome-terminal-proof-attempt",
    "revision": "910ac016f1e5963450e3cfc46f5056ab0a6b04d7",
    "currentAuthority": False,
}
EXPECTED_PRIOR_RELEASE = {
    "release": "v1.1",
    "state": "stopped-zero-outcome-missed-enrollment-attempt",
    "revision": "5ae71bbdd43c0c5dd5a0e120e508bccf9dd9464c",
    "currentAuthority": False,
}
EXPECTED_HISTORICAL_MILESTONES = (
    {
        "release": "v0.1",
        "state": "accepted-repository-control-milestone",
        "revision": "be498f960c9e0587d355291fb24261c91e75cd77",
        "currentAuthority": False,
        "claimLimit": (
            "repository-bound control evidence only; not terminal proposition, "
            "broad user value, software-engineering standard, cross-host, "
            "production, or publication proof"
        ),
    },
    {
        "release": "v0.2",
        "state": "accepted-bounded-calibration-milestone",
        "revision": "0dbcb0af34197e5c35c75d69a1aeacf4fd91b404",
        "currentAuthority": False,
        "claimLimit": (
            "bounded O1-O5 calibration evidence for the fixed natural-task, Codex "
            "reference-host and matched source-gate cohorts only; not the constitution "
            "terminal proposition, sustained live capability and carrier orchestration, "
            "installed product value, universal portability, production, publication, "
            "or release proof"
        ),
    },
    {
        **EXPECTED_V10_RELEASE,
        "claimLimit": (
            "stopped after two independently authorized but zero-registration cohort "
            "generations; O1-O5 remain zero, the revoked cohort and private-evidence cleanup "
            "are historical facts only, and no profile binding, cohort state, task result, "
            "outcome, environment assumption, or completion claim can be inherited by a later "
            "release"
        ),
    },
    {
        **EXPECTED_PRIOR_RELEASE,
        "claimLimit": (
            "stopped after the first post-activation real product-delivery demand received "
            "outcome-bearing assistance before immutable task registration; O1-O5 remain zero, "
            "the revoked cohort and exact private-resource cleanup are historical facts only, "
            "and no profile binding, cohort state, task result, outcome, environment assumption, "
            "or completion claim can be inherited by a later release"
        ),
    },
)
EXPECTED_V10_AUTHORITY_BLOBS = MappingProxyType(
    {
        "product/program.json": (
            "200d98cbf1dce8a8199ac43563413bb04f4ac880b11bd6dd153f34040a7f5f7a"
        ),
        "product/acceptance.json": (
            "97835e30913c4219558433f1aee12fa4837bc7cee2a1fe19538260e935622963"
        ),
    }
)
EXPECTED_V11_AUTHORITY_BLOBS = MappingProxyType(
    {
        "product/program.json": (
            "46569b58bcf62d365aa60e88abd723c6a4df4f94c159f935a7b9048b487a4226"
        ),
        "product/acceptance.json": (
            "cab4a0751116eefc22927a6a591be3b020cb15576afb0e3161d22a57e550d6c9"
        ),
        "harness/control.py": (
            "de577c8b01629cf03266a785c4436bf2cd27e99c39f107cdc770c9f9c86be155"
        ),
    }
)
EXPECTED_ENVIRONMENT_ATTRIBUTION = {
    "scope": "all O1-O5 registrations, measurements, comparisons, adapter claims and release evidence",
    "environmentClasses": ["observed-native-minimum", "user-configured"],
    "treatmentArms": ["without-harness", "with-exact-harness"],
    "assignmentRule": (
        "each natural task-host execution unit runs once in one pre-registered arm; no same-host "
        "treatment replay merely for measurement, O5 cross-host replication is pre-registered "
        "portability evidence, and a paired baseline must be a pre-registered comparable historical "
        "or independent natural task"
    ),
    "comparisonRule": (
        "compare only pre-registered matched tasks within the same environment class, fixed task-relevant "
        "starting manifest and initial authority-and-available-source envelope; exact Harness package and "
        "activation identity is the only planned initial route and configuration difference, while later "
        "capability and configuration changes are attributed treatment-mediated lifecycle deltas; unavoidable "
        "task differences remain explicit matching variables, the evidence is prospective matched observational "
        "rather than single-variable causal, and cross-class differences cannot be claimed as Harness effects"
    ),
    "initialStateRule": (
        "the committed pre-task manifest and initial authority-and-available-source envelope define the "
        "starting condition, not a static capability ceiling; task-time Agent-selected or human-authorized "
        "changes are recorded as treatment-mediated lifecycle deltas rather than erased, normalized away or "
        "mislabeled as baseline contamination"
    ),
    "observedNativeMinimumRule": (
        "exclude discoverable user-global instructions, configuration, rules, Skills, plugins, Apps, "
        "MCP, Hooks, memory and provider overrides at the starting boundary; task-inherent project guidance is allowed only "
        "when identical and non-Harness in both arms; system, developer, built-in, account, "
        "administrator and unobservable state is retained-or-unknown; after demand, governed task-time adaptation remains allowed and attributable"
    ),
    "userConfiguredRule": (
        "freeze the actual task-relevant user starting environment before assignment; after demand, governed "
        "task-time adaptation remains allowed and attributable; mutable, unresolved, unavailable or drifting "
        "starting components narrow the claim or stop the pair and cannot be normalized away after observing a result"
    ),
    "neutralWorkspaceRule": (
        "a without-Harness baseline cannot inherit Harness repository guidance, adapters or consumer "
        "projection; use a neutral workspace or the real target repository with identical task-inherent "
        "non-Harness guidance in both arms"
    ),
    "taskTimeAdaptationRule": (
        "after demand reveals need, the Agent uses a healthy already-authorized route or, before execution, "
        "binds an immutable decision record covering the residual gap, current source resolution, authority "
        "class, planned lifecycle action, rollback and cleanup; online AI is the normal route, while local, "
        "edge or offline execution is a demand-triggered minimum-sufficient degradation or data-locality route "
        "rather than a mandatory product line, and recovery to an online route is reconciled and attributed; "
        "the Agent performs every supported authorized mechanic, while a technically or authoritatively human-"
        "only action is reduced to the smallest exact step, explained without requiring route knowledge, and "
        "verified before resuming"
    ),
    "versionResolutionRule": (
        "at each decision resolve the current suitable official or maintained source from a bounded as-of source "
        "and bind the exact version, commit or package identity before acquisition or execution; use current "
        "evidence, not one historical version across tasks, never execute an unresolved mutable label "
        "such as latest, and on material mid-execution drift re-register or honestly stop"
    ),
    "lifecycleRule": (
        "retain, install, configure, enable, use, switch between online and local or edge execution, degrade, "
        "restore, disable, downgrade, rollback, retire or persist a route only by current need, evidence and "
        "authority; preserve the same quality, privacy, safety, evidence and human-authority floors across route "
        "changes, end task-scoped exposure when the need ends unless persistence has separate net-value evidence "
        "and authorization, then verify the final or restored state and cleanup"
    ),
    "humanInterventionRule": (
        "distinguish a technically or authoritatively unavoidable human-only decision or host action from a "
        "prohibited transfer of Agent-owned work; the former must be source-bound, minimal, explicitly guided "
        "and post-verified, while the user never has to discover or name the route, configuration variable, "
        "syntax, recovery or cleanup and the Agent performs every supported authorized mechanic"
    ),
    "burdenRule": (
        "record all human actions and round trips in total burden, classify legitimate human-only actions "
        "separately from prohibited Agent-work transfers, require zero prohibited transfers, and do not hide "
        "excessive or avoidable human-only interaction from O2 comparison"
    ),
    "manifestFields": [
        "host-client-and-version",
        "model-provider-and-reasoning",
        "account-managed-and-administrator-requirements-presence",
        "system-developer-and-built-in-state-observed-or-unknown",
        "cwd-repository-and-project-instruction-chain",
        "configuration-layers-profiles-and-overrides",
        "rules-skills-plugins-apps-mcp-hooks-memory-and-managers",
        "operating-system-runtime-tool-and-resource-surface",
        "initial-authority-and-available-source-envelope",
        "exact-harness-package-activation-and-task-exposure-delta",
        "capture-time-source-identities-fingerprint-and-drift-check",
    ],
    "historicalEvidenceRule": (
        "classify every reused historical item as environment-independent, environment-bound or "
        "invalidated; no prior outcome, cohort membership or environment assumption is inherited"
    ),
    "driftRule": (
        "missing starting identity, mutable unbound dependencies, unknown material contamination, unregistered "
        "lifecycle drift or restoration failure stops the affected pair without replacement or success imputation; "
        "an official update between tasks is re-resolved and rebound rather than treated as permanent version drift"
    ),
    "humanAuthority": (
        "The user authorizes access to private configuration or authentication state, protected backup, "
        "reset or restoration, a new OS account or trust boundary, installation, publication and "
        "irreversible effects, and performs a technically or authoritatively unavoidable host action only "
        "under minimal exact Agent guidance; the Agent owns need detection, recommendation, every supported "
        "authorized mechanic, post-action verification, restoration verification and exact cleanup."
    ),
}
EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256 = hashlib.sha256(
    json.dumps(
        EXPECTED_ENVIRONMENT_ATTRIBUTION,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


EvidenceValidator = Callable[[dict[str, Any], str, Path, list[str]], bool]
EvidenceValidatorSpec = tuple[
    frozenset[str],
    frozenset[str],
    str,
    EvidenceValidator,
]
PreMeasurementValidator = Callable[
    [dict[str, Any], dict[str, Any], tuple[str, ...], Path, list[str]],
    bool,
]
PreMeasurementValidatorSpec = tuple[
    frozenset[str],
    frozenset[str],
    str,
    PreMeasurementValidator,
]
HumanAuthorizationValidator = Callable[
    [dict[str, Any], Path, list[str]],
    bool,
]
TerminalAuthorizationValidatorSpec = tuple[str, HumanAuthorizationValidator]


class _WindowsCredentialFileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class _WindowsCredential(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint32),
        ("credential_type", ctypes.c_uint32),
        ("target_name", ctypes.c_void_p),
        ("comment", ctypes.c_void_p),
        ("last_written", _WindowsCredentialFileTime),
        ("credential_blob_size", ctypes.c_uint32),
        ("credential_blob", ctypes.c_void_p),
        ("persist", ctypes.c_uint32),
        ("attribute_count", ctypes.c_uint32),
        ("attributes", ctypes.c_void_p),
        ("target_alias", ctypes.c_void_p),
        ("user_name", ctypes.c_void_p),
    ]


class _WindowsSidAndAttributes(ctypes.Structure):
    _fields_ = [("sid", ctypes.c_void_p), ("attributes", ctypes.c_uint32)]


class _WindowsTokenUser(ctypes.Structure):
    _fields_ = [("user", _WindowsSidAndAttributes)]


class _WindowsOverlapped(ctypes.Structure):
    _fields_ = [
        ("internal", ctypes.c_void_p),
        ("internal_high", ctypes.c_void_p),
        ("offset", ctypes.c_uint32),
        ("offset_high", ctypes.c_uint32),
        ("event", ctypes.c_void_p),
    ]


def _initial_authorization_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate private evidence key")
        value[key] = item
    return value


def _read_cohort_authorization_private_evidence(
    credential_filter: str,
    expected_fields: set[str],
    generation_label: str,
    errors: list[str],
) -> tuple[dict[str, Any], str] | None:
    diagnostic = f"{generation_label} authorization private source"
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        _error(errors, f"{diagnostic} is unavailable")
        return None
    try:
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        enumerate_credentials = advapi32.CredEnumerateW
        enumerate_credentials.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        enumerate_credentials.restype = ctypes.c_int
        free_credentials = advapi32.CredFree
        free_credentials.argtypes = [ctypes.c_void_p]
        free_credentials.restype = None
        count = ctypes.c_uint32()
        credentials = ctypes.c_void_p()
        available = enumerate_credentials(
            credential_filter,
            0,
            ctypes.byref(count),
            ctypes.byref(credentials),
        )
        if not available or not credentials.value:
            if credentials.value:
                free_credentials(credentials)
            _error(errors, f"{diagnostic} is unavailable")
            return None
        try:
            if count.value != 1:
                _error(
                    errors,
                    f"{diagnostic} is unavailable",
                )
                return None
            credential_array = ctypes.cast(
                credentials,
                ctypes.POINTER(ctypes.POINTER(_WindowsCredential)),
            )
            credential = credential_array[0].contents
            if (
                credential.credential_type != 1
                or credential.persist != 2
                or not credential.target_name
                or credential.credential_blob_size == 0
                or credential.credential_blob_size
                > MAX_INITIAL_AUTHORIZATION_CREDENTIAL_BYTES
                or not credential.credential_blob
            ):
                _error(errors, f"{diagnostic} is invalid")
                return None
            target_name = ctypes.wstring_at(credential.target_name)
            if not target_name:
                _error(errors, f"{diagnostic} is invalid")
                return None
            raw = ctypes.string_at(
                credential.credential_blob,
                credential.credential_blob_size,
            )
        finally:
            free_credentials(credentials)
        value = json.loads(
            raw,
            object_pairs_hook=_initial_authorization_json_object,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"non-finite private evidence value: {constant}")
            ),
        )
    except (
        OSError,
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
        json.JSONDecodeError,
    ):
        _error(errors, f"{diagnostic} is invalid")
        return None
    if not isinstance(value, dict) or set(value) != expected_fields:
        _error(errors, f"{diagnostic} is invalid")
        return None
    return value, target_name


def _read_initial_authorization_private_evidence(
    errors: list[str],
) -> tuple[dict[str, Any], str] | None:
    return _read_cohort_authorization_private_evidence(
        INITIAL_AUTHORIZATION_CREDENTIAL_FILTER,
        INITIAL_BINDING_PRIVATE_EVIDENCE_FIELDS,
        "initial binding",
        errors,
    )


def _read_successor_authorization_private_evidence(
    errors: list[str],
) -> tuple[dict[str, Any], str] | None:
    return _read_cohort_authorization_private_evidence(
        SUCCESSOR_AUTHORIZATION_CREDENTIAL_FILTER,
        SUCCESSOR_BINDING_PRIVATE_EVIDENCE_FIELDS,
        "successor binding",
        errors,
    )


def _read_current_initial_authorization_private_evidence(
    errors: list[str],
) -> tuple[dict[str, Any], str] | None:
    return _read_cohort_authorization_private_evidence(
        CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_FILTER,
        CURRENT_INITIAL_BINDING_PRIVATE_EVIDENCE_FIELDS,
        "current v1.1 binding",
        errors,
    )


def _cohort_authorization_private_resource_absent(
    credential_filter: str, generation_label: str, errors: list[str]
) -> bool:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return True
    try:
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        enumerate_credentials = advapi32.CredEnumerateW
        enumerate_credentials.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        enumerate_credentials.restype = ctypes.c_int
        free_credentials = advapi32.CredFree
        free_credentials.argtypes = [ctypes.c_void_p]
        free_credentials.restype = None
        count = ctypes.c_uint32()
        credentials = ctypes.c_void_p()
        ctypes.set_last_error(0)
        available = enumerate_credentials(
            credential_filter,
            0,
            ctypes.byref(count),
            ctypes.byref(credentials),
        )
        enumerate_error = ctypes.get_last_error()
        if credentials.value:
            free_credentials(credentials)
        if available or count.value != 0:
            _error(errors, f"revoked {generation_label} private resource still exists")
            return False
        if enumerate_error != 1168:
            _error(
                errors,
                f"revoked {generation_label} private resource absence is unverifiable",
            )
            return False
    except (OSError, ValueError, TypeError):
        _error(
            errors,
            f"revoked {generation_label} private resource absence is unverifiable",
        )
        return False
    return True


def _initial_authorization_private_resource_absent(errors: list[str]) -> bool:
    return _cohort_authorization_private_resource_absent(
        INITIAL_AUTHORIZATION_CREDENTIAL_FILTER,
        "initial binding",
        errors,
    )


def _successor_authorization_private_resource_absent(errors: list[str]) -> bool:
    return _cohort_authorization_private_resource_absent(
        SUCCESSOR_AUTHORIZATION_CREDENTIAL_FILTER,
        "successor binding",
        errors,
    )


def _current_initial_authorization_private_resource_absent(
    errors: list[str],
) -> bool:
    return _cohort_authorization_private_resource_absent(
        CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_FILTER,
        "current v1.1 binding",
        errors,
    )


def _initial_authorization_string_hmac(
    key: bytes | bytearray, domain: str, *parts: str
) -> str:
    message = "\0".join((domain, *parts)).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


def _initial_authorization_bytes_hmac(
    key: bytes | bytearray, domain: str, payload: bytes
) -> str:
    message = domain.encode("utf-8") + b"\0" + payload
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


def _cohort_authorization_credential_target_valid(
    target_name: str,
    key: bytes | bytearray,
    domain: str,
    expected: str | None,
    generation_label: str,
    errors: list[str],
) -> bool:
    commitment = _initial_authorization_string_hmac(
        key,
        domain,
        target_name,
    )
    if expected is None or not hmac.compare_digest(commitment, expected):
        _error(
            errors,
            f"{generation_label} authorization private source identity is invalid",
        )
        return False
    return True


def _initial_authorization_credential_target_valid(
    target_name: str, key: bytes | bytearray, errors: list[str]
) -> bool:
    return _cohort_authorization_credential_target_valid(
        target_name,
        key,
        INITIAL_AUTHORIZATION_TARGET_HMAC_DOMAIN,
        EXPECTED_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT,
        "initial binding",
        errors,
    )


def _successor_authorization_credential_target_valid(
    target_name: str, key: bytes | bytearray, errors: list[str]
) -> bool:
    return _cohort_authorization_credential_target_valid(
        target_name,
        key,
        SUCCESSOR_AUTHORIZATION_TARGET_HMAC_DOMAIN,
        EXPECTED_SUCCESSOR_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT,
        "successor binding",
        errors,
    )


def _current_initial_authorization_credential_target_valid(
    target_name: str, key: bytes | bytearray, errors: list[str]
) -> bool:
    return _cohort_authorization_credential_target_valid(
        target_name,
        key,
        CURRENT_INITIAL_AUTHORIZATION_TARGET_HMAC_DOMAIN,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT,
        "current v1.1 binding",
        errors,
    )


def _current_initial_authorization_private_resource_identity_valid(
    resource: tuple[dict[str, Any], str], errors: list[str]
) -> bool:
    private_evidence, target_name = resource
    encoded_key = private_evidence.get("keyBase64")
    if not isinstance(encoded_key, str):
        _error(errors, "current v1.1 binding authorization private source is invalid")
        return False
    try:
        key = bytearray(base64.b64decode(encoded_key, validate=True))
    except (ValueError, TypeError):
        _error(errors, "current v1.1 binding authorization private source is invalid")
        return False
    try:
        expected_fingerprint = EXPECTED_CURRENT_INITIAL_AUTHORIZATION_KEY_FINGERPRINT
        if (
            len(key) != 32
            or not isinstance(expected_fingerprint, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", expected_fingerprint) is None
            or not hmac.compare_digest(
                "sha256:" + hashlib.sha256(key).hexdigest(),
                expected_fingerprint,
            )
        ):
            _error(errors, "current v1.1 binding authorization private source is invalid")
            return False
        return _current_initial_authorization_credential_target_valid(
            target_name,
            key,
            errors,
        )
    finally:
        key[:] = b"\0" * len(key)


def _successor_authorization_private_resource_identity_valid(
    resource: tuple[dict[str, Any], str], errors: list[str]
) -> bool:
    private_evidence, target_name = resource
    encoded_key = private_evidence.get("keyBase64")
    if not isinstance(encoded_key, str):
        _error(errors, "successor binding authorization private source is invalid")
        return False
    try:
        key = bytearray(base64.b64decode(encoded_key, validate=True))
    except (ValueError, TypeError):
        _error(errors, "successor binding authorization private source is invalid")
        return False
    try:
        if len(key) != 32 or not hmac.compare_digest(
            "sha256:" + hashlib.sha256(key).hexdigest(),
            EXPECTED_SUCCESSOR_AUTHORIZATION_KEY_FINGERPRINT,
        ):
            _error(errors, "successor binding authorization private source is invalid")
            return False
        return _successor_authorization_credential_target_valid(
            target_name,
            key,
            errors,
        )
    finally:
        key[:] = b"\0" * len(key)


def _windows_system_drive() -> str | None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return None
    try:
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_windows_directory = kernel32.GetWindowsDirectoryW
        get_windows_directory.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        get_windows_directory.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32_768)
        length = get_windows_directory(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            return None
        drive = PureWindowsPath(buffer.value).drive
    except (OSError, ValueError):
        return None
    return drive.upper() if re.fullmatch(r"[A-Za-z]:", drive) else None


def _windows_drive_is_fixed(drive: str) -> bool:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return False
    try:
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_drive_type = kernel32.GetDriveTypeW
        get_drive_type.argtypes = [ctypes.c_wchar_p]
        get_drive_type.restype = ctypes.c_uint32
        return get_drive_type(drive + "\\") == 3
    except (OSError, ValueError):
        return False


def _cohort_authorization_source_locator_parts(
    source_locator: str,
    key: bytes | bytearray,
    domain: str,
    expected_root: str | None,
    generation_label: str,
    errors: list[str],
) -> tuple[str, str] | None:
    diagnostic = f"{generation_label} authorization source event"
    try:
        pure = PureWindowsPath(source_locator)
        normalized = str(pure)
    except (TypeError, ValueError):
        _error(errors, f"{diagnostic} is invalid")
        return None
    relative_parts = pure.parts[1:]
    if (
        not source_locator
        or source_locator.startswith("\\\\")
        or not pure.is_absolute()
        or re.fullmatch(r"[A-Za-z]:", pure.drive) is None
        or source_locator.replace("/", "\\") != normalized
        or any(part in {".", ".."} or ":" in part for part in relative_parts)
        or not pure.name.startswith("rollout-")
        or pure.suffix.casefold() != ".jsonl"
        or len(pure.parents) < 4
    ):
        _error(errors, f"{diagnostic} is invalid")
        return None
    day_root = pure.parent
    month_root = day_root.parent
    year_root = month_root.parent
    source_root = year_root.parent
    if (
        re.fullmatch(r"\d{2}", day_root.name) is None
        or re.fullmatch(r"\d{2}", month_root.name) is None
        or re.fullmatch(r"\d{4}", year_root.name) is None
        or source_root.name.casefold() != "sessions"
        or source_root.parent.name.casefold() != ".codex"
    ):
        _error(errors, f"{diagnostic} is invalid")
        return None
    system_drive = _windows_system_drive()
    if (
        system_drive is None
        or pure.drive.casefold() != system_drive.casefold()
        or not _windows_drive_is_fixed(system_drive)
    ):
        _error(errors, f"{diagnostic} is invalid")
        return None
    root_commitment = _initial_authorization_string_hmac(
        key,
        domain,
        str(source_root).casefold(),
    )
    if expected_root is None or not hmac.compare_digest(
        root_commitment, expected_root
    ):
        _error(errors, f"{diagnostic} is invalid")
        return None
    return normalized, str(source_root)


def _initial_authorization_source_locator_parts(
    source_locator: str,
    key: bytes | bytearray,
    errors: list[str],
) -> tuple[str, str] | None:
    return _cohort_authorization_source_locator_parts(
        source_locator,
        key,
        INITIAL_AUTHORIZATION_SOURCE_ROOT_HMAC_DOMAIN,
        EXPECTED_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT,
        "initial binding",
        errors,
    )


def _successor_authorization_source_locator_parts(
    source_locator: str,
    key: bytes | bytearray,
    errors: list[str],
) -> tuple[str, str] | None:
    return _cohort_authorization_source_locator_parts(
        source_locator,
        key,
        SUCCESSOR_AUTHORIZATION_SOURCE_ROOT_HMAC_DOMAIN,
        EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_ROOT_COMMITMENT,
        "successor binding",
        errors,
    )


def _current_initial_authorization_source_locator_parts(
    source_locator: str,
    key: bytes | bytearray,
    errors: list[str],
) -> tuple[str, str] | None:
    return _cohort_authorization_source_locator_parts(
        source_locator,
        key,
        CURRENT_INITIAL_AUTHORIZATION_SOURCE_ROOT_HMAC_DOMAIN,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT,
        "current v1.1 binding",
        errors,
    )


def _open_initial_authorization_source(path: Path):
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return None
    try:
        import msvcrt

        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        handle = create_file(
            str(path),
            0x80000000,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x00000080 | 0x00200000 | 0x08000000,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if not handle or handle == invalid_handle:
            return None
        try:
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
        except OSError:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return None
        try:
            return os.fdopen(descriptor, "rb", closefd=True)
        except (OSError, ValueError):
            os.close(descriptor)
            return None
    except (OSError, ValueError):
        return None


def _lock_initial_authorization_source(stream, size: int) -> _WindowsOverlapped | None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL") or size <= 0:
        return None
    try:
        import msvcrt

        handle = msvcrt.get_osfhandle(stream.fileno())
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        lock_file = kernel32.LockFileEx
        lock_file.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(_WindowsOverlapped),
        ]
        lock_file.restype = ctypes.c_int
        overlapped = _WindowsOverlapped()
        if not lock_file(
            ctypes.c_void_p(handle),
            0x00000001 | 0x00000002,
            0,
            size & 0xFFFFFFFF,
            (size >> 32) & 0xFFFFFFFF,
            ctypes.byref(overlapped),
        ):
            return None
        return overlapped
    except (OSError, ValueError):
        return None


def _unlock_initial_authorization_source(
    stream, size: int, overlapped: _WindowsOverlapped
) -> None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL") or size <= 0:
        return
    try:
        import msvcrt

        handle = msvcrt.get_osfhandle(stream.fileno())
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        unlock_file = kernel32.UnlockFileEx
        unlock_file.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(_WindowsOverlapped),
        ]
        unlock_file.restype = ctypes.c_int
        unlock_file(
            ctypes.c_void_p(handle),
            0,
            size & 0xFFFFFFFF,
            (size >> 32) & 0xFFFFFFFF,
            ctypes.byref(overlapped),
        )
    except (OSError, ValueError):
        return


def _initial_authorization_opened_final_path(stream) -> str | None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return None
    try:
        import msvcrt

        handle = msvcrt.get_osfhandle(stream.fileno())
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_final_path = kernel32.GetFinalPathNameByHandleW
        get_final_path.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        get_final_path.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32_768)
        length = get_final_path(
            ctypes.c_void_p(handle),
            buffer,
            len(buffer),
            0,
        )
        if length == 0 or length >= len(buffer):
            return None
        final_path = buffer.value
    except (OSError, ValueError):
        return None
    if final_path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + final_path[8:]
    if final_path.startswith("\\\\?\\"):
        return final_path[4:]
    return final_path


def _initial_authorization_file_state(value: os.stat_result) -> tuple[int, ...]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_size),
        int(value.st_mtime_ns),
    )


def _normalized_native_path(value: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(value))))


def _read_stable_initial_authorization_snapshot(
    source_path: Path,
    authorized_root: str,
    errors: list[str],
    *,
    generation_label: str = "initial binding",
) -> bytes | None:
    diagnostic = f"{generation_label} authorization source event"
    try:
        source_stat = source_path.lstat()
        parent_stats = [parent.lstat() for parent in source_path.parents[:-1]]
    except (OSError, ValueError):
        _error(errors, f"{diagnostic} is unavailable")
        return None
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not source_path.is_absolute()
        or not stat.S_ISREG(source_stat.st_mode)
        or source_stat.st_ino <= 0
        or getattr(source_stat, "st_file_attributes", 0) & reparse_flag
        or any(
            getattr(parent_stat, "st_file_attributes", 0) & reparse_flag
            for parent_stat in parent_stats
        )
    ):
        _error(errors, f"{diagnostic} is invalid")
        return None
    stream = _open_initial_authorization_source(source_path)
    if stream is None:
        _error(errors, f"{diagnostic} is unavailable")
        return None
    locked: _WindowsOverlapped | None = None
    opened_size = 0
    try:
        try:
            opened_stat = os.fstat(stream.fileno())
            final_path = _initial_authorization_opened_final_path(stream)
            normalized_source = _normalized_native_path(source_path)
            normalized_root = _normalized_native_path(authorized_root)
            normalized_final = (
                _normalized_native_path(final_path) if final_path is not None else None
            )
            inside_root = (
                normalized_final is not None
                and os.path.commonpath([normalized_final, normalized_root])
                == normalized_root
            )
        except (OSError, ValueError):
            _error(errors, f"{diagnostic} is unavailable")
            return None
        if (
            not stat.S_ISREG(opened_stat.st_mode)
            or opened_stat.st_ino <= 0
            or getattr(opened_stat, "st_file_attributes", 0) & reparse_flag
            or opened_stat.st_size <= 0
            or opened_stat.st_size > MAX_INITIAL_AUTHORIZATION_SOURCE_BYTES
            or _initial_authorization_file_state(source_stat)
            != _initial_authorization_file_state(opened_stat)
            or normalized_final != normalized_source
            or not inside_root
        ):
            _error(errors, f"{diagnostic} is invalid")
            return None
        opened_size = opened_stat.st_size
        locked = _lock_initial_authorization_source(stream, opened_size)
        if locked is None:
            _error(errors, f"{diagnostic} is unavailable")
            return None
        try:
            snapshot = stream.read(opened_stat.st_size + 1)
            final_stat = os.fstat(stream.fileno())
        except OSError:
            _error(errors, f"{diagnostic} is unavailable")
            return None
        if (
            len(snapshot) != opened_stat.st_size
            or _initial_authorization_file_state(opened_stat)
            != _initial_authorization_file_state(final_stat)
        ):
            _error(errors, f"{diagnostic} changed during validation")
            return None
        return snapshot
    finally:
        if locked is not None:
            _unlock_initial_authorization_source(stream, opened_size, locked)
        stream.close()


def _initial_authorization_snapshot_valid(
    private_evidence: Mapping[str, Any],
    snapshot: bytes,
    key: bytes | bytearray,
    errors: list[str],
) -> bool:
    source_identity = private_evidence.get("sourceEventIdentity")
    source_timestamp = private_evidence.get("sourceEventTimestamp")
    surface_identity = private_evidence.get("surfaceIdentity")
    if (
        not isinstance(source_identity, str)
        or not isinstance(source_timestamp, str)
        or not isinstance(surface_identity, str)
        or not isinstance(snapshot, bytes)
        or not snapshot
        or len(snapshot) > MAX_INITIAL_AUTHORIZATION_SOURCE_BYTES
    ):
        _error(errors, "initial binding authorization source event is invalid")
        return False
    try:
        source_instant = datetime.fromisoformat(
            source_timestamp.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except ValueError:
        _error(errors, "initial binding authorization source event is invalid")
        return False
    activation_found = False
    record_count = 0
    cursor = 0
    stream = BytesIO(snapshot)
    while cursor < len(snapshot):
        line = stream.readline(MAX_INITIAL_AUTHORIZATION_SOURCE_LINE_BYTES + 1)
        if not line:
            break
        cursor += len(line)
        record_count += 1
        if (
            record_count > MAX_INITIAL_AUTHORIZATION_SOURCE_RECORDS
            or len(line) > MAX_INITIAL_AUTHORIZATION_SOURCE_LINE_BYTES
        ):
            _error(
                errors,
                "initial binding authorization source event exceeds its finite bounds",
            )
            return False
        try:
            event = json.loads(
                line,
                object_pairs_hook=_initial_authorization_json_object,
                parse_constant=lambda constant: (_ for _ in ()).throw(
                    ValueError(f"non-finite source event value: {constant}")
                ),
            )
        except (
            UnicodeError,
            ValueError,
            TypeError,
            RecursionError,
            json.JSONDecodeError,
        ):
            _error(errors, "initial binding authorization source event is invalid")
            return False
        if not isinstance(event, dict) or event.get("type") != "event_msg":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "user_message":
            continue
        event_identity = payload.get("client_id")
        event_message = payload.get("message")
        event_timestamp = event.get("timestamp")
        if not isinstance(event_identity, str) or not isinstance(event_message, str):
            _error(errors, "initial binding authorization source event is invalid")
            return False
        normalized_message = event_message.rstrip("\r\n")
        if event_identity == source_identity:
            try:
                event_instant = (
                    datetime.fromisoformat(
                        event_timestamp.replace("Z", "+00:00")
                    ).astimezone(timezone.utc)
                    if isinstance(event_timestamp, str)
                    and RFC3339.fullmatch(event_timestamp) is not None
                    else None
                )
            except ValueError:
                event_instant = None
            if (
                activation_found
                or event_instant != source_instant
                or normalized_message != "授权！"
            ):
                _error(errors, "initial binding activation source event is invalid")
                return False
            activation_found = True
            continue
        if not activation_found:
            continue
        message_sha256 = hashlib.sha256(
            normalized_message.encode("utf-8")
        ).hexdigest()
        if not hmac.compare_digest(
            message_sha256,
            EXPECTED_INITIAL_BINDING_AUTHORIZATION_MESSAGE_SHA256,
        ):
            _error(
                errors,
                "natural demand appeared before exact first-freeze authorization",
            )
            return False
        try:
            authorization_instant = (
                datetime.fromisoformat(
                    event_timestamp.replace("Z", "+00:00")
                ).astimezone(timezone.utc)
                if isinstance(event_timestamp, str)
                and RFC3339.fullmatch(event_timestamp) is not None
                else None
            )
        except ValueError:
            authorization_instant = None
        if (
            re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                event_identity,
            )
            is None
            or authorization_instant is None
            or authorization_instant < source_instant
        ):
            _error(errors, "initial binding authorization source event is invalid")
            return False
        canonical_timestamp = authorization_instant.isoformat().replace(
            "+00:00", "Z"
        )
        event_commitment = _initial_authorization_string_hmac(
            key,
            INITIAL_AUTHORIZATION_EVENT_HMAC_DOMAIN,
            surface_identity,
            source_identity,
            event_identity,
            canonical_timestamp,
            normalized_message,
        )
        window_commitment = _initial_authorization_bytes_hmac(
            key,
            INITIAL_AUTHORIZATION_WINDOW_HMAC_DOMAIN,
            snapshot[:cursor],
        )
        if (
            EXPECTED_INITIAL_AUTHORIZATION_EVENT_COMMITMENT is None
            or EXPECTED_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT is None
            or not hmac.compare_digest(
                event_commitment,
                EXPECTED_INITIAL_AUTHORIZATION_EVENT_COMMITMENT,
            )
            or not hmac.compare_digest(
                window_commitment,
                EXPECTED_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT,
            )
        ):
            _error(errors, "initial binding authorization source event is invalid")
            return False
        return True
    _error(
        errors,
        "initial frozen normative profile binding authorization source was not independently verified",
    )
    return False


def _initial_authorization_event_window_valid(
    private_evidence: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
    errors: list[str],
    *,
    credential_target_name: str | None = None,
) -> bool:
    expected_public = {
        "schema": 1,
        "kind": "agent-autonomy-harness-v1-provisional-cohort-private-evidence",
        "surfaceIdentity": "enrollment-surface.public-v1:f0e705cf4cc54e13afdc993442811187",
        "activationCursorCommitment": "hmac-sha256:e6038957ab84aea02af9c45ee8e19277e9cf14045634345571ed0b62d866003a",
        "keyIdentity": "cohort-key.public-v1:2d81fdcaa26da32778089bb53198e190",
        "keyFingerprint": EXPECTED_INITIAL_AUTHORIZATION_KEY_FINGERPRINT,
        "sourceKind": "codex-rollout-user-event-v1",
        "disposition": (
            "authorized-retain-through-v1-accepted-or-stopped-no-later-than-"
            "2026-12-31T23:59:59+08:00-delete-and-revoke-on-withdrawal-expiry-"
            "stop-or-validation-failure"
        ),
    }
    if type(private_evidence.get("schema")) is not int or any(
        private_evidence.get(key) != item for key, item in expected_public.items()
    ):
        _error(
            errors,
            "initial binding authorization private source does not match the frozen activation",
        )
        return False
    source_identity = private_evidence.get("sourceEventIdentity")
    source_timestamp = private_evidence.get("sourceEventTimestamp")
    source_locator = private_evidence.get("sourceRollout")
    encoded_key = private_evidence.get("keyBase64")
    if (
        not isinstance(source_identity, str)
        or re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            source_identity,
        )
        is None
        or not isinstance(source_timestamp, str)
        or RFC3339.fullmatch(source_timestamp) is None
        or not isinstance(source_locator, str)
        or not isinstance(encoded_key, str)
    ):
        _error(errors, "initial binding authorization private source is invalid")
        return False
    try:
        key = bytearray(base64.b64decode(encoded_key, validate=True))
    except (ValueError, TypeError):
        _error(errors, "initial binding authorization private source is invalid")
        return False
    try:
        if len(key) != 32:
            _error(errors, "initial binding authorization private source is invalid")
            return False
        fingerprint = "sha256:" + hashlib.sha256(key).hexdigest()
        activation_message = (
            EXPECTED_HMAC_DOMAIN
            + "\0"
            + expected_public["surfaceIdentity"]
            + "\0"
            + source_identity
        ).encode("utf-8")
        commitment = "hmac-sha256:" + hmac.new(
            key, activation_message, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(
            fingerprint, expected_public["keyFingerprint"]
        ) or not hmac.compare_digest(
            commitment,
            expected_public["activationCursorCommitment"],
        ):
            _error(
                errors,
                "initial binding authorization private source does not match the frozen activation",
            )
            return False
        if credential_target_name is None or not _initial_authorization_credential_target_valid(
            credential_target_name,
            key,
            errors,
        ):
            return False
        locator_parts = _initial_authorization_source_locator_parts(
            source_locator,
            key,
            errors,
        )
        if locator_parts is None:
            return False
        source_path_text, authorized_root = locator_parts
        snapshot = _read_stable_initial_authorization_snapshot(
            Path(source_path_text),
            authorized_root,
            errors,
        )
        if snapshot is None:
            return False
        return _initial_authorization_snapshot_valid(
            private_evidence,
            snapshot,
            key,
            errors,
        )
    finally:
        key[:] = b"\0" * len(key)


def _current_initial_materialization_authorization_message() -> str:
    return (
        "正式授权 Agent 在当前 Windows 用户保护存储中创建仅用于 Agent Autonomy "
        "Harness v1.1 cohort 的新随机私密资源，并安装仅针对该精确资源的一次性到期"
        "清理触发器；triggerIdentity="
        + CURRENT_INITIAL_EXPIRY_TASK_NAME
        + "@"
        + CURRENT_INITIAL_EXPIRY_TASK_START_BOUNDARY
        + "；环境归因合同 SHA-256="
        + EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
        + "；环境清单边界="
        + EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY
        + "；私密证据处置="
        + EXPECTED_CURRENT_INITIAL_PRIVATE_EVIDENCE_DISPOSITION
        + "；本次仅允许提交 provisional first-freeze binding，不授权激活 cohort、读取或"
        "计入自然任务、安装 Harness 插件或发布；禁止公开私钥、原始事件、会话路径或"
        "凭据定位。"
    )


def _current_initial_activation_authorization_message(
    authorization_document: Mapping[str, Any],
) -> tuple[str, str] | None:
    values = {
        "kind": authorization_document.get("kind"),
        "revision": authorization_document.get("revision"),
        "bindingSha256": authorization_document.get("bindingSha256"),
        "environmentAttributionContractSha256": authorization_document.get(
            "environmentAttributionContractSha256"
        ),
        "environmentManifestBoundary": authorization_document.get(
            "environmentManifestBoundary"
        ),
        "surfaceIdentity": EXPECTED_CURRENT_INITIAL_SURFACE_IDENTITY,
        "activationCursorCommitment": (
            EXPECTED_CURRENT_INITIAL_ACTIVATION_CURSOR_COMMITMENT
        ),
        "keyIdentity": EXPECTED_CURRENT_INITIAL_KEY_IDENTITY,
        "keyFingerprint": EXPECTED_CURRENT_INITIAL_AUTHORIZATION_KEY_FINGERPRINT,
    }
    if any(not isinstance(item, str) for item in values.values()):
        return None
    return (
        "正式授权 Agent Autonomy Harness v1.1 cohort activation：kind="
        + values["kind"]
        + "；revision="
        + values["revision"]
        + "；bindingSha256="
        + values["bindingSha256"]
        + "；environmentAttributionContractSha256="
        + values["environmentAttributionContractSha256"]
        + "；environmentManifestBoundary="
        + values["environmentManifestBoundary"]
        + "；surfaceIdentity="
        + values["surfaceIdentity"]
        + "；sourceKind=codex-rollout-user-event-v1"
        + "；activationCursorCommitment="
        + values["activationCursorCommitment"]
        + "；keyIdentity="
        + values["keyIdentity"]
        + "；keyFingerprint="
        + values["keyFingerprint"]
        + "；privateEvidenceDisposition="
        + EXPECTED_CURRENT_INITIAL_PRIVATE_EVIDENCE_DISPOSITION
        + "；允许代码拥有的验证器仅从当前 Windows 用户保护存储读取该精确 v1.1 "
        "私密资源，核验本次 materialization grant 至本授权事件之间的完整来源窗口、"
        "零遗漏合格自然需求、环境边界、事件连续性和清理约束；禁止公开私钥、原始事件、"
        "会话路径或凭据定位。"
    )


def _current_initial_authorization_snapshot_valid(
    private_evidence: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
    snapshot: bytes,
    key: bytes | bytearray,
    errors: list[str],
) -> bool:
    source_identity = private_evidence.get("sourceEventIdentity")
    source_timestamp = private_evidence.get("sourceEventTimestamp")
    authorization_identity = private_evidence.get("authorizationEventIdentity")
    authorization_timestamp = private_evidence.get("authorizationEventTimestamp")
    surface_identity = private_evidence.get("surfaceIdentity")
    source_instant = _source_event_instant(source_timestamp)
    authorization_instant = _source_event_instant(authorization_timestamp)
    if (
        not isinstance(source_identity, str)
        or not isinstance(authorization_identity, str)
        or source_identity == authorization_identity
        or re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            source_identity,
        )
        is None
        or re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            authorization_identity,
        )
        is None
        or source_instant is None
        or authorization_instant is None
        or authorization_instant < source_instant
        or not isinstance(surface_identity, str)
        or not isinstance(snapshot, bytes)
        or not snapshot
        or len(snapshot) > MAX_INITIAL_AUTHORIZATION_SOURCE_BYTES
    ):
        _error(errors, "current v1.1 binding authorization source event is invalid")
        return False

    expected_materialization_message = (
        _current_initial_materialization_authorization_message()
    )
    expected_authorization_message = (
        _current_initial_activation_authorization_message(authorization_document)
    )
    if expected_authorization_message is None:
        _error(errors, "current v1.1 binding authorization anchors are unavailable")
        return False

    source_found = False
    authorization_found = False
    record_count = 0
    cursor = 0
    stream = BytesIO(snapshot)
    while cursor < len(snapshot):
        line = stream.readline(MAX_INITIAL_AUTHORIZATION_SOURCE_LINE_BYTES + 1)
        if not line:
            break
        cursor += len(line)
        record_count += 1
        if (
            record_count > MAX_INITIAL_AUTHORIZATION_SOURCE_RECORDS
            or len(line) > MAX_INITIAL_AUTHORIZATION_SOURCE_LINE_BYTES
        ):
            _error(
                errors,
                "current v1.1 binding authorization source event exceeds its finite bounds",
            )
            return False
        try:
            event = json.loads(
                line,
                object_pairs_hook=_initial_authorization_json_object,
                parse_constant=lambda constant: (_ for _ in ()).throw(
                    ValueError(f"non-finite source event value: {constant}")
                ),
            )
        except (
            UnicodeError,
            ValueError,
            TypeError,
            RecursionError,
            json.JSONDecodeError,
        ):
            _error(errors, "current v1.1 binding authorization source event is invalid")
            return False
        if not isinstance(event, dict) or event.get("type") != "event_msg":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "user_message":
            continue
        event_identity = payload.get("client_id")
        event_message = payload.get("message")
        event_timestamp = event.get("timestamp")
        if not isinstance(event_identity, str) or not isinstance(event_message, str):
            _error(errors, "current v1.1 binding authorization source event is invalid")
            return False
        event_instant = _source_event_instant(event_timestamp)
        normalized_message = event_message.rstrip("\r\n")
        if event_identity == source_identity:
            if (
                source_found
                or authorization_found
                or event_instant != source_instant
                or not hmac.compare_digest(
                    normalized_message.encode("utf-8"),
                    expected_materialization_message.encode("utf-8"),
                )
            ):
                _error(
                    errors,
                    "current v1.1 binding materialization source event is invalid",
                )
                return False
            source_found = True
            continue
        if not source_found:
            continue
        if event_identity != authorization_identity:
            _error(
                errors,
                "natural demand appeared before exact current v1.1 first-freeze authorization",
            )
            return False
        if (
            authorization_found
            or event_instant != authorization_instant
            or not hmac.compare_digest(
                normalized_message.encode("utf-8"),
                expected_authorization_message.encode("utf-8"),
            )
        ):
            _error(errors, "current v1.1 binding authorization source event is invalid")
            return False
        authorization_found = True
        canonical_timestamp = authorization_instant.isoformat().replace(
            "+00:00", "Z"
        )
        materialization_commitment = _initial_authorization_string_hmac(
            key,
            CURRENT_INITIAL_MATERIALIZATION_EVENT_HMAC_DOMAIN,
            surface_identity,
            source_identity,
            source_instant.isoformat().replace("+00:00", "Z"),
            expected_materialization_message,
        )
        authorization_commitment = _initial_authorization_string_hmac(
            key,
            CURRENT_INITIAL_AUTHORIZATION_EVENT_HMAC_DOMAIN,
            surface_identity,
            authorization_document["kind"],
            authorization_document["revision"],
            authorization_document["bindingSha256"],
            authorization_document["environmentAttributionContractSha256"],
            authorization_document["environmentManifestBoundary"],
            authorization_identity,
            canonical_timestamp,
            normalized_message,
        )
        window_commitment = _initial_authorization_bytes_hmac(
            key,
            CURRENT_INITIAL_AUTHORIZATION_WINDOW_HMAC_DOMAIN,
            snapshot[:cursor],
        )
        if (
            EXPECTED_CURRENT_INITIAL_MATERIALIZATION_EVENT_COMMITMENT is None
            or EXPECTED_CURRENT_INITIAL_AUTHORIZATION_EVENT_COMMITMENT is None
            or EXPECTED_CURRENT_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT is None
            or not hmac.compare_digest(
                materialization_commitment,
                EXPECTED_CURRENT_INITIAL_MATERIALIZATION_EVENT_COMMITMENT,
            )
            or not hmac.compare_digest(
                authorization_commitment,
                EXPECTED_CURRENT_INITIAL_AUTHORIZATION_EVENT_COMMITMENT,
            )
            or not hmac.compare_digest(
                window_commitment,
                EXPECTED_CURRENT_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT,
            )
        ):
            _error(errors, "current v1.1 binding authorization source event is invalid")
            return False
        return True

    _error(
        errors,
        "current v1.1 frozen normative profile binding authorization source was not independently verified",
    )
    return False


def _current_initial_authorization_event_window_valid(
    private_evidence: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
    errors: list[str],
    *,
    credential_target_name: str | None = None,
) -> bool:
    expected_public = {
        "schema": 1,
        "kind": "agent-autonomy-harness-v1.1-provisional-cohort-private-evidence",
        "surfaceIdentity": EXPECTED_CURRENT_INITIAL_SURFACE_IDENTITY,
        "activationCursorCommitment": (
            EXPECTED_CURRENT_INITIAL_ACTIVATION_CURSOR_COMMITMENT
        ),
        "keyIdentity": EXPECTED_CURRENT_INITIAL_KEY_IDENTITY,
        "keyFingerprint": EXPECTED_CURRENT_INITIAL_AUTHORIZATION_KEY_FINGERPRINT,
        "sourceKind": "codex-rollout-user-event-v1",
        "environmentAttributionContractSha256": (
            EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
        ),
        "environmentManifestBoundary": (
            EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY
        ),
        "disposition": EXPECTED_CURRENT_INITIAL_PRIVATE_EVIDENCE_DISPOSITION,
    }
    required_anchors = (
        EXPECTED_CURRENT_INITIAL_SURFACE_IDENTITY,
        EXPECTED_CURRENT_INITIAL_ACTIVATION_CURSOR_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_KEY_IDENTITY,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_KEY_FINGERPRINT,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_MATERIALIZATION_EVENT_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_EVENT_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT,
    )
    if any(not isinstance(item, str) for item in required_anchors):
        _error(errors, "current v1.1 binding authorization anchors are unavailable")
        return False
    if (
        type(private_evidence.get("schema")) is not int
        or any(private_evidence.get(key) != item for key, item in expected_public.items())
        or authorization_document.get("environmentAttributionContractSha256")
        != EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
        or authorization_document.get("environmentManifestBoundary")
        != EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY
    ):
        _error(
            errors,
            "current v1.1 binding authorization private source does not match the frozen activation",
        )
        return False
    source_identity = private_evidence.get("sourceEventIdentity")
    source_timestamp = private_evidence.get("sourceEventTimestamp")
    authorization_identity = private_evidence.get("authorizationEventIdentity")
    authorization_timestamp = private_evidence.get("authorizationEventTimestamp")
    source_locator = private_evidence.get("sourceRollout")
    encoded_key = private_evidence.get("keyBase64")
    if (
        not isinstance(source_identity, str)
        or not isinstance(source_timestamp, str)
        or not isinstance(authorization_identity, str)
        or not isinstance(authorization_timestamp, str)
        or not isinstance(source_locator, str)
        or not isinstance(encoded_key, str)
    ):
        _error(errors, "current v1.1 binding authorization private source is invalid")
        return False
    try:
        key = bytearray(base64.b64decode(encoded_key, validate=True))
    except (ValueError, TypeError):
        _error(errors, "current v1.1 binding authorization private source is invalid")
        return False
    try:
        if len(key) != 32:
            _error(errors, "current v1.1 binding authorization private source is invalid")
            return False
        fingerprint = "sha256:" + hashlib.sha256(key).hexdigest()
        activation_message = (
            EXPECTED_CURRENT_HMAC_DOMAIN
            + "\0"
            + expected_public["surfaceIdentity"]
            + "\0"
            + source_identity
        ).encode("utf-8")
        commitment = "hmac-sha256:" + hmac.new(
            key,
            activation_message,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            fingerprint,
            expected_public["keyFingerprint"],
        ) or not hmac.compare_digest(
            commitment,
            expected_public["activationCursorCommitment"],
        ):
            _error(
                errors,
                "current v1.1 binding authorization private source does not match the frozen activation",
            )
            return False
        if (
            credential_target_name is None
            or not _current_initial_authorization_credential_target_valid(
                credential_target_name,
                key,
                errors,
            )
        ):
            return False
        locator_parts = _current_initial_authorization_source_locator_parts(
            source_locator,
            key,
            errors,
        )
        if locator_parts is None:
            return False
        source_path_text, authorized_root = locator_parts
        snapshot = _read_stable_initial_authorization_snapshot(
            Path(source_path_text),
            authorized_root,
            errors,
            generation_label="current v1.1 binding",
        )
        if snapshot is None:
            return False
        return _current_initial_authorization_snapshot_valid(
            private_evidence,
            authorization_document,
            snapshot,
            key,
            errors,
        )
    finally:
        key[:] = b"\0" * len(key)


def _source_event_instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or RFC3339.fullmatch(value) is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def _successor_authorization_snapshot_valid(
    private_evidence: Mapping[str, Any],
    snapshot: bytes,
    key: bytes | bytearray,
    errors: list[str],
) -> bool:
    restart_identity = private_evidence.get("sourceEventIdentity")
    restart_timestamp = private_evidence.get("sourceEventTimestamp")
    authorization_identity = private_evidence.get("authorizationEventIdentity")
    authorization_timestamp = private_evidence.get("authorizationEventTimestamp")
    predecessor_identity = private_evidence.get("predecessorRevocationRecordIdentity")
    predecessor_timestamp = private_evidence.get("predecessorRevocationRecordTimestamp")
    surface_identity = private_evidence.get("surfaceIdentity")
    restart_instant = _source_event_instant(restart_timestamp)
    authorization_instant = _source_event_instant(authorization_timestamp)
    predecessor_instant = _source_event_instant(predecessor_timestamp)
    uuid_pattern = (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{12}"
    )
    if (
        not isinstance(restart_identity, str)
        or re.fullmatch(uuid_pattern, restart_identity) is None
        or not isinstance(authorization_identity, str)
        or re.fullmatch(uuid_pattern, authorization_identity) is None
        or restart_identity == authorization_identity
        or not isinstance(predecessor_identity, str)
        or re.fullmatch(r"call_[A-Za-z0-9]{16,128}", predecessor_identity) is None
        or not isinstance(surface_identity, str)
        or predecessor_instant is None
        or restart_instant is None
        or authorization_instant is None
        or not predecessor_instant <= restart_instant <= authorization_instant
        or not isinstance(snapshot, bytes)
        or not snapshot
        or len(snapshot) > MAX_INITIAL_AUTHORIZATION_SOURCE_BYTES
    ):
        _error(errors, "successor binding authorization source event is invalid")
        return False

    predecessor_start: int | None = None
    predecessor_end: int | None = None
    restart_found = False
    record_count = 0
    cursor = 0
    stream = BytesIO(snapshot)
    while cursor < len(snapshot):
        line = stream.readline(MAX_INITIAL_AUTHORIZATION_SOURCE_LINE_BYTES + 1)
        if not line:
            break
        line_start = cursor
        cursor += len(line)
        record_count += 1
        if (
            record_count > MAX_INITIAL_AUTHORIZATION_SOURCE_RECORDS
            or len(line) > MAX_INITIAL_AUTHORIZATION_SOURCE_LINE_BYTES
        ):
            _error(
                errors,
                "successor binding authorization source event exceeds its finite bounds",
            )
            return False
        try:
            event = json.loads(
                line,
                object_pairs_hook=_initial_authorization_json_object,
                parse_constant=lambda constant: (_ for _ in ()).throw(
                    ValueError(f"non-finite source event value: {constant}")
                ),
            )
        except (
            UnicodeError,
            ValueError,
            TypeError,
            RecursionError,
            json.JSONDecodeError,
        ):
            _error(errors, "successor binding authorization source event is invalid")
            return False
        if not isinstance(event, dict):
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if (
            event.get("type") == "response_item"
            and payload.get("type") == "custom_tool_call_output"
            and payload.get("call_id") == predecessor_identity
            and event.get("timestamp") == predecessor_timestamp
        ):
            if (
                predecessor_start is not None
                or not hmac.compare_digest(
                    _initial_authorization_bytes_hmac(
                        key,
                        SUCCESSOR_PREDECESSOR_RECORD_HMAC_DOMAIN,
                        line,
                    ),
                    EXPECTED_SUCCESSOR_PREDECESSOR_RECORD_COMMITMENT,
                )
            ):
                _error(
                    errors,
                    "successor predecessor revocation source record is invalid",
                )
                return False
            predecessor_start = line_start
            predecessor_end = cursor
            continue
        if (
            event.get("type") != "event_msg"
            or payload.get("type") != "user_message"
            or predecessor_start is None
        ):
            continue
        event_identity = payload.get("client_id")
        event_message = payload.get("message")
        event_timestamp = event.get("timestamp")
        if not isinstance(event_identity, str) or not isinstance(event_message, str):
            _error(errors, "successor binding authorization source event is invalid")
            return False
        normalized_message = event_message.rstrip("\r\n")
        if not restart_found:
            if (
                event_identity != restart_identity
                or _source_event_instant(event_timestamp) != restart_instant
                or normalized_message != "同意重启 cohort。"
            ):
                _error(
                    errors,
                    "natural demand appeared before the successor restart grant",
                )
                return False
            restart_commitment = _initial_authorization_string_hmac(
                key,
                SUCCESSOR_RESTART_EVENT_HMAC_DOMAIN,
                surface_identity,
                predecessor_identity,
                restart_identity,
                restart_instant.isoformat().replace("+00:00", "Z"),
                normalized_message,
            )
            if not hmac.compare_digest(
                restart_commitment,
                EXPECTED_SUCCESSOR_RESTART_EVENT_COMMITMENT,
            ):
                _error(errors, "successor restart grant source event is invalid")
                return False
            restart_found = True
            continue
        message_sha256 = hashlib.sha256(
            normalized_message.encode("utf-8")
        ).hexdigest()
        if (
            event_identity != authorization_identity
            or _source_event_instant(event_timestamp) != authorization_instant
            or not hmac.compare_digest(
                message_sha256,
                EXPECTED_SUCCESSOR_BINDING_AUTHORIZATION_MESSAGE_SHA256,
            )
        ):
            _error(
                errors,
                "natural demand appeared before exact successor-freeze authorization",
            )
            return False
        authorization_commitment = _initial_authorization_string_hmac(
            key,
            SUCCESSOR_AUTHORIZATION_EVENT_HMAC_DOMAIN,
            surface_identity,
            predecessor_identity,
            restart_identity,
            authorization_identity,
            authorization_instant.isoformat().replace("+00:00", "Z"),
            normalized_message,
        )
        if predecessor_end is None:
            _error(errors, "successor predecessor revocation source record is invalid")
            return False
        authorization_window_commitment = _initial_authorization_bytes_hmac(
            key,
            SUCCESSOR_AUTHORIZATION_WINDOW_HMAC_DOMAIN,
            snapshot[predecessor_start:cursor],
        )
        if (
            not hmac.compare_digest(
                authorization_commitment,
                EXPECTED_SUCCESSOR_AUTHORIZATION_EVENT_COMMITMENT,
            )
            or not hmac.compare_digest(
                authorization_window_commitment,
                EXPECTED_SUCCESSOR_AUTHORIZATION_WINDOW_COMMITMENT,
            )
        ):
            _error(errors, "successor binding authorization source event is invalid")
            return False
        return True
    _error(
        errors,
        "successor frozen normative profile binding authorization source was not independently verified",
    )
    return False


def _successor_authorization_event_window_valid(
    private_evidence: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
    errors: list[str],
    *,
    credential_target_name: str | None = None,
) -> bool:
    expected_document = {
        "kind": "successor-normative-profile-binding-authorization",
        "revision": EXPECTED_V1_SUCCESSOR_BINDING_REVISION,
        "bindingSha256": EXPECTED_V1_SUCCESSOR_BINDING_SHA256,
        "predecessorRevocationRevision": (
            EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION
        ),
        "predecessorRevocationBindingSha256": (
            EXPECTED_V1_PREDECESSOR_REVOCATION_BINDING_SHA256
        ),
        "sourceWindowRule": EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_WINDOW_RULE,
    }
    if authorization_document != expected_document:
        _error(
            errors,
            "successor binding authorization document does not match the frozen binding",
        )
        return False
    expected_public = {
        "schema": 1,
        "kind": "agent-autonomy-harness-v1-successor-cohort-private-evidence",
        "surfaceIdentity": EXPECTED_SUCCESSOR_SURFACE_IDENTITY,
        "activationCursorCommitment": (
            EXPECTED_SUCCESSOR_ACTIVATION_CURSOR_COMMITMENT
        ),
        "keyIdentity": EXPECTED_SUCCESSOR_KEY_IDENTITY,
        "keyFingerprint": EXPECTED_SUCCESSOR_AUTHORIZATION_KEY_FINGERPRINT,
        "sourceKind": "codex-rollout-user-event-v1",
        "predecessorRevocationRevision": (
            EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION
        ),
        "disposition": (
            "authorized-retain-through-v1-accepted-or-stopped-no-later-than-"
            "2026-12-31T23:59:59+08:00-delete-and-revoke-on-withdrawal-expiry-"
            "stop-or-validation-failure"
        ),
    }
    if type(private_evidence.get("schema")) is not int or any(
        private_evidence.get(key) != item for key, item in expected_public.items()
    ):
        _error(
            errors,
            "successor binding authorization private source does not match the frozen activation",
        )
        return False
    source_locator = private_evidence.get("sourceRollout")
    encoded_key = private_evidence.get("keyBase64")
    restart_identity = private_evidence.get("sourceEventIdentity")
    if (
        not isinstance(source_locator, str)
        or not isinstance(encoded_key, str)
        or not isinstance(restart_identity, str)
    ):
        _error(errors, "successor binding authorization private source is invalid")
        return False
    try:
        key = bytearray(base64.b64decode(encoded_key, validate=True))
    except (ValueError, TypeError):
        _error(errors, "successor binding authorization private source is invalid")
        return False
    try:
        if len(key) != 32:
            _error(errors, "successor binding authorization private source is invalid")
            return False
        fingerprint = "sha256:" + hashlib.sha256(key).hexdigest()
        activation_message = (
            EXPECTED_HMAC_DOMAIN
            + "\0"
            + EXPECTED_SUCCESSOR_SURFACE_IDENTITY
            + "\0"
            + restart_identity
        ).encode("utf-8")
        activation_commitment = "hmac-sha256:" + hmac.new(
            key, activation_message, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(
            fingerprint,
            EXPECTED_SUCCESSOR_AUTHORIZATION_KEY_FINGERPRINT,
        ) or not hmac.compare_digest(
            activation_commitment,
            EXPECTED_SUCCESSOR_ACTIVATION_CURSOR_COMMITMENT,
        ):
            _error(
                errors,
                "successor binding authorization private source does not match the frozen activation",
            )
            return False
        if credential_target_name is None or not _successor_authorization_credential_target_valid(
            credential_target_name,
            key,
            errors,
        ):
            return False
        locator_parts = _successor_authorization_source_locator_parts(
            source_locator,
            key,
            errors,
        )
        if locator_parts is None:
            return False
        source_path_text, authorized_root = locator_parts
        snapshot = _read_stable_initial_authorization_snapshot(
            Path(source_path_text),
            authorized_root,
            errors,
            generation_label="successor binding",
        )
        if snapshot is None:
            return False
        return _successor_authorization_snapshot_valid(
            private_evidence,
            snapshot,
            key,
            errors,
        )
    finally:
        key[:] = b"\0" * len(key)


def _delete_cohort_authorization_private_resource(
    resource: tuple[dict[str, Any], str],
    trigger: str,
    expected_key_fingerprint: str,
    target_validator: Callable[[str, bytes | bytearray, list[str]], bool],
    generation_label: str,
    errors: list[str],
) -> bool:
    del resource, trigger, expected_key_fingerprint, target_validator
    _error(
        errors,
        f"{generation_label} authorization private cleanup is historical and unavailable in v1.1",
    )
    return False


def _delete_initial_authorization_private_resource(
    resource: tuple[dict[str, Any], str],
    trigger: str,
    errors: list[str],
) -> bool:
    return _delete_cohort_authorization_private_resource(
        resource,
        trigger,
        EXPECTED_INITIAL_AUTHORIZATION_KEY_FINGERPRINT,
        _initial_authorization_credential_target_valid,
        "initial binding",
        errors,
    )


def _delete_successor_authorization_private_resource(
    resource: tuple[dict[str, Any], str],
    trigger: str,
    errors: list[str],
) -> bool:
    deleted = _delete_cohort_authorization_private_resource(
        resource,
        trigger,
        EXPECTED_SUCCESSOR_AUTHORIZATION_KEY_FINGERPRINT,
        _successor_authorization_credential_target_valid,
        "successor binding",
        errors,
    )
    if not deleted:
        return False
    return _remove_successor_expiry_cleanup_trigger(errors)


def _revoke_initial_authorization_private_evidence(
    trigger: str,
    errors: list[str],
) -> bool:
    if trigger not in {"withdrawal", "expiry", "stop", "validation-failure"}:
        _error(errors, "initial binding authorization private evidence trigger is invalid")
        return False
    resource = _read_initial_authorization_private_evidence(errors)
    if resource is None:
        return False
    return _delete_initial_authorization_private_resource(resource, trigger, errors)


def _revoke_successor_authorization_private_evidence(
    trigger: str,
    errors: list[str],
) -> bool:
    if trigger not in {"withdrawal", "expiry", "stop", "validation-failure"}:
        _error(errors, "successor binding authorization private evidence trigger is invalid")
        return False
    resource = _read_successor_authorization_private_evidence(errors)
    if resource is None:
        return False
    return _delete_successor_authorization_private_resource(resource, trigger, errors)


def _delete_current_initial_authorization_private_resource(
    resource: tuple[dict[str, Any], str],
    trigger: str,
    root: Path,
    errors: list[str],
) -> bool:
    if trigger not in {"withdrawal", "expiry", "stop", "validation-failure"}:
        _error(
            errors,
            "current v1.1 binding authorization private evidence trigger is invalid",
        )
        return False
    if not _current_initial_authorization_private_resource_identity_valid(
        resource,
        errors,
    ):
        return False
    _, target_name = resource
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        _error(errors, "current v1.1 binding authorization private cleanup is unavailable")
        return False
    try:
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        delete_credential = advapi32.CredDeleteW
        delete_credential.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
        delete_credential.restype = ctypes.c_int
        ctypes.set_last_error(0)
        deleted = delete_credential(target_name, 1, 0)
    except (OSError, ValueError, TypeError):
        deleted = 0
    if not deleted:
        _error(errors, "current v1.1 binding authorization private cleanup failed")
        return False
    absence_errors: list[str] = []
    if not _current_initial_authorization_private_resource_absent(absence_errors):
        errors.extend(absence_errors)
        return False
    if not _remove_current_initial_expiry_cleanup_trigger(root, errors):
        return False
    return True


def _revoke_current_initial_authorization_private_evidence(
    trigger: str,
    root: Path,
    errors: list[str],
) -> bool:
    if trigger not in {"withdrawal", "expiry", "stop", "validation-failure"}:
        _error(
            errors,
            "current v1.1 binding authorization private evidence trigger is invalid",
        )
        return False
    resource = _read_current_initial_authorization_private_evidence(errors)
    if resource is None:
        return False
    return _delete_current_initial_authorization_private_resource(
        resource,
        trigger,
        root,
        errors,
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_initial_binding_authorization(
    authorization_document: dict[str, Any], root: Path, errors: list[str]
) -> bool:
    del root
    if authorization_document != {
        "kind": "initial-normative-profile-binding-authorization",
        "revision": EXPECTED_V1_INITIAL_BINDING_REVISION,
        "bindingSha256": EXPECTED_V1_INITIAL_BINDING_SHA256,
    }:
        _error(
            errors,
            "initial binding authorization document does not match the frozen binding",
        )
        return False
    if _utc_now() > INITIAL_BINDING_AUTHORIZATION_EXPIRY_UTC:
        _revoke_initial_authorization_private_evidence("expiry", errors)
        _error(
            errors,
            "initial binding authorization private evidence retention has expired",
        )
        return False
    resource = _read_initial_authorization_private_evidence(errors)
    if resource is None:
        return False
    private_evidence, target_name = resource
    validation_errors: list[str] = []
    valid = _initial_authorization_event_window_valid(
        private_evidence,
        authorization_document,
        validation_errors,
        credential_target_name=target_name,
    )
    if not valid or validation_errors:
        nondestructive_source_failure = (
            not valid
            and bool(validation_errors)
            and all(
                item in NONDESTRUCTIVE_INITIAL_AUTHORIZATION_SOURCE_FAILURES
                for item in validation_errors
            )
        )
        errors.extend(validation_errors)
        if not nondestructive_source_failure:
            _delete_initial_authorization_private_resource(
                resource,
                "validation-failure",
                errors,
            )
        return False
    if _utc_now() > INITIAL_BINDING_AUTHORIZATION_EXPIRY_UTC:
        _delete_initial_authorization_private_resource(resource, "expiry", errors)
        _error(
            errors,
            "initial binding authorization private evidence retention has expired",
        )
        return False
    return True


def _expiry_task_definition_valid(
    task: ET.Element,
    expected_python: Path,
    expected_root: Path,
    expected_user_sid: str,
    expected_arguments: str,
    expected_start_boundary: str,
    diagnostic: str,
    errors: list[str],
) -> bool:
    def local_name(item: ET.Element) -> str:
        return item.tag.rsplit("}", 1)[-1]

    def elements(local_name: str) -> list[ET.Element]:
        return [
            item
            for item in task.iter()
            if item.tag.rsplit("}", 1)[-1] == local_name
        ]

    trigger_containers = elements("Triggers")
    action_containers = elements("Actions")
    principal_containers = elements("Principals")
    settings_containers = elements("Settings")
    trigger_children = (
        list(trigger_containers[0]) if len(trigger_containers) == 1 else []
    )
    action_children = (
        list(action_containers[0]) if len(action_containers) == 1 else []
    )
    principal_children = (
        list(principal_containers[0]) if len(principal_containers) == 1 else []
    )
    executions = elements("Exec")
    time_triggers = elements("TimeTrigger")
    time_trigger_fields = (
        [local_name(item) for item in time_triggers[0]]
        if len(time_triggers) == 1
        else []
    )
    execution_fields = (
        [local_name(item) for item in executions[0]]
        if len(executions) == 1
        else []
    )
    principal_fields = (
        [local_name(item) for item in principal_children[0]]
        if len(principal_children) == 1
        else []
    )
    settings_fields = (
        [local_name(item) for item in settings_containers[0]]
        if len(settings_containers) == 1
        else []
    )
    exact_authoring_shape = (
        len(time_trigger_fields) == 2
        and set(time_trigger_fields) == {"StartBoundary", "Enabled"}
        and len(principal_fields) == 3
        and set(principal_fields) == {"UserId", "LogonType", "RunLevel"}
        and len(settings_fields) == 7
        and set(settings_fields)
        == {
            "MultipleInstancesPolicy",
            "DisallowStartIfOnBatteries",
            "StopIfGoingOnBatteries",
            "RunOnlyIfNetworkAvailable",
            "StartWhenAvailable",
            "Enabled",
            "ExecutionTimeLimit",
        }
    )
    windows_canonical_export_shape = (
        len(time_trigger_fields) == 1
        and time_trigger_fields == ["StartBoundary"]
        and len(principal_fields) == 2
        and set(principal_fields) == {"UserId", "LogonType"}
        and len(settings_fields) == 6
        and set(settings_fields)
        == {
            "MultipleInstancesPolicy",
            "DisallowStartIfOnBatteries",
            "StopIfGoingOnBatteries",
            "StartWhenAvailable",
            "IdleSettings",
            "ExecutionTimeLimit",
        }
    )
    commands = elements("Command")
    arguments = elements("Arguments")
    working_directories = elements("WorkingDirectory")
    start_boundaries = elements("StartBoundary")
    repetitions = elements("Repetition")
    logon_types = elements("LogonType")
    start_when_available = elements("StartWhenAvailable")
    execution_time_limits = elements("ExecutionTimeLimit")
    multiple_instance_policies = elements("MultipleInstancesPolicy")
    user_ids = elements("UserId")
    run_levels = elements("RunLevel")
    settings_enabled = (
        [item for item in settings_containers[0] if local_name(item) == "Enabled"]
        if len(settings_containers) == 1
        else []
    )
    trigger_enabled = (
        [item for item in time_triggers[0] if local_name(item) == "Enabled"]
        if len(time_triggers) == 1
        else []
    )
    disallow_on_battery = elements("DisallowStartIfOnBatteries")
    stop_on_battery = elements("StopIfGoingOnBatteries")
    require_network = elements("RunOnlyIfNetworkAvailable")
    idle_settings = elements("IdleSettings")
    idle_fields = (
        [local_name(item) for item in idle_settings[0]]
        if len(idle_settings) == 1
        else []
    )
    stop_on_idle_end = elements("StopOnIdleEnd")
    restart_on_idle = elements("RestartOnIdle")
    delayed_or_bounded = [
        *elements("Delay"),
        *elements("RandomDelay"),
        *elements("EndBoundary"),
    ]
    if (
        len(trigger_containers) != 1
        or len(action_containers) != 1
        or len(principal_containers) != 1
        or len(settings_containers) != 1
        or len(trigger_children) != 1
        or local_name(trigger_children[0]) != "TimeTrigger"
        or len(action_children) != 1
        or local_name(action_children[0]) != "Exec"
        or len(principal_children) != 1
        or local_name(principal_children[0]) != "Principal"
        or not (exact_authoring_shape or windows_canonical_export_shape)
        or len(execution_fields) != 3
        or set(execution_fields) != {"Command", "Arguments", "WorkingDirectory"}
        or len(executions) != 1
        or len(time_triggers) != 1
        or len(commands) != 1
        or len(arguments) != 1
        or len(working_directories) != 1
        or len(start_boundaries) != 1
        or len(logon_types) != 1
        or len(start_when_available) != 1
        or len(execution_time_limits) != 1
        or len(multiple_instance_policies) != 1
        or len(user_ids) != 1
        or user_ids[0].text != expected_user_sid
        or (
            exact_authoring_shape
            and (
                len(run_levels) != 1
                or run_levels[0].text != "LeastPrivilege"
                or len(settings_enabled) != 1
                or settings_enabled[0].text != "true"
                or len(trigger_enabled) != 1
                or trigger_enabled[0].text != "true"
                or len(require_network) != 1
                or require_network[0].text != "false"
                or idle_settings
            )
        )
        or (
            windows_canonical_export_shape
            and (
                run_levels
                or settings_enabled
                or trigger_enabled
                or require_network
                or len(idle_settings) != 1
                or len(idle_fields) != 2
                or set(idle_fields) != {"StopOnIdleEnd", "RestartOnIdle"}
                or len(stop_on_idle_end) != 1
                or stop_on_idle_end[0].text != "true"
                or len(restart_on_idle) != 1
                or restart_on_idle[0].text != "false"
            )
        )
        or len(disallow_on_battery) != 1
        or disallow_on_battery[0].text != "false"
        or len(stop_on_battery) != 1
        or stop_on_battery[0].text != "false"
        or delayed_or_bounded
        or repetitions
        or not isinstance(commands[0].text, str)
        or _normalized_native_path(commands[0].text)
        != _normalized_native_path(expected_python)
        or arguments[0].text != expected_arguments
        or not isinstance(working_directories[0].text, str)
        or _normalized_native_path(working_directories[0].text)
        != _normalized_native_path(expected_root)
        or start_boundaries[0].text != expected_start_boundary
        or logon_types[0].text != "S4U"
        or start_when_available[0].text != "true"
        or execution_time_limits[0].text != "PT5M"
        or multiple_instance_policies[0].text != "IgnoreNew"
    ):
        _error(
            errors,
            f"{diagnostic} authorization expiry cleanup trigger is invalid",
        )
        return False
    return True


def _successor_expiry_task_definition_valid(
    task: ET.Element,
    expected_python: Path,
    expected_root: Path,
    expected_user_sid: str,
    errors: list[str],
) -> bool:
    return _expiry_task_definition_valid(
        task,
        expected_python,
        expected_root,
        expected_user_sid,
        SUCCESSOR_EXPIRY_TASK_ARGUMENTS,
        SUCCESSOR_EXPIRY_TASK_START_BOUNDARY,
        "successor binding",
        errors,
    )


def _current_initial_expiry_task_definition_valid(
    task: ET.Element,
    expected_python: Path,
    expected_root: Path,
    expected_user_sid: str,
    errors: list[str],
) -> bool:
    return _expiry_task_definition_valid(
        task,
        expected_python,
        expected_root,
        expected_user_sid,
        CURRENT_INITIAL_EXPIRY_TASK_ARGUMENTS,
        CURRENT_INITIAL_EXPIRY_TASK_START_BOUNDARY,
        "current v1.1 binding",
        errors,
    )


def _current_windows_user_sid() -> str | None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return None
    token = ctypes.c_void_p()
    sid_text = ctypes.c_wchar_p()
    try:
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.restype = ctypes.c_void_p
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        local_free = kernel32.LocalFree
        local_free.argtypes = [ctypes.c_void_p]
        local_free.restype = ctypes.c_void_p
        open_process_token = advapi32.OpenProcessToken
        open_process_token.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        open_process_token.restype = ctypes.c_int
        get_token_information = advapi32.GetTokenInformation
        get_token_information.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        get_token_information.restype = ctypes.c_int
        convert_sid = advapi32.ConvertSidToStringSidW
        convert_sid.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
        convert_sid.restype = ctypes.c_int
        if not open_process_token(get_current_process(), 0x0008, ctypes.byref(token)):
            return None
        size = ctypes.c_uint32()
        get_token_information(token, 1, None, 0, ctypes.byref(size))
        if size.value == 0 or size.value > 65_536:
            return None
        buffer = ctypes.create_string_buffer(size.value)
        if not get_token_information(
            token,
            1,
            buffer,
            size.value,
            ctypes.byref(size),
        ):
            return None
        token_user = ctypes.cast(
            buffer,
            ctypes.POINTER(_WindowsTokenUser),
        ).contents
        if not token_user.user.sid or not convert_sid(
            token_user.user.sid,
            ctypes.byref(sid_text),
        ):
            return None
        value = sid_text.value
        return value if isinstance(value, str) and value.startswith("S-1-") else None
    except (OSError, ValueError, TypeError):
        return None
    finally:
        if sid_text:
            try:
                kernel32.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
            except (NameError, OSError, ValueError):
                pass
        if token.value:
            try:
                kernel32.CloseHandle(token)
            except (NameError, OSError, ValueError):
                pass


def _trusted_windows_schtasks_executable() -> Path | None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return None
    try:
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_system_directory = kernel32.GetSystemDirectoryW
        get_system_directory.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        get_system_directory.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32_768)
        length = get_system_directory(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            raise OSError("system directory unavailable")
        system_directory = Path(buffer.value).resolve(strict=True)
        executable = (system_directory / "schtasks.exe").resolve(strict=True)
        executable_metadata = executable.lstat()
        if (
            executable.parent != system_directory
            or not stat.S_ISREG(executable_metadata.st_mode)
            or _link_or_reparse(executable)
        ):
            raise OSError("untrusted expiry trigger executable")
    except (OSError, RuntimeError, ValueError):
        return None
    return executable


def _expiry_cleanup_trigger_valid(
    root: Path,
    task_name: str,
    task_definition_validator: Callable[[ET.Element, Path, Path, str, list[str]], bool],
    diagnostic: str,
    errors: list[str],
) -> bool:
    executable = _trusted_windows_schtasks_executable()
    current_user_sid = _current_windows_user_sid()
    try:
        expected_python = Path(sys.executable).resolve(strict=True)
        expected_root = root.resolve(strict=True)
        if (
            executable is None
            or current_user_sid is None
            or not stat.S_ISREG(expected_python.lstat().st_mode)
            or _link_or_reparse(expected_python)
        ):
            raise OSError("untrusted expiry trigger runtime")
    except (OSError, RuntimeError, ValueError):
        _error(
            errors,
            f"{diagnostic} authorization expiry cleanup trigger is unavailable",
        )
        return False
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() in {"systemroot", "windir", "path", "pathext", "temp", "tmp"}
    }
    process: subprocess.Popen[bytes] | None = None

    def stop_process() -> None:
        if process is None:
            return
        try:
            if process.poll() is None:
                process.kill()
        except OSError:
            pass

    try:
        process = subprocess.Popen(
            [
                str(executable),
                "/Query",
                "/TN",
                task_name,
                "/XML",
            ],
            cwd=expected_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        timer = Timer(10, stop_process)
        timer.daemon = True
        timer.start()
        try:
            if process.stdout is None:
                stop_process()
                output = b""
            else:
                try:
                    output = process.stdout.read(
                        MAX_SUCCESSOR_EXPIRY_TASK_XML_BYTES + 1
                    )
                finally:
                    process.stdout.close()
            return_code = process.wait()
        finally:
            timer.cancel()
    except (OSError, ValueError, subprocess.SubprocessError):
        _error(
            errors,
            f"{diagnostic} authorization expiry cleanup trigger is unavailable",
        )
        return False
    if return_code != 0 or not output or len(output) > MAX_SUCCESSOR_EXPIRY_TASK_XML_BYTES:
        _error(
            errors,
            f"{diagnostic} authorization expiry cleanup trigger is unavailable",
        )
        return False
    try:
        task = ET.fromstring(output.decode("utf-16"))
    except (ET.ParseError, UnicodeError, ValueError):
        try:
            task = ET.fromstring(output.decode("utf-8-sig"))
        except (ET.ParseError, UnicodeError, ValueError):
            _error(
                errors,
                f"{diagnostic} authorization expiry cleanup trigger is invalid",
            )
            return False
    return task_definition_validator(
        task,
        expected_python,
        expected_root,
        current_user_sid,
        errors,
    )


def _successor_expiry_cleanup_trigger_valid(root: Path, errors: list[str]) -> bool:
    return _expiry_cleanup_trigger_valid(
        root,
        SUCCESSOR_EXPIRY_TASK_NAME,
        _successor_expiry_task_definition_valid,
        "successor binding",
        errors,
    )


def _current_initial_expiry_cleanup_trigger_valid(
    root: Path, errors: list[str]
) -> bool:
    return _expiry_cleanup_trigger_valid(
        root,
        CURRENT_INITIAL_EXPIRY_TASK_NAME,
        _current_initial_expiry_task_definition_valid,
        "current v1.1 binding",
        errors,
    )


def _remove_current_initial_expiry_cleanup_trigger(
    root: Path, errors: list[str]
) -> bool:
    validation_errors: list[str] = []
    if not _current_initial_expiry_cleanup_trigger_valid(root, validation_errors):
        errors.extend(validation_errors)
        return False
    executable = _trusted_windows_schtasks_executable()
    try:
        expected_root = root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        expected_root = None
    if executable is None or expected_root is None:
        _error(
            errors,
            "current v1.1 binding authorization expiry cleanup trigger removal is unavailable",
        )
        return False
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() in {"systemroot", "windir", "path", "pathext", "temp", "tmp"}
    }
    try:
        removed = subprocess.run(
            [
                str(executable),
                "/Delete",
                "/TN",
                CURRENT_INITIAL_EXPIRY_TASK_NAME,
                "/F",
            ],
            cwd=expected_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        _error(
            errors,
            "current v1.1 binding authorization expiry cleanup trigger removal is unavailable",
        )
        return False
    if removed.returncode != 0:
        _error(
            errors,
            "current v1.1 binding authorization expiry cleanup trigger removal failed",
        )
        return False
    post_errors: list[str] = []
    if _current_initial_expiry_cleanup_trigger_valid(root, post_errors):
        _error(
            errors,
            "current v1.1 binding authorization expiry cleanup trigger still exists",
        )
        return False
    if post_errors != [
        "current v1.1 binding authorization expiry cleanup trigger is unavailable"
    ]:
        errors.extend(post_errors)
        return False
    return True


def _current_initial_expiry_cleanup_trigger_absent(errors: list[str]) -> bool:
    executable = _trusted_windows_schtasks_executable()
    if executable is None:
        _error(
            errors,
            "revoked current v1.1 expiry cleanup trigger absence is unverifiable",
        )
        return False
    try:
        task_root = (executable.parent / "Tasks").resolve(strict=True)
        task_root_metadata = task_root.lstat()
        if not stat.S_ISDIR(task_root_metadata.st_mode) or _link_or_reparse(task_root):
            raise OSError("untrusted task root")
        task_path = task_root / CURRENT_INITIAL_EXPIRY_TASK_NAME
        task_path.lstat()
    except FileNotFoundError:
        task_path_absent = True
    except (OSError, RuntimeError, ValueError):
        _error(
            errors,
            "revoked current v1.1 expiry cleanup trigger absence is unverifiable",
        )
        return False
    else:
        task_path_absent = False
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() in {"systemroot", "windir", "path", "pathext", "temp", "tmp"}
    }
    try:
        queried = subprocess.run(
            [
                str(executable),
                "/Query",
                "/TN",
                CURRENT_INITIAL_EXPIRY_TASK_NAME,
                "/XML",
            ],
            cwd=task_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        _error(
            errors,
            "revoked current v1.1 expiry cleanup trigger absence is unverifiable",
        )
        return False
    if not task_path_absent or queried.returncode == 0:
        _error(errors, "revoked current v1.1 expiry cleanup trigger still exists")
        return False
    return True


def _remove_successor_expiry_cleanup_trigger(errors: list[str]) -> bool:
    _error(
        errors,
        "successor binding authorization expiry cleanup trigger removal is historical and unavailable in v1.1",
    )
    return False


def _validate_successor_binding_authorization(
    authorization_document: dict[str, Any], root: Path, errors: list[str]
) -> bool:
    expected_document = {
        "kind": "successor-normative-profile-binding-authorization",
        "revision": EXPECTED_V1_SUCCESSOR_BINDING_REVISION,
        "bindingSha256": EXPECTED_V1_SUCCESSOR_BINDING_SHA256,
        "predecessorRevocationRevision": (
            EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION
        ),
        "predecessorRevocationBindingSha256": (
            EXPECTED_V1_PREDECESSOR_REVOCATION_BINDING_SHA256
        ),
        "sourceWindowRule": EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_WINDOW_RULE,
    }
    if authorization_document != expected_document:
        _error(
            errors,
            "successor binding authorization document does not match the frozen binding",
        )
        return False
    if _utc_now() > SUCCESSOR_BINDING_AUTHORIZATION_EXPIRY_UTC:
        _revoke_successor_authorization_private_evidence("expiry", errors)
        _error(
            errors,
            "successor binding authorization private evidence retention has expired",
        )
        return False
    resource = _read_successor_authorization_private_evidence(errors)
    if resource is None:
        return False
    private_evidence, target_name = resource
    validation_errors: list[str] = []
    valid = _successor_authorization_event_window_valid(
        private_evidence,
        authorization_document,
        validation_errors,
        credential_target_name=target_name,
    )
    if valid and not validation_errors:
        valid = _successor_expiry_cleanup_trigger_valid(root, validation_errors)
    if not valid or validation_errors:
        nondestructive_source_failure = (
            not valid
            and bool(validation_errors)
            and all(
                item in NONDESTRUCTIVE_SUCCESSOR_AUTHORIZATION_SOURCE_FAILURES
                for item in validation_errors
            )
        )
        errors.extend(validation_errors)
        if not nondestructive_source_failure:
            _delete_successor_authorization_private_resource(
                resource,
                "validation-failure",
                errors,
            )
        return False
    if _utc_now() > SUCCESSOR_BINDING_AUTHORIZATION_EXPIRY_UTC:
        _delete_successor_authorization_private_resource(resource, "expiry", errors)
        _error(
            errors,
            "successor binding authorization private evidence retention has expired",
        )
        return False
    return True


def _current_initial_authorization_anchors_valid(
    activation: Mapping[str, Any] | None,
    errors: list[str],
) -> bool:
    expected_surface = EXPECTED_CURRENT_INITIAL_SURFACE_IDENTITY
    expected_cursor = EXPECTED_CURRENT_INITIAL_ACTIVATION_CURSOR_COMMITMENT
    expected_key_identity = EXPECTED_CURRENT_INITIAL_KEY_IDENTITY
    expected_fingerprint = EXPECTED_CURRENT_INITIAL_AUTHORIZATION_KEY_FINGERPRINT
    hmac_commitments = (
        expected_cursor,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_CREDENTIAL_TARGET_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_SOURCE_ROOT_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_MATERIALIZATION_EVENT_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_EVENT_COMMITMENT,
        EXPECTED_CURRENT_INITIAL_AUTHORIZATION_WINDOW_COMMITMENT,
    )
    valid = (
        isinstance(EXPECTED_CURRENT_INITIAL_BINDING_REVISION, str)
        and re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}",
            EXPECTED_CURRENT_INITIAL_BINDING_REVISION,
        )
        is not None
        and isinstance(EXPECTED_CURRENT_INITIAL_BINDING_SHA256, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            EXPECTED_CURRENT_INITIAL_BINDING_SHA256,
        )
        is not None
        and EXPECTED_CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID
        == CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID
        and isinstance(expected_surface, str)
        and PUBLIC_SURFACE_IDENTITY_PATTERN.fullmatch(expected_surface) is not None
        and isinstance(expected_key_identity, str)
        and PUBLIC_COHORT_KEY_IDENTITY_PATTERN.fullmatch(expected_key_identity)
        is not None
        and isinstance(expected_fingerprint, str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", expected_fingerprint) is not None
        and all(
            isinstance(item, str)
            and re.fullmatch(r"hmac-sha256:[0-9a-f]{64}", item) is not None
            for item in hmac_commitments
        )
    )
    if activation is not None:
        valid = valid and all(
            activation.get(field) == expected
            for field, expected in {
                "surfaceIdentity": expected_surface,
                "activationCursorCommitment": expected_cursor,
                "keyIdentity": expected_key_identity,
                "keyFingerprint": expected_fingerprint,
            }.items()
        )
    if not valid:
        _error(errors, "current v1.1 binding authorization anchors are unavailable")
        return False
    return True


def _validate_current_initial_binding_authorization(
    authorization_document: dict[str, Any], root: Path, errors: list[str]
) -> bool:
    expected_document = {
        "kind": "v1.1-normative-profile-binding-authorization",
        "revision": EXPECTED_CURRENT_INITIAL_BINDING_REVISION,
        "bindingSha256": EXPECTED_CURRENT_INITIAL_BINDING_SHA256,
        "environmentAttributionContractSha256": (
            EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
        ),
        "environmentManifestBoundary": (
            EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY
        ),
    }
    if authorization_document != expected_document:
        _error(
            errors,
            "current v1.1 binding authorization document does not match the frozen binding",
        )
        return False
    if not _current_initial_authorization_anchors_valid(None, errors):
        return False
    if _utc_now() > CURRENT_INITIAL_BINDING_AUTHORIZATION_EXPIRY_UTC:
        _revoke_current_initial_authorization_private_evidence(
            "expiry",
            root,
            errors,
        )
        _error(
            errors,
            "current v1.1 binding authorization private evidence retention has expired",
        )
        return False
    resource = _read_current_initial_authorization_private_evidence(errors)
    if resource is None:
        return False
    private_evidence, target_name = resource
    validation_errors: list[str] = []
    valid = _current_initial_authorization_event_window_valid(
        private_evidence,
        authorization_document,
        validation_errors,
        credential_target_name=target_name,
    )
    if valid and not validation_errors:
        valid = _current_initial_expiry_cleanup_trigger_valid(root, validation_errors)
    if not valid or validation_errors:
        nondestructive_source_failure = (
            not valid
            and bool(validation_errors)
            and all(
                item in NONDESTRUCTIVE_CURRENT_INITIAL_AUTHORIZATION_SOURCE_FAILURES
                for item in validation_errors
            )
        )
        errors.extend(validation_errors)
        if not nondestructive_source_failure:
            _delete_current_initial_authorization_private_resource(
                resource,
                "validation-failure",
                root,
                errors,
            )
        return False
    if _utc_now() > CURRENT_INITIAL_BINDING_AUTHORIZATION_EXPIRY_UTC:
        _delete_current_initial_authorization_private_resource(
            resource,
            "expiry",
            root,
            errors,
        )
        _error(
            errors,
            "current v1.1 binding authorization private evidence retention has expired",
        )
        return False
    return True


def expire_current_initial_authorization_private_evidence(
    root: Path, errors: list[str]
) -> bool:
    if _utc_now() < CURRENT_INITIAL_BINDING_AUTHORIZATION_EXPIRY_UTC:
        _error(errors, "current v1.1 binding authorization expiry cleanup is not due")
        return False
    read_errors: list[str] = []
    resource = _read_current_initial_authorization_private_evidence(read_errors)
    if resource is None:
        absence_errors: list[str] = []
        if _current_initial_authorization_private_resource_absent(absence_errors):
            return _remove_current_initial_expiry_cleanup_trigger(root, errors)
        errors.extend(read_errors)
        errors.extend(absence_errors)
        return False
    if not _current_initial_authorization_private_resource_identity_valid(
        resource,
        errors,
    ):
        return False
    return _delete_current_initial_authorization_private_resource(
        resource,
        "expiry",
        root,
        errors,
    )


SUPPORTED_EVIDENCE_VALIDATORS: Mapping[str, EvidenceValidatorSpec] = MappingProxyType({})
SUPPORTED_PRE_MEASUREMENT_VALIDATORS: Mapping[
    str, PreMeasurementValidatorSpec
] = MappingProxyType({})
SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS: Mapping[
    str, HumanAuthorizationValidator
] = MappingProxyType({})
SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS: Mapping[
    str, TerminalAuthorizationValidatorSpec
] = MappingProxyType({})

_EVIDENCE_GIT_CACHE: ContextVar[
    dict[tuple[str, tuple[str, ...], bytes | None, int], bytes | None] | None
] = ContextVar("harness_evidence_git_cache", default=None)

_VERIFICATION_READ_BUDGET: ContextVar[dict[str, Any] | None] = ContextVar(
    "harness_verification_read_budget", default=None
)


def _evidence_git(
    root: Path,
    *arguments: str,
    stdin_data: bytes | None = None,
    max_output_bytes: int = MAX_GIT_OUTPUT_BYTES,
) -> bytes | None:
    cache = _EVIDENCE_GIT_CACHE.get()
    key = (str(root.resolve(strict=False)), arguments, stdin_data, max_output_bytes)
    if cache is not None and key in cache:
        return cache[key]
    if (
        not isinstance(max_output_bytes, int)
        or isinstance(max_output_bytes, bool)
        or max_output_bytes < 0
        or max_output_bytes > MAX_VERIFICATION_TOTAL_BYTES
        or (stdin_data is not None and len(stdin_data) > MAX_GIT_OUTPUT_BYTES)
    ):
        return None
    executable = shutil.which("git")
    if executable is None:
        result = None
        if cache is not None:
            cache[key] = result
        return result
    try:
        executable_path = Path(executable).resolve(strict=True)
        executable_path.relative_to(root.resolve(strict=True))
    except ValueError:
        pass
    except (OSError, RuntimeError):
        result = None
        if cache is not None:
            cache[key] = result
        return result
    else:
        result = None
        if cache is not None:
            cache[key] = result
        return result
    try:
        metadata = executable_path.lstat()
    except OSError:
        result = None
        if cache is not None:
            cache[key] = result
        return result
    if (
        executable_path.name.casefold() not in {"git", "git.exe"}
        or not stat.S_ISREG(metadata.st_mode)
        or _link_or_reparse(executable_path)
    ):
        result = None
        if cache is not None:
            cache[key] = result
        return result
    if os.name == "nt":
        folded_parts = tuple(part.casefold() for part in executable_path.parts)
        system_directory = ctypes.create_unicode_buffer(32_768)
        system_length = ctypes.windll.kernel32.GetSystemDirectoryW(
            system_directory, len(system_directory)
        )
        system_drive = (
            Path(system_directory.value).drive.casefold()
            if 0 < system_length < len(system_directory)
            else ""
        )
        trusted_install = (
            bool(executable_path.drive)
            and not executable_path.drive.startswith("\\\\")
            and executable_path.drive.casefold() == system_drive
            and len(folded_parts) >= 4
            and folded_parts[1:3]
            in {
                ("program files", "git"),
                ("program files (x86)", "git"),
            }
        )
    else:
        trusted_roots = (
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            Path("/usr/local/Cellar"),
            Path("/opt/homebrew"),
            Path("/opt/local/bin"),
        )
        trusted_install = any(
            executable_path == trusted_root
            or trusted_root in executable_path.parents
            for trusted_root in trusted_roots
        )
    if not trusted_install:
        result = None
        if cache is not None:
            cache[key] = result
        return result

    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold()
        in {"systemroot", "windir", "path", "pathext", "temp", "tmp"}
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_EXTERNAL_DIFF": "",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
    )
    process: subprocess.Popen[bytes] | None = None
    isolated_remote_workspace: tempfile.TemporaryDirectory[str] | None = None
    process_cwd = root
    if arguments and arguments[0] == "ls-remote":
        try:
            isolated_remote_workspace = tempfile.TemporaryDirectory(
                prefix="harness-ls-remote-"
            )
            process_cwd = Path(isolated_remote_workspace.name).resolve()
            environment["GIT_CEILING_DIRECTORIES"] = str(process_cwd)
        except OSError:
            if cache is not None:
                cache[key] = None
            return None

    def stop_process() -> None:
        if process is None:
            return
        try:
            if process.poll() is None:
                process.kill()
        except OSError:
            pass

    try:
        process = subprocess.Popen(
            [
                str(executable_path),
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "core.pager=cat",
                "-c",
                "color.ui=false",
                "-c",
                "diff.external=",
                "-c",
                "credential.helper=",
                "-c",
                "protocol.file.allow=never",
                "-c",
                "http.sslVerify=true",
                *arguments,
            ],
            cwd=process_cwd,
            env=environment,
            stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        timer = Timer(10, stop_process)
        timer.daemon = True
        timer.start()
        try:
            if stdin_data is not None:
                process_stdin = getattr(process, "stdin", None)
                if process_stdin is None:
                    result = None
                    stop_process()
                else:
                    process_stdin.write(stdin_data)
                    process_stdin.close()
            if process.stdout is None:
                result = None
            else:
                raw = process.stdout.read(max_output_bytes + 1)
                if len(raw) > max_output_bytes:
                    stop_process()
                    result = None
                else:
                    result = raw if process.wait() == 0 else None
        finally:
            timer.cancel()
            stop_process()
            process.wait()
            process_stdin = getattr(process, "stdin", None)
            if process_stdin is not None and not process_stdin.closed:
                process_stdin.close()
            if process.stdout is not None:
                process.stdout.close()
    except (OSError, subprocess.SubprocessError):
        result = None
    finally:
        if isolated_remote_workspace is not None:
            try:
                isolated_remote_workspace.cleanup()
            except OSError:
                result = None
    if result is not None:
        budget = _VERIFICATION_READ_BUDGET.get()
        if budget is not None:
            total = budget["bytes"] + len(result)
            if total > MAX_VERIFICATION_TOTAL_BYTES:
                result = None
            else:
                budget["bytes"] = total
    if cache is not None:
        cache[key] = result
    return result


def _committed_blob(
    root: Path, revision: str, locator: str, expected_sha256: str
) -> bool:
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is None:
        return False
    if _evidence_git(root, "merge-base", "--is-ancestor", revision, "HEAD") is None:
        return False
    raw_size = _evidence_git(root, "cat-file", "-s", f"{revision}:{locator}")
    try:
        object_size = int(raw_size.decode("ascii").strip()) if raw_size is not None else -1
    except (UnicodeError, ValueError):
        return False
    if object_size < 0 or object_size > MAX_DOCUMENT_BYTES:
        return False
    committed = _evidence_git(root, "show", f"{revision}:{locator}")
    return committed is not None and hashlib.sha256(committed).hexdigest() == expected_sha256


def _binding_matches_generation(
    candidate: Mapping[str, Any], frozen: Mapping[str, Any]
) -> bool:
    return candidate.get("state") in {"frozen", "revoked"} and all(
        _same_typed_value(candidate.get(field), value)
        for field, value in frozen.items()
        if field != "state"
    )


def _successor_binding_preserves_profile(
    first_frozen: Mapping[str, Any], successor_frozen: Mapping[str, Any]
) -> bool:
    first_activation = first_frozen.get("cohortActivation")
    successor_activation = successor_frozen.get("cohortActivation")
    return (
        successor_frozen.get("state") == "frozen"
        and all(
            _same_typed_value(successor_frozen.get(field), value)
            for field, value in first_frozen.items()
            if field not in {"state", "cohortActivation"}
        )
        and isinstance(first_activation, dict)
        and isinstance(successor_activation, dict)
        and all(
            not _same_typed_value(successor_activation.get(field), first_activation.get(field))
            for field in {
                "surfaceIdentity",
                "activationCursorCommitment",
                "keyIdentity",
                "keyFingerprint",
            }
        )
    )


def _binding_authorization_valid(
    root: Path,
    label: str,
    document_kind: str,
    revision: str,
    binding_sha256: str,
    validator_id: str | None,
    errors: list[str],
    *,
    source_window_boundary: Mapping[str, Any] | None = None,
) -> bool:
    before = len(errors)
    authorization_evaluator = (
        SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS.get(validator_id)
        if isinstance(validator_id, str)
        else None
    )
    if authorization_evaluator is None:
        _error(
            errors,
            f"{label} frozen normative profile binding has no code-owned source authorization validator",
        )
        return False
    authorization_document = {
        "kind": document_kind,
        "revision": revision,
        "bindingSha256": binding_sha256,
    }
    if source_window_boundary is not None:
        if any(field in authorization_document for field in source_window_boundary):
            _error(errors, f"{label} authorization source window boundary is invalid")
            return False
        authorization_document.update(source_window_boundary)
    authorization_errors: list[str] = []
    try:
        authorization_verified = authorization_evaluator(
            authorization_document, root, authorization_errors
        )
    except Exception as exc:
        _error(
            authorization_errors,
            f"{label} frozen normative profile binding authorization validator failed closed: "
            f"{exc.__class__.__name__}",
        )
    else:
        if authorization_verified is not True and not authorization_errors:
            _error(
                authorization_errors,
                f"{label} frozen normative profile binding authorization source was not independently verified",
            )
    errors.extend(authorization_errors)
    return len(errors) == before


def _normative_profile_binding_history_valid(
    root: Path, current_binding: Mapping[str, Any], errors: list[str]
) -> bool:
    """Reject reset, re-freeze, history truncation, or side-lineage poisoning."""

    before = len(errors)
    inside_worktree = _evidence_git(root, "rev-parse", "--is-inside-work-tree")
    if inside_worktree is None:
        _error(errors, "normative profile binding history cannot be verified")
        return False
    history_floor_available = (
        _evidence_git(
            root,
            "merge-base",
            "--is-ancestor",
            NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION,
            "HEAD",
        )
        is not None
    )
    if not history_floor_available:
        _error(errors, "normative profile binding history floor is unavailable")
        return False
    revisions_raw = _evidence_git(
        root,
        "log",
        "--first-parent",
        "--topo-order",
        "--reverse",
        f"--max-count={MAX_NORMATIVE_BINDING_HISTORY_REVISIONS + 1}",
        "--format=%H",
        f"{NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION}..HEAD",
        "--",
        "product/program.json",
    )
    if revisions_raw is None:
        _error(errors, "normative profile binding history cannot be enumerated")
        return False
    try:
        revisions = revisions_raw.decode("ascii").splitlines()
    except UnicodeError:
        _error(errors, "normative profile binding history cannot be enumerated")
        return False
    if len(revisions) > MAX_NORMATIVE_BINDING_HISTORY_REVISIONS:
        _error(errors, "normative profile binding history exceeds its inspection bound")
        return False
    revisions.insert(0, NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION)
    if any(
        re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is None
        for revision in revisions
    ):
        _error(errors, "normative profile binding history contains an invalid revision")
        return False
    batch_request = b"".join(
        f"{revision}:product/program.json\n".encode("ascii")
        for revision in revisions
    )
    batch_raw = _evidence_git(
        root,
        "cat-file",
        "--batch",
        stdin_data=batch_request,
        max_output_bytes=MAX_NORMATIVE_BINDING_HISTORY_BYTES,
    )
    if batch_raw is None:
        _error(errors, "normative profile binding history cannot be inspected")
        return False
    expected_program_id = f"harness-product-program-{CURRENT_RELEASE}"
    first_frozen: dict[str, Any] | None = None
    first_frozen_revision: str | None = None
    active_frozen: dict[str, Any] | None = None
    successor_frozen: dict[str, Any] | None = None
    successor_frozen_revision: str | None = None
    predecessor_revoked: dict[str, Any] | None = None
    predecessor_revoked_revision: str | None = None
    binding_history_started = False
    generation = 0
    revoked = False
    prior_registration_seen = False
    cursor = 0
    for revision in revisions:
        header_end = batch_raw.find(b"\n", cursor)
        if header_end < 0:
            _error(errors, "normative profile binding history cannot be inspected")
            return False
        header = batch_raw[cursor:header_end].split()
        cursor = header_end + 1
        try:
            object_size = int(header[2].decode("ascii")) if len(header) == 3 else -1
        except (UnicodeError, ValueError):
            object_size = -1
        if (
            len(header) != 3
            or header[1] != b"blob"
            or object_size < 0
            or object_size > MAX_DOCUMENT_BYTES
            or cursor + object_size >= len(batch_raw)
            or batch_raw[cursor + object_size : cursor + object_size + 1] != b"\n"
        ):
            _error(errors, "normative profile binding history cannot be inspected")
            return False
        program_raw = batch_raw[cursor : cursor + object_size]
        cursor += object_size + 1
        historical_program = _parse_json_object_bytes(
            program_raw,
            f"historical product/program.json at {revision}",
            errors,
        )
        if historical_program.get("id") != expected_program_id:
            if binding_history_started:
                _error(errors, "v1 normative profile binding history is incomplete")
                return False
            continue
        historical_binding = historical_program.get("normativeProfileBinding")
        if not isinstance(historical_binding, dict) or set(
            historical_binding
        ) != NORMATIVE_PROFILE_BINDING_FIELDS:
            if binding_history_started:
                _error(errors, "v1 normative profile binding history is incomplete")
                return False
            continue
        historical_increments = historical_program.get("increments")
        if not isinstance(historical_increments, list):
            _error(errors, "v1 normative profile binding history has invalid increments")
            return False
        if any(
            isinstance(increment, dict)
            and increment.get("taskRegistration") is not None
            for increment in historical_increments
        ):
            prior_registration_seen = True
        binding_history_started = True
        binding_state = historical_binding.get("state")
        if binding_state == "unfrozen":
            if generation != 0:
                _error(errors, "frozen normative profile binding cannot return to unfrozen")
                return False
            continue
        if binding_state == "frozen":
            if generation == 0:
                first_frozen = dict(historical_binding)
                first_frozen_revision = revision
                active_frozen = first_frozen
                generation = 1
                revoked = False
                continue
            if not revoked:
                if active_frozen is None or not _same_typed_value(
                    historical_binding, active_frozen
                ):
                    _error(errors, "frozen normative profile binding changed within a generation")
                    return False
                continue
            if (
                generation != 1
                or first_frozen is None
                or successor_frozen is not None
                or prior_registration_seen
                or not _successor_binding_preserves_profile(
                    first_frozen, historical_binding
                )
            ):
                _error(
                    errors,
                    "successor cohort generation violates its single zero-outcome boundary",
                )
                return False
            successor_frozen = dict(historical_binding)
            successor_frozen_revision = revision
            active_frozen = successor_frozen
            generation = 2
            revoked = False
            continue
        if binding_state == "revoked":
            if active_frozen is None or not _binding_matches_generation(
                historical_binding, active_frozen
            ):
                _error(errors, "revoked normative profile binding must preserve its active generation")
                return False
            if not revoked and generation == 1:
                predecessor_revoked = dict(historical_binding)
                predecessor_revoked_revision = revision
            revoked = True
            continue
        _error(errors, "v1 normative profile binding history contains an invalid state")
        return False
    if cursor != len(batch_raw):
        _error(errors, "normative profile binding history cannot be inspected")
        return False

    current_state = current_binding.get("state")
    if current_state == "unfrozen":
        if generation != 0:
            _error(errors, "frozen normative profile binding cannot return to unfrozen")
    elif current_state == "frozen":
        if generation == 0:
            _error(errors, "frozen normative profile binding must exist in committed first-parent history")
        elif revoked:
            if (
                generation != 1
                or first_frozen is None
                or successor_frozen is not None
                or prior_registration_seen
                or not _successor_binding_preserves_profile(first_frozen, current_binding)
            ):
                _error(
                    errors,
                    "successor cohort generation violates its single zero-outcome boundary",
                )
            else:
                successor_frozen = dict(current_binding)
                active_frozen = successor_frozen
                generation = 2
                revoked = False
        elif active_frozen is None or not _same_typed_value(
            current_binding, active_frozen
        ):
            _error(errors, "current normative profile binding differs from its active generation")
    elif current_state == "revoked":
        if active_frozen is None or not _binding_matches_generation(
            current_binding, active_frozen
        ):
            _error(errors, "revoked normative profile binding must preserve its active generation")
        revoked = True
    else:
        _error(errors, "v1 normative profile binding history contains an invalid state")

    if first_frozen is not None:
        initial_revision = EXPECTED_V1_INITIAL_BINDING_REVISION
        initial_sha256 = EXPECTED_V1_INITIAL_BINDING_SHA256
        canonical_initial = json.dumps(
            first_frozen,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        initial_anchor_valid = (
            isinstance(initial_revision, str)
            and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", initial_revision)
            is not None
            and isinstance(initial_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", initial_sha256) is not None
            and first_frozen_revision == initial_revision
            and _evidence_git(
                root, "merge-base", "--is-ancestor", initial_revision, "HEAD"
            )
            is not None
            and hashlib.sha256(canonical_initial).hexdigest() == initial_sha256
        )
        if not initial_anchor_valid:
            _error(
                errors,
                "initial frozen normative profile binding is not code-pinned to canonical history",
            )
        elif generation == 1 and not revoked and len(errors) == before:
            _binding_authorization_valid(
                root,
                "initial",
                "initial-normative-profile-binding-authorization",
                initial_revision,
                initial_sha256,
                EXPECTED_V1_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID,
                errors,
            )

    if generation == 2 and successor_frozen is not None:
        successor_revision = EXPECTED_V1_SUCCESSOR_BINDING_REVISION
        successor_sha256 = EXPECTED_V1_SUCCESSOR_BINDING_SHA256
        canonical_successor = json.dumps(
            successor_frozen,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        canonical_predecessor_revoked = (
            json.dumps(
                predecessor_revoked,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if predecessor_revoked is not None
            else None
        )
        successor_anchor_valid = (
            isinstance(successor_revision, str)
            and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", successor_revision)
            is not None
            and isinstance(successor_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", successor_sha256) is not None
            and successor_frozen_revision == successor_revision
            and predecessor_revoked_revision
            == EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION
            and canonical_predecessor_revoked is not None
            and hashlib.sha256(canonical_predecessor_revoked).hexdigest()
            == EXPECTED_V1_PREDECESSOR_REVOCATION_BINDING_SHA256
            and _evidence_git(
                root, "merge-base", "--is-ancestor", successor_revision, "HEAD"
            )
            is not None
            and _evidence_git(
                root,
                "merge-base",
                "--is-ancestor",
                EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION,
                successor_revision,
            )
            is not None
            and hashlib.sha256(canonical_successor).hexdigest() == successor_sha256
        )
        if not successor_anchor_valid:
            _error(
                errors,
                "successor cohort binding is not code-pinned to canonical history",
            )
        elif not revoked and len(errors) == before:
            _binding_authorization_valid(
                root,
                "successor",
                "successor-normative-profile-binding-authorization",
                successor_revision,
                successor_sha256,
                EXPECTED_V1_SUCCESSOR_BINDING_AUTHORIZATION_VALIDATOR_ID,
                errors,
                source_window_boundary={
                    "predecessorRevocationRevision": (
                        EXPECTED_V1_PREDECESSOR_REVOCATION_REVISION
                    ),
                    "predecessorRevocationBindingSha256": (
                        EXPECTED_V1_PREDECESSOR_REVOCATION_BINDING_SHA256
                    ),
                    "sourceWindowRule": (
                        EXPECTED_SUCCESSOR_AUTHORIZATION_SOURCE_WINDOW_RULE
                    ),
                },
            )
    return len(errors) == before


def _current_normative_profile_binding_history_valid(
    root: Path,
    current_binding: Mapping[str, Any],
    errors: list[str],
    *,
    allow_authorization: bool = True,
) -> bool:
    """Enforce one irreversible v1.1 generation from the current authority floor."""

    before = len(errors)
    inside_worktree = _evidence_git(root, "rev-parse", "--is-inside-work-tree")
    if inside_worktree is None:
        _error(errors, "current normative profile binding history cannot be verified")
        return False
    if (
        _evidence_git(
            root,
            "merge-base",
            "--is-ancestor",
            CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION,
            "HEAD",
        )
        is None
    ):
        _error(errors, "current normative profile binding history floor is unavailable")
        return False
    revisions_raw = _evidence_git(
        root,
        "log",
        "--first-parent",
        "--topo-order",
        "--reverse",
        f"--max-count={MAX_NORMATIVE_BINDING_HISTORY_REVISIONS + 1}",
        "--format=%H",
        f"{CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION}..HEAD",
        "--",
        "product/program.json",
    )
    if revisions_raw is None:
        _error(errors, "current normative profile binding history cannot be enumerated")
        return False
    try:
        revisions = revisions_raw.decode("ascii").splitlines()
    except UnicodeError:
        _error(errors, "current normative profile binding history cannot be enumerated")
        return False
    if len(revisions) > MAX_NORMATIVE_BINDING_HISTORY_REVISIONS:
        _error(errors, "current normative profile binding history exceeds its inspection bound")
        return False
    revisions.insert(0, CURRENT_NORMATIVE_PROFILE_BINDING_HISTORY_FLOOR_REVISION)
    if any(
        re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is None
        for revision in revisions
    ):
        _error(errors, "current normative profile binding history contains an invalid revision")
        return False
    batch_request = b"".join(
        f"{revision}:product/program.json\n".encode("ascii")
        for revision in revisions
    )
    batch_raw = _evidence_git(
        root,
        "cat-file",
        "--batch",
        stdin_data=batch_request,
        max_output_bytes=MAX_NORMATIVE_BINDING_HISTORY_BYTES,
    )
    if batch_raw is None:
        _error(errors, "current normative profile binding history cannot be inspected")
        return False

    expected_program_id = f"harness-product-program-{CURRENT_RELEASE}"
    first_frozen: dict[str, Any] | None = None
    first_frozen_revision: str | None = None
    binding_history_started = False
    revoked = False
    cursor = 0
    for revision in revisions:
        header_end = batch_raw.find(b"\n", cursor)
        if header_end < 0:
            _error(errors, "current normative profile binding history cannot be inspected")
            return False
        header = batch_raw[cursor:header_end].split()
        cursor = header_end + 1
        try:
            object_size = int(header[2].decode("ascii")) if len(header) == 3 else -1
        except (UnicodeError, ValueError):
            object_size = -1
        if (
            len(header) != 3
            or header[1] != b"blob"
            or object_size < 0
            or object_size > MAX_DOCUMENT_BYTES
            or cursor + object_size >= len(batch_raw)
            or batch_raw[cursor + object_size : cursor + object_size + 1] != b"\n"
        ):
            _error(errors, "current normative profile binding history cannot be inspected")
            return False
        program_raw = batch_raw[cursor : cursor + object_size]
        cursor += object_size + 1
        historical_program = _parse_json_object_bytes(
            program_raw,
            f"historical product/program.json at {revision}",
            errors,
        )
        if historical_program.get("id") != expected_program_id:
            if binding_history_started:
                _error(errors, "v1.1 normative profile binding history is incomplete")
                return False
            continue
        historical_binding = historical_program.get("normativeProfileBinding")
        if not isinstance(historical_binding, dict) or set(
            historical_binding
        ) != NORMATIVE_PROFILE_BINDING_FIELDS:
            if binding_history_started:
                _error(errors, "v1.1 normative profile binding history is incomplete")
                return False
            continue
        binding_history_started = True
        binding_state = historical_binding.get("state")
        if binding_state == "unfrozen":
            if first_frozen is not None:
                _error(errors, "frozen v1.1 normative profile binding cannot return to unfrozen")
                return False
            continue
        if binding_state == "frozen":
            if first_frozen is None:
                first_frozen = dict(historical_binding)
                first_frozen_revision = revision
                revoked = False
                continue
            if revoked:
                _error(errors, "revoked v1.1 cohort cannot open a successor generation")
                return False
            if not _same_typed_value(historical_binding, first_frozen):
                _error(errors, "frozen v1.1 normative profile binding changed")
                return False
            continue
        if binding_state == "revoked":
            if first_frozen is None or not _binding_matches_generation(
                historical_binding, first_frozen
            ):
                _error(errors, "revoked v1.1 binding must preserve its only generation")
                return False
            revoked = True
            continue
        _error(errors, "v1.1 normative profile binding history contains an invalid state")
        return False
    if cursor != len(batch_raw):
        _error(errors, "current normative profile binding history cannot be inspected")
        return False

    current_state = current_binding.get("state")
    if current_state == "unfrozen":
        if first_frozen is not None:
            _error(errors, "frozen v1.1 normative profile binding cannot return to unfrozen")
    elif current_state == "frozen":
        if first_frozen is None:
            _error(
                errors,
                "frozen v1.1 normative profile binding must exist in committed first-parent history",
            )
        elif revoked:
            _error(errors, "revoked v1.1 cohort cannot open a successor generation")
        elif not _same_typed_value(current_binding, first_frozen):
            _error(errors, "current v1.1 binding differs from its only generation")
    elif current_state == "revoked":
        if first_frozen is None or not _binding_matches_generation(
            current_binding, first_frozen
        ):
            _error(errors, "revoked v1.1 binding must preserve its only generation")
        revoked = True
    else:
        _error(errors, "v1.1 normative profile binding history contains an invalid state")

    if first_frozen is not None:
        canonical = json.dumps(
            first_frozen,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        anchor_revision = EXPECTED_CURRENT_INITIAL_BINDING_REVISION
        anchor_sha256 = EXPECTED_CURRENT_INITIAL_BINDING_SHA256
        anchor_valid = (
            isinstance(anchor_revision, str)
            and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", anchor_revision)
            is not None
            and isinstance(anchor_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", anchor_sha256) is not None
            and first_frozen_revision == anchor_revision
            and _evidence_git(
                root, "merge-base", "--is-ancestor", anchor_revision, "HEAD"
            )
            is not None
            and hashlib.sha256(canonical).hexdigest() == anchor_sha256
        )
        if not anchor_valid:
            _error(
                errors,
                "initial v1.1 frozen binding is not code-pinned to canonical history",
            )
        elif not _current_initial_authorization_anchors_valid(
            first_frozen.get("cohortActivation")
            if isinstance(first_frozen.get("cohortActivation"), dict)
            else None,
            errors,
        ):
            pass
        elif current_state == "frozen" and allow_authorization and not errors:
            _binding_authorization_valid(
                root,
                "current v1.1",
                "v1.1-normative-profile-binding-authorization",
                anchor_revision,
                anchor_sha256,
                EXPECTED_CURRENT_INITIAL_BINDING_AUTHORIZATION_VALIDATOR_ID,
                errors,
                source_window_boundary={
                    "environmentAttributionContractSha256": (
                        EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
                    ),
                    "environmentManifestBoundary": (
                        EXPECTED_CURRENT_INITIAL_ENVIRONMENT_MANIFEST_BOUNDARY
                    ),
                },
            )
    return len(errors) == before


def _strict_git_ancestor(root: Path, ancestor: Any, descendant: Any) -> bool:
    if (
        not isinstance(ancestor, str)
        or not isinstance(descendant, str)
        or ancestor == descendant
        or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", ancestor) is None
        or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", descendant) is None
    ):
        return False
    return (
        _evidence_git(root, "merge-base", "--is-ancestor", ancestor, descendant)
        is not None
    )


def _registration_added_at_revision(root: Path, revision: str, locator: str) -> bool:
    raw = _evidence_git(
        root,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "--diff-filter=A",
        "-r",
        revision,
        "--",
        locator,
    )
    if raw is None:
        return False
    try:
        return raw.decode("utf-8").splitlines() == [locator]
    except UnicodeError:
        return False


def _registration_parent_has_profile_binding(
    root: Path,
    revision: str,
    profile_binding: Mapping[str, Any],
    errors: list[str],
) -> bool:
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is None:
        return False
    parents_raw = _evidence_git(root, "rev-list", "--parents", "-n", "1", revision)
    if parents_raw is None:
        return False
    try:
        ancestry = parents_raw.decode("ascii").strip().split()
    except UnicodeError:
        return False
    if len(ancestry) != 2 or ancestry[0] != revision:
        return False
    parent = ancestry[1]
    program_object = f"{parent}:product/program.json"
    raw_size = _evidence_git(root, "cat-file", "-s", program_object)
    try:
        object_size = int(raw_size.decode("ascii").strip()) if raw_size is not None else -1
    except (UnicodeError, ValueError):
        return False
    if object_size < 0 or object_size > MAX_DOCUMENT_BYTES:
        return False
    program_raw = _evidence_git(root, "show", program_object)
    if program_raw is None or len(program_raw) != object_size:
        return False
    parent_program = _parse_json_object_bytes(
        program_raw,
        "task registration parent product/program.json",
        errors,
    )
    parent_binding = parent_program.get("normativeProfileBinding")
    return _same_typed_value(parent_binding, dict(profile_binding))


def _registration_history_paths(
    root: Path, frozen_at_revision: Any, errors: list[str]
) -> set[str] | None:
    if not isinstance(frozen_at_revision, str):
        _error(errors, "cannot enumerate cohort registrations without a freeze revision")
        return None
    raw = _evidence_git(
        root,
        "log",
        "--format=",
        "--name-status",
        "-z",
        f"{frozen_at_revision}..HEAD",
        "--",
        "product/evidence",
    )
    if raw is None:
        _error(errors, "cohort registration history cannot be enumerated")
        return None
    tokens = raw.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()
    paths: set[str] = set()
    index = 0
    try:
        while index < len(tokens):
            status = tokens[index].decode("ascii")
            index += 1
            path_count = 2 if status.startswith(("R", "C")) else 1
            if index + path_count > len(tokens):
                raise ValueError
            changed = [tokens[index + offset].decode("utf-8") for offset in range(path_count)]
            index += path_count
            registration_paths = [
                path
                for path in changed
                if PurePosixPath(path).parent == PurePosixPath("product/evidence")
                and PurePosixPath(path).name.endswith("-registration.json")
            ]
            if not registration_paths:
                continue
            if status == "D" or status.startswith(("R", "C")):
                _error(
                    errors,
                    "cohort registration artifacts are append-only and cannot be deleted, renamed or copied",
                )
            paths.update(registration_paths)
    except (UnicodeError, ValueError):
        _error(errors, "cohort registration history is malformed")
        return None
    return paths


class _InvalidJson(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJson(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise _InvalidJson(f"non-finite constant: {value}")


def _parse_json(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
    )


def _error(errors: list[str], message: str) -> None:
    if message in errors or DIAGNOSTIC_LIMIT_MESSAGE in errors:
        return
    if len(errors) < MAX_VERIFICATION_DIAGNOSTICS - 1:
        errors.append(message)
    else:
        errors.append(DIAGNOSTIC_LIMIT_MESSAGE)


def _read_bounded_bytes(path: Path, label: str, errors: list[str]) -> bytes | None:
    budget = _VERIFICATION_READ_BUDGET.get()
    try:
        if _link_or_reparse(path):
            _error(errors, f"{label} cannot be a link or reparse point")
            return None
        canonical = os.path.normcase(str(path.resolve(strict=True)))
        if budget is not None:
            cached = budget["files"].get(canonical)
            if cached is not None:
                return cached
        with path.open("rb") as stream:
            raw = stream.read(MAX_DOCUMENT_BYTES + 1)
    except FileNotFoundError:
        _error(errors, f"missing {label}")
        return None
    except OSError as exc:
        _error(errors, f"cannot read {label}: {exc.__class__.__name__}")
        return None
    if len(raw) > MAX_DOCUMENT_BYTES:
        _error(errors, f"cannot read {label}: byte limit exceeded")
        return None
    if budget is not None:
        files = budget["files"]
        if len(files) >= MAX_VERIFICATION_FILES:
            _error(errors, "verification file limit exceeded")
            return None
        total = budget["bytes"] + len(raw)
        if total > MAX_VERIFICATION_TOTAL_BYTES:
            _error(errors, "verification cumulative byte limit exceeded")
            return None
        files[canonical] = raw
        budget["bytes"] = total
    return raw


def _json_within_resource_limits(value: Any) -> bool:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            return False
        if isinstance(current, str):
            if len(current) > MAX_JSON_STRING_CHARACTERS:
                return False
        elif isinstance(current, dict):
            if len(current) > MAX_JSON_CONTAINER_ITEMS:
                return False
            for key, item in current.items():
                if len(key) > MAX_JSON_STRING_CHARACTERS:
                    return False
                stack.append((item, depth + 1))
        elif isinstance(current, list):
            if len(current) > MAX_JSON_CONTAINER_ITEMS:
                return False
            stack.extend((item, depth + 1) for item in current)
    return True


def _parse_json_object_bytes(
    raw: bytes, label: str, errors: list[str]
) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        value = _parse_json(text)
    except (json.JSONDecodeError, _InvalidJson, RecursionError, UnicodeError):
        _error(errors, f"cannot read {label}: invalid JSON")
        return {}
    if not _json_within_resource_limits(value):
        _error(errors, f"cannot read {label}: JSON resource limit exceeded")
        return {}
    if not isinstance(value, dict):
        _error(errors, f"{label} must be a JSON object")
        return {}
    return value


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    raw = _read_bounded_bytes(path, label, errors)
    if raw is None:
        return {}
    return _parse_json_object_bytes(raw, label, errors)


def _load_authority_json(
    root: Path, relative: str, label: str, errors: list[str]
) -> dict[str, Any]:
    path = _inside_root(root, relative, errors, label)
    if path is None:
        return {}
    return _load_json(path, label, errors)


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        return None
    if len(value) != len(set(value)):
        return None
    return value


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _substantive_registration_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return not isinstance(value, bool) and (
            not isinstance(value, float) or math.isfinite(value)
        )
    if isinstance(value, list):
        return bool(value) and all(
            _substantive_registration_value(item) for item in value
        )
    if isinstance(value, dict):
        return bool(value) and all(
            isinstance(key, str)
            and bool(key.strip())
            and _substantive_registration_value(item)
            for key, item in value.items()
        )
    return False


def _same_typed_value(value: Any, expected: Any) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(
            _same_typed_value(value[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(value) == len(expected) and all(
            _same_typed_value(item, expected_item)
            for item, expected_item in zip(value, expected)
        )
    return value == expected


def _criteria_contract_digest(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    by_id: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            return None
        criterion_id = item.get("id")
        if not isinstance(criterion_id, str) or criterion_id in by_id:
            return None
        by_id[criterion_id] = item
    if set(by_id) != EXPECTED_CRITERION_IDS:
        return None
    contract: list[dict[str, Any]] = []
    for criterion_id in sorted(EXPECTED_CRITERION_IDS):
        fields = set(CRITERION_CONTRACT_BASE_FIELDS)
        if criterion_id in OUTCOME_IDS:
            fields.add("operationalization")
        item = by_id[criterion_id]
        contract.append({field: item.get(field) for field in sorted(fields)})
    payload = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _relative_locator(value: Any, *, allow_evidence: bool = False) -> str | None:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return None
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        return None
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in parts):
        return None
    folded = {part.casefold() for part in parts}
    excluded = EXCLUDED_AUTHORITY_PARTS - ({"evidence"} if allow_evidence else set())
    if folded & excluded:
        return None
    return PurePosixPath(*parts).as_posix()


def _cleanup_locator(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return None
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        return None
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in parts):
        return None
    forbidden = {".git", "evidence", "fixtures", "legacy"}
    if {part.casefold() for part in parts} & forbidden:
        return None
    return PurePosixPath(*parts).as_posix()


def _link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse)


def _inside_root(root: Path, relative: str, errors: list[str], label: str) -> Path | None:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    try:
        current = root
        for part in PurePosixPath(relative).parts:
            current = current / part
            if _link_or_reparse(current):
                _error(errors, f"{label} cannot traverse a link or reparse point: {relative}")
                return None
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        _error(errors, f"{label} escapes repository root: {relative}")
        return None
    return candidate


def _path_entry_absent(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _rfc3339_instant(value: Any) -> Decimal | None:
    if not isinstance(value, str) or RFC3339.fullmatch(value) is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    offset_start = len(normalized) - 6
    if offset_start <= 18 or normalized[offset_start] not in {"+", "-"}:
        return None
    head = normalized[:offset_start]
    offset = normalized[offset_start:]
    fraction = ""
    if "." in head:
        prefix, fraction = head.split(".", 1)
        head = prefix
    try:
        moment = datetime.fromisoformat(head + offset).astimezone(timezone.utc)
    except ValueError:
        return None
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = moment - epoch
    seconds = Decimal(delta.days * 86400 + delta.seconds)
    if fraction:
        seconds += Decimal(f"0.{fraction}")
    return seconds
def _authority_files(
    root: Path, constitution: dict[str, Any], errors: list[str]
) -> list[tuple[str, Path]]:
    required = _string_list(constitution.get("requiredAuthorityFiles"))
    globs = _string_list(constitution.get("activeAuthorityGlobs"))
    if required is None or set(required) != BOOTSTRAP_REQUIRED_AUTHORITY:
        _error(errors, "requiredAuthorityFiles must equal the code-owned bootstrap set")
        required = sorted(BOOTSTRAP_REQUIRED_AUTHORITY)
    if globs is None or set(globs) != EXPECTED_AUTHORITY_GLOBS:
        _error(errors, "activeAuthorityGlobs must equal the code-owned lean authority globs")

    found: dict[str, Path] = {}
    product_root = _inside_root(root, "product", errors, "product authority root")
    if product_root is not None:
        try:
            with os.scandir(product_root) as entries:
                for index, entry in enumerate(entries, start=1):
                    if index > MAX_AUTHORITY_WALK_ENTRIES:
                        _error(errors, "product authority root entry limit exceeded")
                        break
                    if Path(entry.name).suffix.casefold() != ".json":
                        continue
                    candidate = product_root / entry.name
                    relative = candidate.relative_to(root).as_posix()
                    if relative not in BOOTSTRAP_REQUIRED_AUTHORITY:
                        _error(errors, f"undeclared product authority JSON: {relative}")
        except (OSError, RuntimeError, ValueError):
            _error(errors, "product authority root cannot be enumerated")
    for raw in required:
        relative = _relative_locator(raw)
        if relative is None:
            _error(errors, f"invalid required authority locator: {raw!r}")
            continue
        candidate = _inside_root(root, relative, errors, "authority file")
        if candidate is None:
            continue
        try:
            if not candidate.is_file():
                _error(errors, f"required authority file is missing: {relative}")
                continue
        except OSError:
            _error(errors, f"required authority file cannot be inspected: {relative}")
            continue
        found[relative] = candidate

    harness_root = _inside_root(root, "harness", errors, "Harness authority root")
    if harness_root is not None:
        authority_entries = 0
        pending = [harness_root]
        while pending:
            current_path = pending.pop()
            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        authority_entries += 1
                        if authority_entries > MAX_AUTHORITY_WALK_ENTRIES:
                            _error(errors, "Harness authority closure entry limit exceeded")
                            pending.clear()
                            break
                        candidate = Path(entry.path)
                        relative = candidate.relative_to(root).as_posix()
                        if _link_or_reparse(candidate):
                            if (
                                current_path == harness_root
                                and candidate.suffix.casefold() == ".py"
                            ):
                                _inside_root(root, relative, errors, "active authority")
                            else:
                                _error(
                                    errors,
                                    f"undeclared Harness authority link: {relative}",
                                )
                            continue
                        try:
                            is_directory = entry.is_dir(follow_symlinks=False)
                        except OSError:
                            _error(errors, "Harness authority closure cannot be enumerated")
                            continue
                        if is_directory:
                            if entry.name.casefold() != "__pycache__":
                                pending.append(candidate)
                            continue
                        if current_path != harness_root or candidate.suffix.casefold() != ".py":
                            _error(errors, f"undeclared Harness authority file: {relative}")
                            continue
                        checked = _inside_root(root, relative, errors, "active authority")
                        if checked is None:
                            continue
                        try:
                            if not checked.is_file():
                                _error(errors, f"active authority path is invalid: {relative}")
                                continue
                            checked.resolve(strict=True).relative_to(root.resolve(strict=True))
                        except (OSError, RuntimeError, ValueError):
                            _error(errors, f"active authority path is invalid: {relative}")
                            continue
                        found[relative] = checked
            except (OSError, RuntimeError, ValueError):
                _error(errors, "Harness authority closure cannot be enumerated")
    return sorted(found.items())


def _authority_identity_valid(
    files: list[tuple[str, Path]], errors: list[str]
) -> bool:
    before = len(errors)
    for relative, path in files:
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
            if pattern.search(relative):
                _error(errors, f"forbidden predecessor authority path: {relative}")
        raw = _read_bounded_bytes(path, f"active authority {relative}", errors)
        if raw is None:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            _error(errors, f"active authority cannot be read: {relative}")
            continue
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
            if pattern.search(text):
                _error(errors, f"forbidden predecessor identity in active authority: {relative}")
        if path.suffix.casefold() == ".json":
            parse_errors: list[str] = []
            document = _parse_json_object_bytes(
                raw, f"active authority {relative}", parse_errors
            )
            if parse_errors:
                _error(errors, f"active authority JSON is invalid or unbounded: {relative}")
                continue
            stack: list[Any] = [document]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    stack.extend(value.keys())
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)
                elif isinstance(value, str):
                    for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
                        if pattern.search(value):
                            _error(
                                errors,
                                f"forbidden predecessor semantic identity in active authority: {relative}",
                            )
    return len(errors) == before


def _v10_historical_authority_valid(root: Path, errors: list[str]) -> bool:
    before = len(errors)
    for locator, expected_sha256 in EXPECTED_V10_AUTHORITY_BLOBS.items():
        if not _committed_blob(
            root,
            EXPECTED_V10_RELEASE["revision"],
            locator,
            expected_sha256,
        ):
            _error(errors, f"v1.0 historical authority identity changed: {locator}")
    return len(errors) == before


def _v11_historical_authority_valid(root: Path, errors: list[str]) -> bool:
    before = len(errors)
    for locator, expected_sha256 in EXPECTED_V11_AUTHORITY_BLOBS.items():
        if not _committed_blob(
            root,
            EXPECTED_PRIOR_RELEASE["revision"],
            locator,
            expected_sha256,
        ):
            _error(errors, f"v1.1 historical authority identity changed: {locator}")
    return len(errors) == before


def _historical_boundary_valid(
    root: Path,
    constitution: dict[str, Any],
    program: dict[str, Any],
    errors: list[str],
) -> bool:
    before = len(errors)
    prior = program.get("priorRelease")
    if not _same_typed_value(prior, EXPECTED_PRIOR_RELEASE):
        _error(
            errors,
            "program priorRelease must match the code-owned historical milestone",
        )
    if not _same_typed_value(
        constitution.get("historicalEvidenceBoundary"),
        EXPECTED_HISTORICAL_EVIDENCE_BOUNDARY,
    ):
        _error(errors, "constitution historicalEvidenceBoundary is invalid")
    milestones = constitution.get("historicalMilestones")
    if not isinstance(milestones, list) or not _same_typed_value(
        milestones, list(EXPECTED_HISTORICAL_MILESTONES)
    ):
        _error(
            errors,
            "constitution historical milestones must match the code-owned records",
        )
    _v10_historical_authority_valid(root, errors)
    _v11_historical_authority_valid(root, errors)
    return len(errors) == before


def _supporting_documents_exist(
    root: Path, constitution: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    documents = _string_list(constitution.get("supportingDocuments"))
    if documents is None:
        _error(errors, "supportingDocuments must be a non-empty unique string list")
        return False
    if set(documents) != EXPECTED_REQUIRED_SUPPORTING_DOCUMENTS:
        _error(errors, "supportingDocuments must equal the code-owned semantic document set")
    for raw in documents:
        relative = _relative_locator(raw)
        if relative is None:
            _error(errors, f"invalid supporting document locator: {raw!r}")
            continue
        candidate = _inside_root(root, relative, errors, "supporting document")
        if candidate is None:
            continue
        try:
            if not candidate.is_file():
                _error(errors, f"supporting document is missing: {relative}")
                continue
        except OSError:
            _error(errors, f"supporting document cannot be inspected: {relative}")
            continue
        raw_document = _read_bounded_bytes(
            candidate, f"supporting document {relative}", errors
        )
        if raw_document is None:
            continue
        try:
            substantive = bool(raw_document.decode("utf-8").strip())
        except UnicodeError:
            _error(errors, f"supporting document cannot be inspected: {relative}")
            continue
        if not substantive:
            _error(errors, f"supporting document is empty: {relative}")
    return len(errors) == before


def _frozen_v02_profile_artifacts_valid(root: Path, errors: list[str]) -> bool:
    before = len(errors)
    for relative, expected_sha256 in FROZEN_V02_PROFILE_ARTIFACT_SHA256.items():
        candidate = _inside_root(root, relative, errors, "frozen v0.2 profile artifact")
        if candidate is None:
            continue
        raw = _read_bounded_bytes(
            candidate, f"frozen v0.2 profile artifact {relative}", errors
        )
        if raw is None:
            continue
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            _error(errors, f"frozen v0.2 profile artifact identity changed: {relative}")
    return len(errors) == before


def _cohort_activation_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == COHORT_ACTIVATION_FIELDS
        and isinstance(value.get("surfaceIdentity"), str)
        and PUBLIC_SURFACE_IDENTITY_PATTERN.fullmatch(value["surfaceIdentity"])
        is not None
        and isinstance(value.get("activationCursorCommitment"), str)
        and SHA256_COMMITMENT_PATTERN.fullmatch(value["activationCursorCommitment"])
        is not None
        and value["activationCursorCommitment"].startswith("hmac-sha256:")
        and isinstance(value.get("keyIdentity"), str)
        and PUBLIC_COHORT_KEY_IDENTITY_PATTERN.fullmatch(value["keyIdentity"])
        is not None
        and isinstance(value.get("keyFingerprint"), str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", value["keyFingerprint"])
        is not None
        and value.get("sourceMessageRule") == EXPECTED_SOURCE_MESSAGE_RULE
        and value.get("hmacDomain") == EXPECTED_HMAC_DOMAIN
        and value.get("surfaceTransitionRule")
        == EXPECTED_SURFACE_TRANSITION_RULE
        and value.get("keyRetentionRule") == EXPECTED_KEY_RETENTION_RULE
    )


def _current_cohort_activation_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == COHORT_ACTIVATION_FIELDS
        and isinstance(value.get("surfaceIdentity"), str)
        and PUBLIC_SURFACE_IDENTITY_PATTERN.fullmatch(value["surfaceIdentity"])
        is not None
        and isinstance(value.get("activationCursorCommitment"), str)
        and SHA256_COMMITMENT_PATTERN.fullmatch(value["activationCursorCommitment"])
        is not None
        and value["activationCursorCommitment"].startswith("hmac-sha256:")
        and isinstance(value.get("keyIdentity"), str)
        and PUBLIC_COHORT_KEY_IDENTITY_PATTERN.fullmatch(value["keyIdentity"])
        is not None
        and isinstance(value.get("keyFingerprint"), str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", value["keyFingerprint"])
        is not None
        and value.get("sourceMessageRule") == EXPECTED_CURRENT_SOURCE_MESSAGE_RULE
        and value.get("hmacDomain") == EXPECTED_CURRENT_HMAC_DOMAIN
        and value.get("surfaceTransitionRule")
        == EXPECTED_SURFACE_TRANSITION_RULE
        and value.get("keyRetentionRule") == EXPECTED_KEY_RETENTION_RULE
    )


def _v1_candidate_artifacts_valid(root: Path, errors: list[str]) -> bool:
    before = len(errors)
    expected = (
        (EXPECTED_V1_PROFILE_LOCATOR, EXPECTED_V1_PROFILE_SHA256),
        (
            EXPECTED_V1_COHORT_PROTOCOL_LOCATOR,
            EXPECTED_V1_COHORT_PROTOCOL_SHA256,
        ),
    )
    for locator, digest in expected:
        candidate = _inside_root(root, locator, errors, "v1 candidate artifact")
        if candidate is None:
            continue
        raw = _read_bounded_bytes(candidate, f"v1 candidate artifact {locator}", errors)
        if (
            raw is not None
            and hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
            != digest
        ):
            _error(errors, f"code-owned v1 candidate artifact identity changed: {locator}")
    return len(errors) == before


# Review-time integrity seam only. A pre-freeze candidate is not product
# authority and therefore must not become a verifier prerequisite until the
# program explicitly freezes and binds it through _normative_profile_binding_valid.
def _current_profile_candidate_artifacts_valid(
    root: Path, errors: list[str]
) -> bool:
    before = len(errors)
    expected = (
        (
            EXPECTED_CURRENT_PROFILE_CANDIDATE_LOCATOR,
            EXPECTED_CURRENT_PROFILE_CANDIDATE_SHA256,
        ),
        (
            EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_LOCATOR,
            EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_SHA256,
        ),
    )
    for locator, digest in expected:
        candidate = _inside_root(
            root, locator, errors, "current profile candidate artifact"
        )
        if candidate is None:
            continue
        raw = _read_bounded_bytes(
            candidate, f"current profile candidate artifact {locator}", errors
        )
        if (
            raw is not None
            and hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
            != digest
        ):
            _error(
                errors,
                f"code-owned current profile candidate artifact identity changed: {locator}",
            )
    return len(errors) == before


def _current_profile_binding_material_valid(
    root: Path, binding: Mapping[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    state = binding.get("state")
    locator = _relative_locator(binding.get("locator"))
    profile_identity = binding.get("profileIdentity")
    profile_sha256 = binding.get("sha256")
    protocol_identity = binding.get("cohortProtocolIdentity")
    protocol_locator = _relative_locator(binding.get("cohortProtocolLocator"))
    protocol_sha256 = binding.get("cohortProtocolSha256")
    artifact_revision = binding.get("frozenAtRevision")
    if (
        state not in {"frozen", "revoked"}
        or profile_identity != EXPECTED_CURRENT_PROFILE_CANDIDATE_IDENTITY
        or locator != EXPECTED_CURRENT_PROFILE_CANDIDATE_LOCATOR
        or profile_sha256 != EXPECTED_CURRENT_PROFILE_CANDIDATE_SHA256
        or protocol_identity
        != EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_IDENTITY
        or protocol_locator
        != EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_LOCATOR
        or protocol_sha256
        != EXPECTED_CURRENT_COHORT_PROTOCOL_CANDIDATE_SHA256
        or artifact_revision != EXPECTED_CURRENT_PROFILE_ARTIFACT_REVISION
        or not _current_cohort_activation_valid(binding.get("cohortActivation"))
    ):
        _error(errors, "frozen normative profile binding is not the code-owned v1.1 candidate")
        return False

    profile_path = _inside_root(root, locator, errors, "v1.1 normative profile")
    if profile_path is None:
        return False
    profile_raw = _read_bounded_bytes(
        profile_path, f"v1.1 normative profile {locator}", errors
    )
    if profile_raw is None:
        return False
    if (
        hashlib.sha256(profile_raw.replace(b"\r\n", b"\n")).hexdigest()
        != profile_sha256
        or not _committed_blob(root, artifact_revision, locator, profile_sha256)
    ):
        _error(errors, "frozen v1.1 normative profile identity or source revision mismatch")

    protocol_path = _inside_root(
        root, protocol_locator, errors, "v1.1 cohort protocol"
    )
    if protocol_path is None:
        return False
    protocol_raw = _read_bounded_bytes(
        protocol_path,
        f"v1.1 cohort protocol {protocol_locator}",
        errors,
    )
    if protocol_raw is None:
        return False
    if (
        hashlib.sha256(protocol_raw.replace(b"\r\n", b"\n")).hexdigest()
        != protocol_sha256
        or not _committed_blob(
            root,
            artifact_revision,
            protocol_locator,
            protocol_sha256,
        )
    ):
        _error(errors, "frozen v1.1 cohort protocol identity or source revision mismatch")
        return len(errors) == before
    protocol = _parse_json_object_bytes(
        protocol_raw,
        f"v1.1 cohort protocol {protocol_locator}",
        errors,
    )
    protocol_valid = (
        set(protocol) == CURRENT_COHORT_PROTOCOL_FIELDS
        and type(protocol.get("schema")) is int
        and protocol.get("schema") == 1
        and _nonempty_text(protocol.get("id"))
        and protocol.get("profileIdentity") == profile_identity
        and protocol.get("cohortProtocolIdentity") == protocol_identity
        and all(
            protocol.get(field) == expected
            for field, expected in EXPECTED_CURRENT_COHORT_PROTOCOL_RULES.items()
        )
        and _string_list(protocol.get("claimLimits")) is not None
    )
    if not protocol_valid:
        _error(errors, "frozen v1.1 cohort protocol shape is invalid")
    return len(errors) == before


def _normative_profile_binding_valid(
    root: Path, program: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    binding = program.get("normativeProfileBinding")
    if not isinstance(binding, dict) or set(binding) != NORMATIVE_PROFILE_BINDING_FIELDS:
        _error(errors, "program normativeProfileBinding fields must match the code-owned schema")
        return False
    binding_state = binding.get("state")
    if binding.get("state") == "unfrozen":
        if _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY:
            _normative_profile_binding_history_valid(root, binding, errors)
        else:
            _current_normative_profile_binding_history_valid(root, binding, errors)
        if not _same_typed_value(binding, UNFROZEN_NORMATIVE_PROFILE_BINDING):
            _error(errors, "unfrozen normative profile binding must contain only null identities")
        if program.get("status") == "stopped":
            _error(errors, "stopped v1.1 program requires its only cohort to be revoked")
        return len(errors) == before
    if not CURRENT_PROFILE_FREEZE_ENABLED:
        _error(errors, "current normative profile freeze is not enabled")
        return False
    if not _LEGACY_V10_PROFILE_MECHANISM_TEST_ONLY:
        material_valid = _current_profile_binding_material_valid(root, binding, errors)
        _current_normative_profile_binding_history_valid(
            root,
            binding,
            errors,
            allow_authorization=material_valid and not errors,
        )
        if binding_state == "revoked":
            if program.get("status") != "stopped":
                _error(errors, "revoked v1.1 cohort requires a stopped program")
            _current_initial_authorization_private_resource_absent(errors)
            _current_initial_expiry_cleanup_trigger_absent(errors)
        elif binding_state == "frozen":
            if program.get("status") == "stopped":
                _error(errors, "stopped v1.1 program requires its only cohort to be revoked")
        else:
            _error(errors, "program normative profile binding state must be unfrozen, frozen or revoked")
        return len(errors) == before
    _normative_profile_binding_history_valid(root, binding, errors)
    _v1_candidate_artifacts_valid(root, errors)
    if binding_state not in {"frozen", "revoked"}:
        _error(errors, "program normative profile binding state must be unfrozen, frozen or revoked")
        return False
    locator = _relative_locator(binding.get("locator"))
    profile_identity = binding.get("profileIdentity")
    cohort_protocol_identity = binding.get("cohortProtocolIdentity")
    cohort_protocol_locator = _relative_locator(binding.get("cohortProtocolLocator"))
    expected_sha256 = binding.get("sha256")
    cohort_protocol_sha256 = binding.get("cohortProtocolSha256")
    revision = binding.get("frozenAtRevision")
    if (
        locator != EXPECTED_V1_PROFILE_LOCATOR
        or profile_identity != EXPECTED_V1_PROFILE_IDENTITY
        or expected_sha256 != EXPECTED_V1_PROFILE_SHA256
        or cohort_protocol_identity != EXPECTED_V1_COHORT_PROTOCOL_IDENTITY
        or cohort_protocol_locator != EXPECTED_V1_COHORT_PROTOCOL_LOCATOR
        or cohort_protocol_sha256 != EXPECTED_V1_COHORT_PROTOCOL_SHA256
        or EXPECTED_V1_PROFILE_ARTIFACT_REVISION is None
        or revision != EXPECTED_V1_PROFILE_ARTIFACT_REVISION
        or not _cohort_activation_valid(binding.get("cohortActivation"))
    ):
        _error(errors, "frozen normative profile binding is not the code-owned v1 candidate")
        return False
    candidate = _inside_root(root, locator, errors, "normative profile")
    if candidate is None:
        return False
    raw = _read_bounded_bytes(candidate, f"normative profile {locator}", errors)
    if raw is None:
        return False
    if (
        hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        != expected_sha256
        or not _committed_blob(root, revision, locator, expected_sha256)
    ):
        _error(errors, "frozen normative profile identity or source revision mismatch")
    protocol_candidate = _inside_root(
        root, cohort_protocol_locator, errors, "cohort protocol"
    )
    if protocol_candidate is None:
        return False
    protocol_raw = _read_bounded_bytes(
        protocol_candidate,
        f"cohort protocol {cohort_protocol_locator}",
        errors,
    )
    if protocol_raw is None:
        return False
    if (
        hashlib.sha256(protocol_raw.replace(b"\r\n", b"\n")).hexdigest()
        != cohort_protocol_sha256
        or not _committed_blob(
            root,
            revision,
            cohort_protocol_locator,
            cohort_protocol_sha256,
        )
    ):
        _error(errors, "frozen cohort protocol identity or source revision mismatch")
        return len(errors) == before
    protocol = _parse_json_object_bytes(
        protocol_raw,
        f"cohort protocol {cohort_protocol_locator}",
        errors,
    )
    protocol_valid = (
        set(protocol) == COHORT_PROTOCOL_FIELDS
        and type(protocol.get("schema")) is int
        and protocol.get("schema") == 1
        and _nonempty_text(protocol.get("id"))
        and protocol.get("profileIdentity") == profile_identity
        and protocol.get("cohortProtocolIdentity") == cohort_protocol_identity
        and all(
            protocol.get(field) == expected
            for field, expected in EXPECTED_COHORT_PROTOCOL_RULES.items()
        )
        and protocol.get("strata") == list(EXPECTED_COHORT_SCENARIO_CLASSES)
        and _string_list(protocol.get("claimLimits")) is not None
    )
    if not protocol_valid:
        _error(errors, "frozen cohort protocol shape is invalid")
    current_activation = binding.get("cohortActivation")
    is_successor_generation = (
        isinstance(current_activation, dict)
        and current_activation.get("keyFingerprint")
        != EXPECTED_INITIAL_AUTHORIZATION_KEY_FINGERPRINT
    )
    program_state = program.get("status")
    if (
        binding_state == "revoked"
        and is_successor_generation
        and program_state != "stopped"
    ):
        _error(errors, "revoked successor cohort requires a stopped program")
    if program_state == "stopped" and not (
        binding_state == "revoked" and is_successor_generation
    ):
        _error(errors, "stopped program requires a revoked successor cohort")
    if binding_state == "revoked" or is_successor_generation:
        _initial_authorization_private_resource_absent(errors)
    if binding_state == "revoked" and is_successor_generation:
        _successor_authorization_private_resource_absent(errors)
    return len(errors) == before


def _terminal_release_binding_valid(
    root: Path, program: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    binding = program.get("terminalReleaseBinding")
    if not isinstance(binding, dict) or set(binding) != TERMINAL_RELEASE_BINDING_FIELDS:
        _error(errors, "program terminalReleaseBinding fields must match the code-owned schema")
        return False
    if binding.get("state") == "unregistered":
        if not _same_typed_value(binding, UNREGISTERED_TERMINAL_RELEASE_BINDING):
            _error(errors, "unregistered terminal release binding must contain only null identities")
        return len(errors) == before
    tag = binding.get("tag")
    expected_prefix = f"{program.get('release')}."
    authorization_validator = binding.get("authorizationValidator")
    authorization_source_policy = binding.get("authorizationSourcePolicy")
    if (
        binding.get("state") != "candidate"
        or program.get("status") != "completed"
        or not isinstance(tag, str)
        or re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) is None
        or not tag.startswith(expected_prefix)
        or binding.get("publicRemote") != EXPECTED_PUBLIC_REMOTE
        or binding.get("annotationFormat")
        != TERMINAL_RELEASE_ANNOTATION_FORMAT
        or not isinstance(binding.get("o5EvidenceSetSha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", binding["o5EvidenceSetSha256"])
        is None
        or not isinstance(authorization_validator, dict)
        or set(authorization_validator)
        != TERMINAL_AUTHORIZATION_VALIDATOR_BINDING_FIELDS
        or not isinstance(authorization_source_policy, dict)
        or set(authorization_source_policy)
        != TERMINAL_AUTHORIZATION_SOURCE_POLICY_FIELDS
    ):
        _error(errors, "terminal release candidate binding shape is invalid")
        return len(errors) == before
    validator_kind = authorization_validator.get("kind")
    validator_version = authorization_validator.get("version")
    validator_locator = _relative_locator(authorization_validator.get("locator"))
    validator_revision = authorization_validator.get("revision")
    validator_sha256 = authorization_validator.get("sha256")
    validator_path = (
        PurePosixPath(validator_locator) if validator_locator is not None else None
    )
    validator_spec = (
        SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS.get(validator_kind)
        if isinstance(validator_kind, str)
        else None
    )
    current_revision_raw = _evidence_git(root, "rev-parse", "--verify", "HEAD")
    try:
        current_revision = (
            current_revision_raw.decode("ascii").strip()
            if current_revision_raw is not None
            else ""
        )
    except UnicodeError:
        current_revision = ""
    validator_identity_valid = (
        isinstance(validator_kind, str)
        and SOURCE_KIND_PATTERN.fullmatch(validator_kind) is not None
        and type(validator_version) is int
        and validator_version == 1
        and validator_path is not None
        and validator_path.parent == PurePosixPath("harness")
        and validator_path.suffix == ".py"
        and validator_path.name.startswith("terminal_authorization_validator_")
        and isinstance(validator_revision, str)
        and isinstance(validator_sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", validator_sha256) is not None
        and validator_spec is not None
        and validator_locator == validator_spec[0]
        and _strict_git_ancestor(root, validator_revision, current_revision)
        and _committed_blob(
            root,
            validator_revision,
            validator_locator,
            validator_sha256,
        )
    )
    current_validator = (
        _inside_root(root, validator_locator, errors, "terminal authorization validator")
        if validator_locator is not None
        else None
    )
    current_validator_bytes = (
        _read_bounded_bytes(
            current_validator,
            f"terminal authorization validator {validator_locator}",
            errors,
        )
        if current_validator is not None
        else None
    )
    if (
        not validator_identity_valid
        or current_validator_bytes is None
        or hashlib.sha256(current_validator_bytes.replace(b"\r\n", b"\n")).hexdigest()
        != validator_sha256
    ):
        _error(errors, "terminal authorization validator identity is not prebound")
    if not (
        isinstance(authorization_source_policy.get("sourceKind"), str)
        and SOURCE_KIND_PATTERN.fullmatch(authorization_source_policy["sourceKind"])
        is not None
        and authorization_source_policy.get("publicIdentityScheme")
        == EXPECTED_TERMINAL_AUTHORIZATION_PUBLIC_IDENTITY_SCHEME
        and authorization_source_policy.get("commitmentScheme")
        == EXPECTED_TERMINAL_AUTHORIZATION_COMMITMENT_SCHEME
        and authorization_source_policy.get("privateLocatorRule")
        == EXPECTED_TERMINAL_AUTHORIZATION_PRIVATE_LOCATOR_RULE
    ):
        _error(errors, "terminal authorization source policy is invalid")
    return len(errors) == before


def _release_identity_valid(
    constitution: dict[str, Any],
    program: dict[str, Any],
    acceptance: dict[str, Any],
    errors: list[str],
) -> bool:
    before = len(errors)
    for label, document in (
        ("constitution", constitution),
        ("program", program),
        ("acceptance", acceptance),
    ):
        if set(document) != AUTHORITY_TOP_LEVEL_FIELDS[label]:
            _error(
                errors,
                f"{label} top-level fields must match the code-owned schema",
            )
    release = program.get("release")
    if not isinstance(release, str) or RELEASE.fullmatch(release) is None:
        _error(errors, "program release must use v<major>.<minor>")
        release = "invalid"
    expected_program_id = f"harness-product-program-{CURRENT_RELEASE}"
    expected_acceptance_id = f"harness-product-acceptance-{CURRENT_RELEASE}"
    checks = (
        (
            type(constitution.get("schema")) is int
            and constitution.get("schema") == 1,
            "constitution schema must be integer 1",
        ),
        (
            type(program.get("schema")) is int and program.get("schema") == 1,
            "program schema must be integer 1",
        ),
        (
            type(acceptance.get("schema")) is int
            and acceptance.get("schema") == 1,
            "acceptance schema must be integer 1",
        ),
        (constitution.get("id") == CONSTITUTION_ID, f"constitution id must be {CONSTITUTION_ID}"),
        (program.get("id") == expected_program_id, f"program id must be {expected_program_id}"),
        (acceptance.get("id") == expected_acceptance_id, f"acceptance id must be {expected_acceptance_id}"),
        (constitution.get("productId") == PRODUCT_ID, "constitution productId is invalid"),
        (program.get("productId") == PRODUCT_ID, "program productId is invalid"),
        (acceptance.get("productId") == PRODUCT_ID, "acceptance productId is invalid"),
        (release == CURRENT_RELEASE, f"program release must be {CURRENT_RELEASE}"),
        (acceptance.get("release") == release, "program and acceptance releases must match"),
        (program.get("constitution") == "product/constitution.json", "program constitution path is invalid"),
        (program.get("acceptance") == "product/acceptance.json", "program acceptance path is invalid"),
        (acceptance.get("program") == "product/program.json", "acceptance program path is invalid"),
        (program.get("completionExpression") == COMPLETION_EXPRESSION, "program completionExpression is invalid"),
        (acceptance.get("completionExpression") == COMPLETION_EXPRESSION, "acceptance completionExpression is invalid"),
        (constitution.get("purpose") == EXPECTED_PRODUCT_PURPOSE, "constitution purpose is invalid"),
        (
            constitution.get("successDefinition") == EXPECTED_SUCCESS_DEFINITION,
            "constitution successDefinition is invalid",
        ),
        (program.get("purpose") == EXPECTED_PROGRAM_PURPOSE, "program purpose is invalid"),
        (
            acceptance.get("progressRule") == EXPECTED_PROGRESS_RULE,
            "acceptance progressRule is invalid",
        ),
    )
    for valid, message in checks:
        if not valid:
            _error(errors, message)
    if not _same_typed_value(
        constitution.get("collaborationModel"), EXPECTED_COLLABORATION_MODEL
    ):
        _error(errors, "constitution collaborationModel is invalid")
    if not _same_typed_value(constitution.get("productForm"), EXPECTED_PRODUCT_FORM):
        _error(errors, "constitution productForm is invalid")
    fixed_invariants = _string_list(constitution.get("fixedInvariants"))
    if (
        fixed_invariants is None
        or set(fixed_invariants) != EXPECTED_FIXED_INVARIANTS
    ):
        _error(errors, "constitution fixedInvariants are invalid")
    adaptive_surfaces = _string_list(constitution.get("adaptiveSurfaces"))
    if (
        adaptive_surfaces is None
        or set(adaptive_surfaces) != EXPECTED_ADAPTIVE_SURFACES
    ):
        _error(errors, "constitution adaptiveSurfaces are invalid")
    bootstrap_guards = _string_list(constitution.get("bootstrapGuards"))
    if (
        bootstrap_guards is None
        or set(bootstrap_guards) != EXPECTED_BOOTSTRAP_GUARDS
    ):
        _error(errors, "constitution bootstrapGuards are invalid")
    if not _same_typed_value(
        constitution.get("planningModel"), EXPECTED_PLANNING_MODEL
    ):
        _error(errors, "constitution planningModel is invalid")
    if (
        _criteria_contract_digest(acceptance.get("criteria"))
        != EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256
    ):
        _error(errors, "acceptance criteria contract identity is invalid")
    if not _same_typed_value(
        acceptance.get("environmentAttribution"), EXPECTED_ENVIRONMENT_ATTRIBUTION
    ):
        _error(errors, "acceptance environmentAttribution is invalid")
    return len(errors) == before


def _capability_influence_valid(
    constitution: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    if not _same_typed_value(
        constitution.get("capabilityInfluenceBoundary"),
        EXPECTED_CAPABILITY_INFLUENCE_BOUNDARY,
    ):
        _error(errors, "constitution capabilityInfluenceBoundary is invalid")
    return len(errors) == before


def _criteria(
    acceptance: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    raw = acceptance.get("criteria")
    if not isinstance(raw, list):
        _error(errors, "acceptance criteria must be a list")
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            _error(errors, f"acceptance criterion {index} must be an object")
            continue
        criterion_id = item.get("id")
        if not isinstance(criterion_id, str) or not criterion_id:
            _error(errors, f"acceptance criterion {index} must have a string id")
            continue
        if criterion_id in by_id:
            _error(errors, f"duplicate acceptance criterion {criterion_id}")
            continue
        by_id[criterion_id] = item
    if set(by_id) != EXPECTED_CRITERION_IDS:
        _error(errors, "acceptance criteria must contain exactly O1-O5 and G1-G4")
    for criterion_id, item in by_id.items():
        expected_class = "outcome" if criterion_id in OUTCOME_IDS else "guardrail"
        if item.get("class") != expected_class:
            _error(errors, f"criterion {criterion_id} must be classed as {expected_class}")
        for field in ("name", "statement", "metric", "threshold"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                _error(errors, f"criterion {criterion_id} is missing {field}")
        assessment = item.get("assessment")
        if not isinstance(assessment, str) or assessment not in ASSESSMENTS:
            _error(errors, f"criterion {criterion_id} has invalid assessment")
        if criterion_id in EXPECTED_CRITERION_IDS:
            expected_fields = set(CRITERION_BASE_FIELDS)
            if criterion_id in OUTCOME_IDS:
                expected_fields.add("operationalization")
                if assessment == "verified":
                    expected_fields.add("evidence")
            if set(item) != expected_fields:
                _error(
                    errors,
                    f"criterion {criterion_id} fields must match the code-owned schema",
                )
        if criterion_id in GUARDRAIL_IDS and assessment != "computed":
            _error(errors, f"criterion {criterion_id} must be computed")
        if criterion_id in OUTCOME_IDS and assessment == "computed":
            _error(errors, f"criterion {criterion_id} must be planned or verified")
        operationalization = item.get("operationalization")
        if criterion_id in OUTCOME_IDS:
            if (
                not isinstance(operationalization, dict)
                or set(operationalization) != OUTCOME_OPERATIONALIZATION_FIELDS
            ):
                _error(
                    errors,
                    f"criterion {criterion_id} requires the exact operationalization fields",
                )
            else:
                sample_floor, comparison_design = OUTCOME_OPERATIONALIZATION_BASELINES[
                    criterion_id
                ]
                sample_count = operationalization.get("minimumSampleCount")
                if (
                    type(sample_count) is not int
                    or sample_count < sample_floor
                ):
                    _error(
                        errors,
                        f"criterion {criterion_id} minimumSampleCount must be at least {sample_floor}",
                    )
                if operationalization.get("comparisonDesign") != comparison_design:
                    _error(
                        errors,
                        f"criterion {criterion_id} comparisonDesign is invalid",
                    )
                for field in ("sampleUnit", "passRule", "humanAuthority"):
                    if not _nonempty_text(operationalization.get(field)):
                        _error(
                            errors,
                            f"criterion {criterion_id} operationalization {field} is invalid",
                        )
                for field in (
                    "preRegistrationFields",
                    "requiredMeasures",
                    "falsifiers",
                ):
                    if _string_list(operationalization.get(field)) is None:
                        _error(
                            errors,
                            f"criterion {criterion_id} operationalization {field} is invalid",
                        )
        elif "operationalization" in item:
            _error(errors, f"guardrail {criterion_id} cannot declare operationalization")
        if assessment == "verified" and _string_list(item.get("evidence")) is None:
            _error(errors, f"verified criterion {criterion_id} requires evidence")
        if assessment != "verified" and "evidence" in item:
            _error(errors, f"non-verified criterion {criterion_id} cannot bind evidence")
    return by_id


def _objects(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _error(errors, f"{label} must be a list")
        return []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            _error(errors, f"{label} item {index} must be an object")
            continue
        result.append(item)
    return result


def _program_graph(
    program: dict[str, Any],
    criteria: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    increments = _objects(program.get("increments"), "program increments", errors)
    program_state = program.get("status")
    if not isinstance(program_state, str) or program_state not in PROGRAM_STATES:
        _error(errors, "program status must be active, ready, stopped, or completed")
    if not increments and program_state not in {"ready", "stopped"}:
        _error(
            errors,
            "only a ready or stopped program may have an empty current increment graph",
        )
    active_increment_id = program.get("activeIncrementId")
    active_increments: list[dict[str, Any]] = []
    all_work: list[dict[str, Any]] = []
    increment_ids: set[str] = set()
    work_ids: set[str] = set()
    for increment in increments:
        increment_id = increment.get("id")
        if set(increment) != INCREMENT_FIELDS:
            _error(
                errors,
                f"increment {increment_id} fields must match the code-owned schema",
            )
        if not isinstance(increment_id, str) or not increment_id:
            _error(errors, "every increment requires a string id")
            continue
        if increment_id in increment_ids:
            _error(errors, f"duplicate increment id {increment_id}")
        increment_ids.add(increment_id)
        increment_state = increment.get("state")
        if not isinstance(increment_state, str) or increment_state not in INCREMENT_STATES:
            _error(errors, f"increment {increment_id} has invalid state")
        if increment_state == "planned":
            _error(errors, f"current program cannot queue planned increment {increment_id}")
        if increment_state == "active":
            active_increments.append(increment)
        correction_class = increment.get("correctionClass")
        if not isinstance(correction_class, str) or not correction_class.strip():
            _error(errors, f"increment {increment_id} requires a correctionClass")
        for field in ("observedProblem", "hypothesis", "falsifier", "stopCondition"):
            if not isinstance(increment.get(field), str) or not increment[field].strip():
                _error(errors, f"increment {increment_id} is missing {field}")
        mapped = _string_list(increment.get("acceptanceIds"))
        if mapped is None or not set(mapped) <= set(criteria):
            _error(errors, f"increment {increment_id} has invalid acceptanceIds")
        work_items = _objects(increment.get("workItems"), f"increment {increment_id} workItems", errors)
        if not work_items:
            _error(errors, f"increment {increment_id} must contain at least one work item")
        active_work_count = 0
        for work in work_items:
            work_id = work.get("id")
            if set(work) != WORK_ITEM_FIELDS:
                _error(
                    errors,
                    f"work item {work_id} fields must match the code-owned schema",
                )
            if not isinstance(work_id, str) or not work_id:
                _error(errors, f"increment {increment_id} has work without a string id")
                continue
            if work_id in work_ids:
                _error(errors, f"duplicate work item id {work_id}")
            work_ids.add(work_id)
            work_state = work.get("state")
            if not isinstance(work_state, str) or work_state not in WORK_STATES:
                _error(errors, f"work item {work_id} has invalid state")
            if work_state == "planned":
                _error(errors, f"current increment cannot queue planned work item {work_id}")
            if work_state == "active":
                active_work_count += 1
                if increment.get("state") != "active":
                    _error(errors, f"active work item {work_id} must belong to the active increment")
            work_mapped = _string_list(work.get("acceptanceIds"))
            if work_mapped is None or not set(work_mapped) <= set(criteria):
                _error(errors, f"work item {work_id} has invalid acceptanceIds")
            elif mapped is not None and not set(work_mapped) <= set(mapped):
                _error(
                    errors,
                    f"work item {work_id} acceptanceIds exceed increment {increment_id}",
                )
            if _string_list(work.get("operationIds")) is None:
                _error(errors, f"work item {work_id} requires non-empty operationIds")
            if _string_list(work.get("deliverables")) is None:
                _error(errors, f"work item {work_id} requires non-empty deliverables")
            all_work.append(work)
        if active_work_count > 1:
            _error(errors, f"increment {increment_id} has more than one active work item")
        if increment_state == "active" and active_work_count != 1:
            _error(errors, f"active increment {increment_id} must have exactly one active work item")
        if increment_state in TERMINAL_STATES and any(
            not isinstance(work.get("state"), str)
            or work.get("state") not in TERMINAL_STATES
            for work in work_items
        ):
            _error(errors, f"terminal increment {increment_id} has non-terminal work")

    if program_state == "active":
        if len(active_increments) != 1:
            _error(errors, "active program must have exactly one active increment")
        elif active_increment_id != active_increments[0].get("id"):
            _error(errors, "activeIncrementId must identify the active increment")
    elif active_increment_id is not None or active_increments:
        _error(errors, f"{program_state} program must have no active increment")
    if program_state in {"ready", "stopped", "completed"} and any(
        not isinstance(increment.get("state"), str)
        or increment.get("state") not in TERMINAL_STATES
        for increment in increments
    ):
        _error(errors, f"{program_state} program must have a terminal increment graph")
    active = active_increments[0] if len(active_increments) == 1 else None
    return increments, all_work, active


def _progression_policy_valid(program: dict[str, Any], errors: list[str]) -> bool:
    before = len(errors)
    if not _same_typed_value(
        program.get("progressionPolicy"), EXPECTED_PROGRESSION_POLICY
    ):
        _error(errors, "program progressionPolicy is invalid")
    return len(errors) == before


def _authority_guardrail(
    program: dict[str, Any], all_work: list[dict[str, Any]], errors: list[str]
) -> bool:
    before = len(errors)
    boundary = program.get("authorityBoundary")
    if not isinstance(boundary, dict):
        _error(errors, "program authorityBoundary must be an object")
        return False
    if set(boundary) != AUTHORITY_BOUNDARY_FIELDS:
        _error(
            errors,
            "program authorityBoundary fields must match the code-owned schema",
        )
    user = _string_list(boundary.get("userOwns"))
    agent = _string_list(boundary.get("agentOwnsWithinBoundedAuthority"))
    if user is None or not REQUIRED_USER_AUTHORITY <= set(user):
        _error(errors, "program userOwns omits a mandatory human authority")
    elif set(user) != REQUIRED_USER_AUTHORITY:
        _error(errors, "program userOwns contains an undeclared human authority")
    if agent is None:
        _error(errors, "program agent authority must be a non-empty string list")
        agent = []
    elif set(agent) != set(OPERATION_EFFECTS):
        _error(errors, "program agent authority must equal the code-owned operation set")
    unknown_agent_operations = set(agent) - set(OPERATION_EFFECTS)
    if unknown_agent_operations:
        _error(errors, "program agent authority contains an unknown operation")
    if set(agent) & (REQUIRED_USER_AUTHORITY | HUMAN_ONLY_OPERATIONS):
        _error(errors, "agent authority overlaps a human-only authority")
    for work in all_work:
        work_state = work.get("state")
        if not isinstance(work_state, str) or work_state not in {
            "active",
            "completed",
            "stopped",
        }:
            continue
        operations = _string_list(work.get("operationIds")) or []
        if set(operations) - set(OPERATION_EFFECTS):
            _error(errors, f"work item {work.get('id')} contains an unknown operation")
        if not set(operations) <= set(agent):
            _error(errors, f"work item {work.get('id')} exceeds agent authority")
    return len(errors) == before


def _registration_cohort_values_valid(
    values: Mapping[str, Any], activation: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    enrollment = values.get("enrollmentSurfaceAndCursor")
    private_binding = values.get("naturalDemandEventAndPrivateBinding")
    if (
        not isinstance(enrollment, dict)
        or set(enrollment) != ENROLLMENT_SURFACE_AND_CURSOR_FIELDS
        or not isinstance(private_binding, dict)
        or set(private_binding) != NATURAL_DEMAND_PRIVATE_BINDING_FIELDS
    ):
        return None
    transition = enrollment.get("surfaceTransition")
    if not isinstance(transition, dict) or set(transition) != SURFACE_TRANSITION_FIELDS:
        return None
    surface_identity = enrollment.get("surfaceIdentity")
    key_identity = enrollment.get("cohortKeyIdentity")
    key_fingerprint = enrollment.get("cohortKeyFingerprint")
    cursor_start = enrollment.get("cursorWindowStartCommitment")
    natural_cursor = enrollment.get("naturalDemandCursorCommitment")
    prior_task = enrollment.get("previousRegistrationTaskIdentity")
    common_valid = (
        isinstance(surface_identity, str)
        and PUBLIC_SURFACE_IDENTITY_PATTERN.fullmatch(surface_identity) is not None
        and isinstance(key_identity, str)
        and PUBLIC_COHORT_KEY_IDENTITY_PATTERN.fullmatch(key_identity) is not None
        and key_identity == activation.get("keyIdentity")
        and isinstance(key_fingerprint, str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", key_fingerprint) is not None
        and key_fingerprint == activation.get("keyFingerprint")
        and enrollment.get("sourceMessageRule")
        == activation.get("sourceMessageRule")
        and enrollment.get("hmacDomain") == activation.get("hmacDomain")
        and isinstance(cursor_start, str)
        and re.fullmatch(r"hmac-sha256:[0-9a-f]{64}", cursor_start) is not None
        and isinstance(natural_cursor, str)
        and re.fullmatch(r"hmac-sha256:[0-9a-f]{64}", natural_cursor) is not None
        and natural_cursor != cursor_start
        and isinstance(prior_task, str)
        and (
            prior_task == "cohort-activation"
            or CANONICAL_TASK_IDENTITY_PATTERN.fullmatch(prior_task) is not None
        )
        and private_binding.get("bindingScheme") == EXPECTED_PRIVATE_BINDING_SCHEME
        and isinstance(private_binding.get("sourceKind"), str)
        and SOURCE_KIND_PATTERN.fullmatch(private_binding["sourceKind"]) is not None
        and isinstance(private_binding.get("sourceCommitment"), str)
        and re.fullmatch(
            r"hmac-sha256:[0-9a-f]{64}", private_binding["sourceCommitment"]
        )
        is not None
        and private_binding.get("sourceMessageRule")
        == activation.get("sourceMessageRule")
        and private_binding.get("cohortKeyIdentity") == key_identity
        and private_binding.get("cohortKeyFingerprint") == key_fingerprint
    )
    state = transition.get("state")
    if not common_valid or state not in {"cohort-activation", "none", "serial"}:
        return None
    if state == "cohort-activation":
        transition_valid = (
            surface_identity == activation.get("surfaceIdentity")
            and cursor_start == activation.get("activationCursorCommitment")
            and prior_task == "cohort-activation"
            and transition.get("sourceSurfaceIdentity") == "none"
            and transition.get("sourceWindowStartCommitment")
            == activation.get("activationCursorCommitment")
            and transition.get("sourceFinalCursorCommitment")
            == activation.get("activationCursorCommitment")
            and transition.get("cause")
            == "source-authorized-first-freeze-activation"
        )
    elif state == "none":
        transition_valid = (
            transition.get("sourceSurfaceIdentity") == surface_identity
            and transition.get("sourceWindowStartCommitment") == cursor_start
            and transition.get("sourceFinalCursorCommitment") == cursor_start
            and transition.get("cause") == "none"
        )
    else:
        source_surface = transition.get("sourceSurfaceIdentity")
        transition_valid = (
            isinstance(source_surface, str)
            and PUBLIC_SURFACE_IDENTITY_PATTERN.fullmatch(source_surface) is not None
            and source_surface != surface_identity
            and isinstance(transition.get("sourceWindowStartCommitment"), str)
            and re.fullmatch(
                r"hmac-sha256:[0-9a-f]{64}",
                transition["sourceWindowStartCommitment"],
            )
            is not None
            and isinstance(transition.get("sourceFinalCursorCommitment"), str)
            and re.fullmatch(
                r"hmac-sha256:[0-9a-f]{64}",
                transition["sourceFinalCursorCommitment"],
            )
            is not None
            and transition.get("cause") in ALLOWED_SURFACE_TRANSITION_CAUSES
        )
    return (dict(enrollment), dict(private_binding)) if transition_valid else None


def _environment_attribution_binding_valid(
    root: Path,
    value: Any,
    source_revision: str,
    registered_at: datetime | None,
) -> bool:
    if not isinstance(value, dict) or set(value) != ENVIRONMENT_ATTRIBUTION_BINDING_FIELDS:
        return False
    environment_class = value.get("environmentClass")
    treatment_arm = value.get("treatmentArm")
    locator = _relative_locator(value.get("manifestLocator"), allow_evidence=True)
    revision = value.get("manifestRevision")
    expected_sha256 = value.get("manifestSha256")
    activation_delta = value.get("harnessActivationDelta")
    if (
        value.get("contractSha256") != EXPECTED_ENVIRONMENT_ATTRIBUTION_SHA256
        or environment_class
        not in EXPECTED_ENVIRONMENT_ATTRIBUTION["environmentClasses"]
        or treatment_arm not in EXPECTED_ENVIRONMENT_ATTRIBUTION["treatmentArms"]
        or locator is None
        or re.fullmatch(
            r"product/evidence/environment-manifests/[a-z0-9][a-z0-9._-]{0,127}\.json",
            locator,
        )
        is None
        or not isinstance(revision, str)
        or not isinstance(source_revision, str)
        or not _strict_git_ancestor(root, revision, source_revision)
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        or not _committed_blob(root, revision, locator, expected_sha256)
        or not isinstance(activation_delta, dict)
        or set(activation_delta) != HARNESS_ACTIVATION_DELTA_FIELDS
    ):
        return False
    if treatment_arm == "without-harness":
        activation_valid = activation_delta == {
            "state": "absent",
            "packageIdentity": "none",
            "packageSha256": "none",
            "activationIdentity": "none",
            "activationSha256": "none",
            "taskExposureIdentity": "none",
            "taskExposureSha256": "none",
        }
    else:
        activation_valid = (
            activation_delta.get("state") == "active"
            and all(
                _nonempty_text(activation_delta.get(field))
                for field in (
                    "packageIdentity",
                    "activationIdentity",
                    "taskExposureIdentity",
                )
            )
            and all(
                isinstance(activation_delta.get(field), str)
                and re.fullmatch(r"[0-9a-f]{64}", activation_delta[field])
                is not None
                for field in (
                    "packageSha256",
                    "activationSha256",
                    "taskExposureSha256",
                )
            )
        )
    if not activation_valid:
        return False
    raw = _evidence_git(root, "show", f"{revision}:{locator}")
    if raw is None:
        return False
    manifest_errors: list[str] = []
    manifest = _parse_json_object_bytes(
        raw,
        f"environment manifest {locator} at {revision}",
        manifest_errors,
    )
    if manifest_errors:
        return False
    expected_manifest_fields = {
        "schema",
        "environmentClass",
        "treatmentArm",
        "capturedAt",
        *EXPECTED_ENVIRONMENT_ATTRIBUTION["manifestFields"],
    }
    captured_at = (
        _rfc3339_instant(manifest.get("capturedAt"))
        if isinstance(manifest, dict)
        else None
    )
    return (
        isinstance(manifest, dict)
        and set(manifest) == expected_manifest_fields
        and type(manifest.get("schema")) is int
        and manifest.get("schema") == 1
        and manifest.get("environmentClass") == environment_class
        and manifest.get("treatmentArm") == treatment_arm
        and captured_at is not None
        and registered_at is not None
        and captured_at <= registered_at
        and all(
            _substantive_registration_value(manifest.get(field))
            for field in EXPECTED_ENVIRONMENT_ATTRIBUTION["manifestFields"]
        )
        and _same_typed_value(
            manifest.get("exact-harness-package-activation-and-task-exposure-delta"),
            activation_delta,
        )
    )


def _pre_measurement_validator_binding_valid(
    root: Path,
    increment: dict[str, Any],
    registration: dict[str, Any],
    source_revision: str,
    mapped_outcomes: list[str],
    value: Any,
    errors: list[str],
) -> str | None:
    before = len(errors)
    increment_id = increment.get("id")
    if not isinstance(value, dict) or set(value) != PRE_MEASUREMENT_VALIDATOR_BINDING_FIELDS:
        _error(
            errors,
            f"increment {increment_id} requires an exact preMeasurementValidator binding",
        )
        return None
    kind = value.get("kind")
    version = value.get("version")
    locator = _relative_locator(value.get("locator"))
    revision = value.get("revision")
    expected_sha256 = value.get("sha256")
    validator_path = PurePosixPath(locator) if locator is not None else None
    if (
        not isinstance(kind, str)
        or SOURCE_KIND_PATTERN.fullmatch(kind) is None
        or type(version) is not int
        or version != 1
        or validator_path is None
        or validator_path.parent != PurePosixPath("harness")
        or validator_path.suffix != ".py"
        or not validator_path.name.startswith("task_validator_")
        or not isinstance(revision, str)
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
    ):
        _error(
            errors,
            f"increment {increment_id} preMeasurementValidator identity is invalid",
        )
        return None
    spec = SUPPORTED_PRE_MEASUREMENT_VALIDATORS.get(kind)
    if spec is None:
        _error(
            errors,
            f"increment {increment_id} has no code-owned pre-measurement validator: {kind}",
        )
        return None
    supported_criteria, supported_increments, expected_locator, validator = spec
    if locator != expected_locator:
        _error(
            errors,
            f"increment {increment_id} pre-measurement validator locator is not code-owned: {kind}",
        )
    if not set(mapped_outcomes) <= supported_criteria:
        _error(
            errors,
            f"increment {increment_id} outcomes are not supported by pre-measurement validator: {kind}",
        )
    if increment_id not in supported_increments:
        _error(
            errors,
            f"pre-measurement validator is not bound to increment {increment_id}: {kind}",
        )
    if not _strict_git_ancestor(root, revision, source_revision):
        _error(
            errors,
            f"increment {increment_id} pre-measurement validator must be committed before task registration",
        )
    candidate = _inside_root(root, locator, errors, "pre-measurement validator")
    current = (
        _read_bounded_bytes(
            candidate,
            f"pre-measurement validator {locator}",
            errors,
        )
        if candidate is not None
        else None
    )
    if (
        current is None
        or hashlib.sha256(current.replace(b"\r\n", b"\n")).hexdigest()
        != expected_sha256
        or not _committed_blob(root, revision, locator, expected_sha256)
    ):
        _error(
            errors,
            f"increment {increment_id} pre-measurement validator code identity has drifted",
        )
    if len(errors) != before:
        return None
    validator_errors: list[str] = []
    try:
        result = validator(
            json.loads(json.dumps(registration)),
            json.loads(json.dumps(increment)),
            tuple(mapped_outcomes),
            root,
            validator_errors,
        )
    except Exception as exc:  # fail closed at the registration seam
        _error(
            validator_errors,
            f"increment {increment_id} pre-measurement validator failed closed: {exc.__class__.__name__}",
        )
        result = False
    if result is not True:
        _error(
            validator_errors,
            f"increment {increment_id} pre-measurement validator did not return true: {kind}",
        )
    errors.extend(validator_errors)
    return (kind, locator) if result is True and not validator_errors else None


def _task_registration_guardrail(
    root: Path,
    increment: dict[str, Any],
    criteria: Mapping[str, dict[str, Any]],
    profile_binding: Mapping[str, Any],
    errors: list[str],
) -> tuple[
    datetime,
    str,
    str,
    str,
    dict[str, Any],
    dict[str, Any],
    tuple[str, str],
] | None:
    before = len(errors)
    increment_id = increment.get("id")
    mapped = _string_list(increment.get("acceptanceIds")) or []
    mapped_outcomes = sorted(set(mapped) & OUTCOME_IDS)
    binding = increment.get("taskRegistration")
    if not mapped_outcomes:
        if binding is not None:
            _error(
                errors,
                f"outcome-neutral increment {increment_id} must bind null taskRegistration",
            )
        return None
    if profile_binding.get("state") != "frozen":
        _error(
            errors,
            f"outcome-bearing increment {increment_id} requires a frozen normative profile",
        )
        return None
    if not isinstance(binding, dict) or set(binding) != TASK_REGISTRATION_BINDING_FIELDS:
        _error(
            errors,
            f"outcome-bearing increment {increment_id} requires an exact taskRegistration binding",
        )
        return None
    locator = _relative_locator(binding.get("locator"), allow_evidence=True)
    registration_path = PurePosixPath(locator) if locator is not None else None
    if (
        registration_path is None
        or registration_path.parent != PurePosixPath("product/evidence")
        or not registration_path.name.endswith("-registration.json")
    ):
        _error(errors, f"increment {increment_id} has invalid taskRegistration locator")
        return None
    candidate = _inside_root(root, locator, errors, "task registration")
    if candidate is None:
        return None
    registration_label = f"task registration {locator}"
    raw = _read_bounded_bytes(candidate, registration_label, errors)
    if raw is None:
        return None
    expected_sha256 = binding.get("sha256")
    if (
        not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
    ):
        _error(errors, f"increment {increment_id} taskRegistration identity mismatch")
        return None
    source_revision = binding.get("sourceRevision")
    measurement_not_before = _rfc3339_instant(binding.get("measurementNotBefore"))
    profile_sha256 = binding.get("profileSha256")
    cohort_protocol_sha256 = binding.get("cohortProtocolSha256")
    frozen_at_revision = profile_binding.get("frozenAtRevision")
    if (
        not isinstance(source_revision, str)
        or hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        != expected_sha256
        or not _committed_blob(root, source_revision, locator, expected_sha256)
        or measurement_not_before is None
        or profile_sha256 != profile_binding.get("sha256")
        or cohort_protocol_sha256
        != profile_binding.get("cohortProtocolSha256")
    ):
        _error(
            errors,
            f"increment {increment_id} taskRegistration identity or frozen-profile binding mismatch",
        )
        return None
    if not _strict_git_ancestor(root, frozen_at_revision, source_revision):
        _error(
            errors,
            f"increment {increment_id} taskRegistration must strictly descend from the frozen profile and cohort protocol",
        )
        return None
    if not _registration_parent_has_profile_binding(
        root, source_revision, profile_binding, errors
    ):
        _error(
            errors,
            f"increment {increment_id} taskRegistration must have one parent containing the exact frozen normative profile binding",
        )
        return None
    if not _registration_added_at_revision(root, source_revision, locator):
        _error(
            errors,
            f"increment {increment_id} taskRegistration identity or frozen-profile binding mismatch",
        )
        return None
    registration = _parse_json_object_bytes(raw, registration_label, errors)
    if set(registration) != TASK_REGISTRATION_FIELDS:
        _error(errors, f"task registration {locator} fields must match the code-owned schema")
        return None
    criterion_ids = _string_list(registration.get("criterionIds"))
    source_capture = registration.get("sourceCaptureEligibilityAndStopRule")
    acceptance_authority = registration.get("acceptanceAuthority")
    floors = registration.get("qualitySafetyEvidenceAndResidueFloors")
    values = registration.get("preRegistrationValues")
    registered_at = _rfc3339_instant(registration.get("registeredAt"))
    expected_fields: set[str] = set()
    for criterion_id in mapped_outcomes:
        operationalization = criteria.get(criterion_id, {}).get("operationalization")
        if not isinstance(operationalization, dict):
            _error(errors, f"task registration {locator} cannot resolve {criterion_id}")
            continue
        required = _string_list(operationalization.get("preRegistrationFields"))
        if required is None:
            _error(errors, f"task registration {locator} cannot resolve {criterion_id}")
            continue
        expected_fields.update(required)
    cohort_values = (
        _registration_cohort_values_valid(
            values,
            profile_binding["cohortActivation"],
        )
        if isinstance(values, dict)
        and isinstance(profile_binding.get("cohortActivation"), dict)
        else None
    )
    environment_binding_valid = (
        _environment_attribution_binding_valid(
            root,
            values.get("environmentAttributionBinding"),
            source_revision,
            registered_at,
        )
        if isinstance(values, dict)
        and "environmentAttributionBinding" in expected_fields
        else False
    )
    if not environment_binding_valid:
        _error(
            errors,
            f"task registration {locator} environment attribution binding is invalid",
        )
    shape_valid = (
        type(registration.get("schema")) is int
        and registration.get("schema") == 1
        and _nonempty_text(registration.get("id"))
        and registered_at is not None
        and registered_at <= measurement_not_before
        and isinstance(registration.get("taskIdentity"), str)
        and CANONICAL_TASK_IDENTITY_PATTERN.fullmatch(registration["taskIdentity"])
        is not None
        and registration.get("incrementId") == increment_id
        and criterion_ids == mapped_outcomes
        and isinstance(values, dict)
        and set(values) == expected_fields
        and all(_substantive_registration_value(item) for item in values.values())
        and cohort_values is not None
        and environment_binding_valid
        and values.get("normativeProfileIdentity")
        == profile_binding.get("profileIdentity")
        and values.get("cohortProtocolIdentity")
        == profile_binding.get("cohortProtocolIdentity")
        and values.get("profileSha256") == profile_binding.get("sha256")
        and values.get("cohortProtocolSha256")
        == profile_binding.get("cohortProtocolSha256")
        and (
            "scenarioClass" not in expected_fields
            or values.get("scenarioClass") in EXPECTED_COHORT_SCENARIO_CLASSES
        )
        and all(
            _same_typed_value(values[field], registration[field])
            for field in TASK_REGISTRATION_VALUE_ALIASES & expected_fields
        )
        and _nonempty_text(registration.get("namedHumanAcceptor"))
        and isinstance(acceptance_authority, dict)
        and set(acceptance_authority) == ACCEPTANCE_AUTHORITY_FIELDS
        and acceptance_authority.get("locator") == "product/acceptance.json"
        and acceptance_authority.get("criteriaContractSha256")
        == EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256
        and isinstance(floors, dict)
        and bool(floors)
        and all(
            isinstance(key, str)
            and bool(key.strip())
            and _substantive_registration_value(item)
            for key, item in floors.items()
        )
        and _string_list(registration.get("materialInterventionTaxonomy")) is not None
        and _string_list(registration.get("materialCollaborationLossTaxonomy")) is not None
        and isinstance(source_capture, dict)
        and set(source_capture) == SOURCE_CAPTURE_FIELDS
        and source_capture.get("enrollmentSurfaceRule")
        == EXPECTED_CURRENT_COHORT_PROTOCOL_RULES["enrollmentSurfaceRule"]
        and source_capture.get("cursorWindowStartsAfter")
        == "surface-activation-or-prior-registration"
        and source_capture.get("naturalDemandObservedBefore")
        == "immutable-registration"
        and source_capture.get("measurementStartsAfter")
        == "immutable-registration"
        and _string_list(source_capture.get("eligibleSources")) is not None
        and _string_list(source_capture.get("ineligibleSources")) is not None
        and _nonempty_text(source_capture.get("stopRule"))
        and _string_list(registration.get("claimLimits")) is not None
        and _same_typed_value(
            registration.get("preMeasurementValidator"),
            binding.get("preMeasurementValidator"),
        )
    )
    if not shape_valid:
        _error(errors, f"task registration {locator} shape is invalid")
    validator_binding = None
    if len(errors) == before:
        validator_binding = _pre_measurement_validator_binding_valid(
            root,
            increment,
            registration,
            source_revision,
            mapped_outcomes,
            registration.get("preMeasurementValidator"),
            errors,
        )
    task_identity = registration.get("taskIdentity")
    return (
        (
            measurement_not_before,
            task_identity,
            source_revision,
            locator,
            cohort_values[0],
            cohort_values[1],
            validator_binding,
        )
        if len(errors) == before
        and isinstance(task_identity, str)
        and isinstance(source_revision, str)
        and cohort_values is not None
        and isinstance(validator_binding, tuple)
        else None
    )


def _task_registration_floors(
    root: Path,
    increments: list[dict[str, Any]],
    criteria: Mapping[str, dict[str, Any]],
    profile_binding: Mapping[str, Any],
    errors: list[str],
) -> tuple[dict[str, datetime], dict[str, tuple[str, str]]]:
    floors: dict[str, datetime] = {}
    validator_bindings: dict[str, tuple[str, str]] = {}
    task_identities: set[str] = set()
    source_commitments: set[str] = set()
    natural_demand_cursors: set[str] = set()
    bound_registration_paths: set[str] = set()
    prior_registration_revision: str | None = None
    prior_task_identity: str | None = None
    prior_enrollment: dict[str, Any] | None = None
    for increment in increments:
        increment_id = increment.get("id")
        registration = _task_registration_guardrail(
            root, increment, criteria, profile_binding, errors
        )
        if isinstance(increment_id, str) and registration is not None:
            (
                floor,
                task_identity,
                source_revision,
                locator,
                enrollment,
                private_binding,
                validator_binding,
            ) = registration
            if task_identity in task_identities:
                _error(
                    errors,
                    f"taskIdentity {task_identity} is reused across outcome registrations",
                )
            task_identities.add(task_identity)
            source_commitment = private_binding["sourceCommitment"]
            natural_cursor = enrollment["naturalDemandCursorCommitment"]
            if source_commitment in source_commitments:
                _error(errors, "private natural-demand source commitment is reused")
            source_commitments.add(source_commitment)
            if natural_cursor in natural_demand_cursors:
                _error(errors, "natural-demand cursor commitment is reused")
            natural_demand_cursors.add(natural_cursor)
            if prior_registration_revision is not None and not _strict_git_ancestor(
                root, prior_registration_revision, source_revision
            ):
                _error(
                    errors,
                    "outcome registration revisions must form one strict Git ancestry order",
                )
            transition = enrollment["surfaceTransition"]
            if prior_enrollment is None:
                if transition["state"] != "cohort-activation":
                    _error(errors, "first outcome registration must descend from cohort activation")
            else:
                prior_cursor = prior_enrollment["naturalDemandCursorCommitment"]
                if enrollment["previousRegistrationTaskIdentity"] != prior_task_identity:
                    _error(errors, "outcome registration chain skips its prior task identity")
                if transition["state"] == "none":
                    if (
                        enrollment["surfaceIdentity"]
                        != prior_enrollment["surfaceIdentity"]
                        or enrollment["cursorWindowStartCommitment"] != prior_cursor
                        or transition["sourceWindowStartCommitment"] != prior_cursor
                    ):
                        _error(errors, "outcome registration cursor chain is discontinuous")
                elif transition["state"] == "serial":
                    if (
                        transition["sourceSurfaceIdentity"]
                        != prior_enrollment["surfaceIdentity"]
                        or transition["sourceWindowStartCommitment"] != prior_cursor
                    ):
                        _error(errors, "surface transition does not continue the prior cohort cursor")
                else:
                    _error(errors, "cohort activation cannot recur after the first registration")
            prior_registration_revision = source_revision
            prior_task_identity = task_identity
            prior_enrollment = enrollment
            bound_registration_paths.add(locator)
            floors[increment_id] = floor
            validator_bindings[increment_id] = validator_binding
    if profile_binding.get("state") == "frozen":
        history_paths = _registration_history_paths(
            root, profile_binding.get("frozenAtRevision"), errors
        )
        if history_paths is not None and history_paths != bound_registration_paths:
            _error(
                errors,
                "every post-freeze cohort registration artifact must bind exactly one outcome increment",
            )
    return floors, validator_bindings


def _process_loss_guardrail(
    root: Path,
    increments: list[dict[str, Any]],
    validated_work_outcomes: Mapping[str, set[str]],
    errors: list[str],
) -> bool:
    before = len(errors)
    seen_correction_classes: set[str] = set()
    for increment in increments:
        state = increment.get("state")
        if state == "planned":
            continue
        budget = increment.get("processLossBudget")
        increment_id = increment.get("id")
        if not isinstance(budget, dict) or set(budget) != PROCESS_LOSS_FIELDS:
            _error(errors, f"increment {increment_id} requires the exact process-loss budget fields")
            continue
        integer_fields = (
            "maxSameClassUserCorrectionBeforeStop",
            "maxConsecutiveOutcomeNeutralWorkItems",
            "maxProhibitedAgentWorkTransfers",
        )
        for field in integer_fields:
            value = budget.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                _error(errors, f"process-loss budget {field} must be a non-negative integer")
        if budget.get("maxSameClassUserCorrectionBeforeStop") != 1:
            _error(errors, "same-class user correction budget must stop before recurrence")
        if budget.get("maxProhibitedAgentWorkTransfers") != 0:
            _error(errors, "prohibited Agent-work transfer budget must be zero")
        neutral_budget = budget.get("maxConsecutiveOutcomeNeutralWorkItems")
        if neutral_budget not in {0, 1}:
            _error(errors, "outcome-neutral work budget must be zero or one")
        for field in ("stopOnAuthorityOrIrreversibleIncident", "stopOnUnboundedResidue"):
            if budget.get(field) is not True:
                _error(errors, f"process-loss budget {field} must be true")

        work_items = increment.get("workItems") if isinstance(increment.get("workItems"), list) else []
        current_neutral = 0
        max_neutral = 0
        increment_has_validated_outcome = False
        for work in work_items:
            if not isinstance(work, dict):
                continue
            work_state = work.get("state")
            if not isinstance(work_state, str):
                continue
            if work_state == "planned":
                continue
            mapped = _string_list(work.get("acceptanceIds")) or []
            mapped_outcomes = set(mapped) & OUTCOME_IDS
            work_outcomes = validated_work_outcomes.get(work.get("id"), set())
            if mapped_outcomes & work_outcomes:
                increment_has_validated_outcome = True
                current_neutral = 0
            else:
                current_neutral += 1
                max_neutral = max(max_neutral, current_neutral)
        if isinstance(neutral_budget, int) and max_neutral > neutral_budget:
            _error(errors, f"increment {increment_id} exceeds its outcome-neutral work budget")
        if state in TERMINAL_STATES:
            if not increment_has_validated_outcome:
                _error(
                    errors,
                    f"closed outcome-neutral increment must leave the current graph: {increment_id}",
                )
            elif state != "completed":
                _error(
                    errors,
                    "only a completed increment may retain validated outcome "
                    f"binding: {increment_id}",
                )
        correction_class = increment.get("correctionClass")
        if (
            isinstance(correction_class, str)
            and correction_class
            and correction_class in seen_correction_classes
        ):
            _error(errors, f"increments repeat correctionClass: {correction_class}")
        if isinstance(correction_class, str) and correction_class:
            seen_correction_classes.add(correction_class)

        cleanup = increment.get("cleanupBoundary")
        if not isinstance(cleanup, dict) or set(cleanup) != CLEANUP_BOUNDARY_FIELDS:
            _error(
                errors,
                f"increment {increment_id} requires the exact cleanup boundary fields",
            )
            continue
        paths = cleanup.get("repositoryTemporaryPaths")
        if (
            not isinstance(paths, list)
            or not all(isinstance(item, str) and item.strip() for item in paths)
            or len(paths) != len(set(paths))
        ):
            _error(errors, f"increment {increment_id} requires exact repository cleanup paths")
            continue
        for raw in paths:
            relative = _cleanup_locator(raw)
            if relative is None:
                _error(errors, f"invalid repository cleanup path: {raw!r}")
                continue
            candidate = _inside_root(root, relative, errors, "cleanup path")
            if candidate is not None and not _path_entry_absent(candidate):
                _error(errors, f"repository cleanup residue remains: {relative}")
        private_dispositions = cleanup.get("privateResourceDispositions")
        if (
            not isinstance(private_dispositions, list)
            or len(private_dispositions) != len(set(private_dispositions))
            or not all(
                isinstance(item, str)
                and item in ALLOWED_PRIVATE_RESOURCE_DISPOSITIONS
                for item in private_dispositions
            )
        ):
            _error(
                errors,
                f"increment {increment_id} requires exact privacy-safe private "
                "resource dispositions",
            )
    _repository_residue_absent(root, errors)
    return len(errors) == before


def _repository_residue_absent(root: Path, errors: list[str]) -> bool:
    before = len(errors)
    scanned_entries = 0

    def conventional_directory(name: str) -> bool:
        return name.casefold() in CONVENTIONAL_RESIDUE_NAMES

    def conventional_file(name: str) -> bool:
        folded = name.casefold()
        return folded in CONVENTIONAL_RESIDUE_NAMES or folded.endswith(
            CONVENTIONAL_RESIDUE_SUFFIXES
        )

    pending: list[tuple[Path, int]] = [(root, 0)]
    while pending:
        current_path, depth = pending.pop()
        if depth > MAX_REPOSITORY_WALK_DEPTH:
            _error(errors, "repository residue scan depth limit exceeded")
            break
        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    scanned_entries += 1
                    if scanned_entries > MAX_REPOSITORY_WALK_ENTRIES:
                        _error(errors, "repository residue scan entry limit exceeded")
                        pending.clear()
                        break
                    candidate = Path(entry.path)
                    try:
                        relative = candidate.relative_to(root).as_posix()
                    except ValueError:
                        _error(errors, "repository residue scan escaped the repository root")
                        continue
                    if relative == ".git" or relative.startswith(".git/"):
                        continue
                    linked = _link_or_reparse(candidate)
                    try:
                        is_directory = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        _error(errors, "repository residue cannot be enumerated")
                        continue
                    if is_directory:
                        if conventional_directory(entry.name):
                            _error(errors, f"repository cleanup residue remains: {relative}")
                        elif not linked:
                            pending.append((candidate, depth + 1))
                        continue
                    if conventional_file(entry.name):
                        _error(errors, f"repository cleanup residue remains: {relative}")
        except OSError:
            _error(errors, "repository residue cannot be enumerated")
    return len(errors) == before


def _evidence_states(
    root: Path,
    criteria: dict[str, dict[str, Any]],
    work_bindings: Mapping[str, tuple[str, set[str], str]],
    registration_floors: Mapping[str, datetime],
    registration_validator_bindings: Mapping[str, tuple[str, str]],
    errors: list[str],
) -> tuple[dict[str, bool], bool, dict[str, set[str]]]:
    states = {criterion_id: False for criterion_id in EXPECTED_CRITERION_IDS}
    validated_work_outcomes: dict[str, set[str]] = {}
    evidence_id_locators: dict[str, str] = {}
    before = len(errors)
    evidence_locator_references = sum(
        len(_string_list(criteria.get(criterion_id, {}).get("evidence")) or [])
        for criterion_id in OUTCOME_IDS
        if criteria.get(criterion_id, {}).get("assessment") == "verified"
    )
    if evidence_locator_references > MAX_EVIDENCE_LOCATOR_REFERENCES:
        _error(errors, "evidence locator reference limit exceeded")
        return states, False, validated_work_outcomes
    for criterion_id in sorted(OUTCOME_IDS):
        criterion = criteria.get(criterion_id, {})
        if criterion.get("assessment") != "verified":
            continue
        locators = _string_list(criterion.get("evidence")) or []
        valid = bool(locators)
        criterion_work_ids: set[str] = set()
        for raw in locators:
            relative = _relative_locator(raw, allow_evidence=True)
            evidence_path = PurePosixPath(relative) if relative is not None else None
            if (
                evidence_path is None
                or evidence_path.parent != PurePosixPath("product/evidence")
                or evidence_path.suffix != ".json"
            ):
                _error(errors, f"criterion {criterion_id} has invalid evidence locator: {raw!r}")
                valid = False
                continue
            candidate = _inside_root(root, relative, errors, "evidence file")
            if candidate is None:
                valid = False
                continue
            document = _load_json(candidate, f"evidence {relative}", errors)
            validator = document.get("validator")
            validator_kind = validator.get("kind") if isinstance(validator, dict) else None
            criterion_ids = _string_list(document.get("criterionIds"))
            source = document.get("source")
            authority = document.get("authority")
            result = document.get("result")
            increment_id = document.get("incrementId")
            work_id = document.get("workItemId")
            work_binding = work_bindings.get(work_id) if _nonempty_text(work_id) else None
            evidence_id = document.get("id")
            observed_at = _rfc3339_instant(document.get("observedAt"))
            decided_at = (
                _rfc3339_instant(authority.get("decidedAt"))
                if isinstance(authority, dict)
                else None
            )
            prior_locator = (
                evidence_id_locators.get(evidence_id)
                if _nonempty_text(evidence_id)
                else None
            )
            if prior_locator is not None and prior_locator != relative:
                _error(errors, f"duplicate evidence id {evidence_id}: {relative}")
            elif _nonempty_text(evidence_id):
                evidence_id_locators[evidence_id] = relative
            shape_valid = (
                type(document.get("schema")) is int
                and document.get("schema") == 1
                and _nonempty_text(evidence_id)
                and (prior_locator is None or prior_locator == relative)
                and criterion_ids is not None
                and criterion_id in criterion_ids
                and observed_at is not None
                and _nonempty_text(increment_id)
                and increment_id in registration_floors
                and observed_at >= registration_floors[increment_id]
                and _nonempty_text(work_id)
                and work_binding is not None
                and work_binding[0] == increment_id
                and set(criterion_ids) <= OUTCOME_IDS
                and set(criterion_ids) <= work_binding[1]
                and all(
                    declared_id in criteria
                    and criteria[declared_id].get("assessment") == "verified"
                    and relative
                    in (_string_list(criteria[declared_id].get("evidence")) or [])
                    for declared_id in criterion_ids
                )
                and work_binding[2] == "completed"
                and isinstance(source, dict)
                and all(
                    _nonempty_text(source.get(field))
                    for field in ("kind", "locator", "identity")
                )
                and isinstance(authority, dict)
                and authority.get("kind") == "named-accountable-human"
                and _nonempty_text(authority.get("name"))
                and authority.get("decision") == "accepted"
                and decided_at is not None
                and decided_at >= observed_at
                and isinstance(result, dict)
                and result.get("accepted") is True
                and _string_list(document.get("claimLimits")) is not None
                and isinstance(validator_kind, str)
                and type(validator.get("version")) is int
                and validator.get("version") == 1
            )
            if not shape_valid:
                _error(errors, f"criterion {criterion_id} evidence shape is invalid: {relative}")
                valid = False
                continue
            validator_spec = SUPPORTED_EVIDENCE_VALIDATORS.get(validator_kind)
            if validator_spec is None:
                _error(errors, f"criterion {criterion_id} has no code-owned evidence validator: {validator_kind}")
                valid = False
                continue
            registered_validator_binding = registration_validator_bindings.get(increment_id)
            if (
                registered_validator_binding is None
                or validator_kind != registered_validator_binding[0]
            ):
                _error(
                    errors,
                    f"criterion {criterion_id} evidence validator does not reuse the "
                    f"pre-measurement validator bound to increment {increment_id}",
                )
                valid = False
                continue
            (
                supported_criteria,
                supported_increments,
                validator_locator,
                evidence_validator,
            ) = validator_spec
            if validator_locator != registered_validator_binding[1]:
                _error(
                    errors,
                    f"criterion {criterion_id} evidence validator code locator does not "
                    f"reuse the pre-measurement binding: {validator_kind}",
                )
                valid = False
                continue
            if criterion_id not in supported_criteria:
                _error(
                    errors,
                    f"criterion {criterion_id} is not supported by evidence validator: {validator_kind}",
                )
                valid = False
                continue
            if increment_id not in supported_increments:
                _error(
                    errors,
                    f"criterion {criterion_id} evidence validator is not bound to "
                    f"increment {increment_id}: {validator_kind}",
                )
                valid = False
                continue
            validator_errors: list[str] = []
            try:
                validator_result = evidence_validator(
                    document,
                    criterion_id,
                    root,
                    validator_errors,
                )
                if validator_result is not True:
                    _error(
                        validator_errors,
                        f"criterion {criterion_id} evidence validator did not return true: {relative}",
                    )
                    valid = False
                elif not validator_errors:
                    criterion_work_ids.add(work_id)
            except Exception as exc:  # fail closed at the public verifier seam
                _error(
                    validator_errors,
                    f"criterion {criterion_id} evidence validator failed closed: {exc.__class__.__name__}",
                )
                valid = False
            if validator_errors:
                valid = False
                errors.extend(validator_errors)
        states[criterion_id] = valid
        if valid:
            for work_id in criterion_work_ids:
                validated_work_outcomes.setdefault(work_id, set()).add(criterion_id)
    return states, len(errors) == before, validated_work_outcomes


def _criterion_evidence_set_sha256(
    root: Path,
    criterion: Mapping[str, Any],
    errors: list[str],
) -> str | None:
    locators = _string_list(criterion.get("evidence"))
    if criterion.get("assessment") != "verified" or locators is None:
        return None
    digest = hashlib.sha256()
    for locator in sorted(locators):
        relative = _relative_locator(locator, allow_evidence=True)
        path = PurePosixPath(relative) if relative is not None else None
        if (
            path is None
            or path.parent != PurePosixPath("product/evidence")
            or path.suffix != ".json"
        ):
            return None
        candidate = _inside_root(root, relative, errors, "terminal evidence")
        if candidate is None:
            return None
        raw = _read_bounded_bytes(candidate, f"terminal evidence {relative}", errors)
        if raw is None:
            return None
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw.replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _terminal_checkout_inventory_clean(root: Path, errors: list[str]) -> bool:
    tracked_raw = _evidence_git(root, "ls-files", "-z", "--cached")
    if tracked_raw is None:
        _error(errors, "terminal tracked-file inventory cannot be resolved")
        return False
    try:
        tracked = {
            item.decode("utf-8")
            for item in tracked_raw.split(b"\0")
            if item
        }
    except UnicodeError:
        _error(errors, "terminal tracked-file inventory is malformed")
        return False
    required_directories: set[str] = set()
    for relative in tracked:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            required_directories.add(parent.as_posix())
            parent = parent.parent
    observed_files: set[str] = set()
    entries_seen = 0
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        if depth > MAX_REPOSITORY_WALK_DEPTH:
            _error(errors, "terminal checkout inventory depth limit exceeded")
            return False
        try:
            with os.scandir(directory) as iterator:
                entries = list(iterator)
        except OSError:
            _error(errors, "terminal checkout inventory cannot be enumerated")
            return False
        for entry in entries:
            entries_seen += 1
            if entries_seen > MAX_REPOSITORY_WALK_ENTRIES:
                _error(errors, "terminal checkout inventory entry limit exceeded")
                return False
            candidate = Path(entry.path)
            try:
                relative = candidate.relative_to(root).as_posix()
            except ValueError:
                _error(errors, "terminal checkout inventory escaped the repository root")
                return False
            if depth == 0 and relative == ".git":
                continue
            try:
                metadata = candidate.lstat()
            except OSError:
                _error(errors, "terminal checkout inventory entry cannot be inspected")
                return False
            if stat.S_ISDIR(metadata.st_mode) and not _link_or_reparse(candidate):
                if relative not in required_directories:
                    _error(errors, f"terminal checkout contains an extra directory: {relative}")
                    return False
                stack.append((candidate, depth + 1))
                continue
            if relative not in tracked:
                _error(errors, f"terminal checkout contains an extra entry: {relative}")
                return False
            observed_files.add(relative)
    if observed_files != tracked:
        _error(errors, "terminal checkout does not materialize the exact tracked file set")
        return False
    return True


def _terminal_release_gate(
    root: Path,
    program: Mapping[str, Any],
    criteria: Mapping[str, Mapping[str, Any]],
    errors: list[str],
) -> tuple[bool, str]:
    binding = program.get("terminalReleaseBinding")
    if not isinstance(binding, dict) or binding.get("state") != "candidate":
        _error(errors, "terminal completion requires a predeclared release candidate binding")
        return False, "invalid"
    expected_evidence_sha256 = _criterion_evidence_set_sha256(
        root, criteria.get("O5", {}), errors
    )
    if expected_evidence_sha256 != binding.get("o5EvidenceSetSha256"):
        _error(errors, "terminal release candidate does not bind the exact O5 evidence set")
        return False, "invalid"
    status = _evidence_git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=matching",
    )
    if status is None:
        _error(
            errors,
            "terminal release candidate checkout status cannot be resolved",
        )
        return False, "invalid"
    if status != b"":
        _error(
            errors,
            "terminal release candidate must be a clean checkout with no ignored or untracked residue",
        )
        return False, "invalid"
    if not _terminal_checkout_inventory_clean(root, errors):
        return False, "invalid"
    head_raw = _evidence_git(root, "rev-parse", "--verify", "HEAD")
    try:
        head = head_raw.decode("ascii").strip() if head_raw is not None else ""
    except UnicodeError:
        head = ""
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head) is None:
        _error(errors, "terminal release candidate HEAD cannot be resolved")
        return False, "invalid"
    tag = binding["tag"]
    tag_ref = f"refs/tags/{tag}"
    local_tag_raw = _evidence_git(root, "rev-parse", "--verify", tag_ref)
    if local_tag_raw is None:
        return False, "candidate-clean-awaiting-authorized-tag"
    try:
        local_tag_object = local_tag_raw.decode("ascii").strip()
    except UnicodeError:
        local_tag_object = ""
    tag_type = _evidence_git(root, "cat-file", "-t", tag_ref)
    tag_commit = _evidence_git(root, "rev-parse", f"{tag_ref}^{{commit}}")
    annotation_raw = _evidence_git(
        root, "for-each-ref", "--format=%(contents)", "--count=1", tag_ref
    )
    try:
        tag_commit_text = tag_commit.decode("ascii").strip() if tag_commit is not None else ""
    except UnicodeError:
        tag_commit_text = ""
    if (
        re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", local_tag_object) is None
        or tag_type is None
        or tag_type.strip() != b"tag"
        or tag_commit_text != head
        or annotation_raw is None
    ):
        _error(errors, "local terminal tag is not one annotated tag over candidate HEAD")
        return False, "invalid"
    annotation = _parse_json_object_bytes(
        annotation_raw.strip(), f"terminal tag annotation {tag}", errors
    )
    authority = annotation.get("authority")
    authorization_source = (
        authority.get("source") if isinstance(authority, dict) else None
    )
    authorization_validator = (
        authority.get("validator") if isinstance(authority, dict) else None
    )
    bound_authorization_validator = binding.get("authorizationValidator")
    authorization_source_policy = binding.get("authorizationSourcePolicy")
    annotation_valid = (
        set(annotation) == TERMINAL_RELEASE_ANNOTATION_FIELDS
        and type(annotation.get("schema")) is int
        and annotation.get("schema") == 1
        and annotation.get("format") == TERMINAL_RELEASE_ANNOTATION_FORMAT
        and annotation.get("productId") == PRODUCT_ID
        and annotation.get("release") == program.get("release")
        and annotation.get("candidateRevision") == head
        and annotation.get("tag") == tag
        and annotation.get("publicRemote") == EXPECTED_PUBLIC_REMOTE
        and annotation.get("o5EvidenceSetSha256") == expected_evidence_sha256
        and isinstance(authority, dict)
        and set(authority) == TERMINAL_RELEASE_AUTHORITY_FIELDS
        and authority.get("kind") == "named-accountable-human"
        and _nonempty_text(authority.get("name"))
        and authority.get("decision") == "authorized"
        and _rfc3339_instant(authority.get("decidedAt")) is not None
        and isinstance(authorization_source, dict)
        and set(authorization_source)
        == TERMINAL_RELEASE_AUTHORITY_SOURCE_FIELDS
        and isinstance(authorization_source_policy, dict)
        and authorization_source.get("kind")
        == authorization_source_policy.get("sourceKind")
        and isinstance(authorization_source.get("publicIdentity"), str)
        and TERMINAL_PUBLIC_AUTHORIZATION_IDENTITY_PATTERN.fullmatch(
            authorization_source["publicIdentity"]
        )
        is not None
        and isinstance(authorization_source.get("commitment"), str)
        and re.fullmatch(
            r"hmac-sha256:[0-9a-f]{64}", authorization_source["commitment"]
        )
        is not None
        and isinstance(authorization_validator, dict)
        and set(authorization_validator)
        == TERMINAL_RELEASE_AUTHORITY_VALIDATOR_FIELDS
        and _nonempty_text(authorization_validator.get("kind"))
        and type(authorization_validator.get("version")) is int
        and authorization_validator.get("version") == 1
        and isinstance(bound_authorization_validator, dict)
        and authorization_validator.get("kind")
        == bound_authorization_validator.get("kind")
        and authorization_validator.get("version")
        == bound_authorization_validator.get("version")
        and _same_typed_value(
            annotation.get("acceptedScope"), EXPECTED_TERMINAL_RELEASE_SCOPE
        )
    )
    if not annotation_valid:
        _error(errors, "terminal tag annotation authorization is invalid")
        return False, "invalid"
    validator_kind = authorization_validator["kind"]
    authorization_spec = SUPPORTED_TERMINAL_HUMAN_AUTHORIZATION_VALIDATORS.get(
        validator_kind
    )
    if authorization_spec is None:
        _error(
            errors,
            f"terminal human authorization has no code-owned source validator: {validator_kind}",
        )
        return False, "invalid"
    _, authorization_evaluator = authorization_spec
    try:
        authorization_verified = authorization_evaluator(annotation, root, errors)
    except Exception as exc:
        _error(
            errors,
            "terminal human authorization validator failed closed: "
            f"{exc.__class__.__name__}",
        )
        return False, "invalid"
    if authorization_verified is not True:
        _error(errors, "terminal human authorization source was not independently verified")
        return False, "invalid"
    remote_raw = _evidence_git(
        root,
        "ls-remote",
        "--tags",
        EXPECTED_PUBLIC_REMOTE,
        tag_ref,
        f"{tag_ref}^{{}}",
    )
    if remote_raw is None:
        _error(errors, "public terminal tag cannot be verified")
        return False, "invalid"
    try:
        remote_entries = {
            ref: object_id
            for line in remote_raw.decode("ascii").splitlines()
            for object_id, ref in [line.split("\t", 1)]
        }
    except (UnicodeError, ValueError):
        remote_entries = {}
    if (
        remote_entries
        != {
            tag_ref: local_tag_object,
            f"{tag_ref}^{{}}": head,
        }
    ):
        _error(errors, "public terminal tag object or peeled commit does not match locally")
        return False, "invalid"
    return True, "published-verified"


def _source_carrier_release_preflight(
    program: Mapping[str, Any], authority_valid: bool
) -> dict[str, Any]:
    if not authority_valid:
        return {
            "allowed": False,
            "state": "unknown-stop-before-release",
            "reason": "authority-verification-failed",
            "scope": "live-cohort-source-dependency-only",
        }
    binding = program.get("normativeProfileBinding")
    binding_state = binding.get("state") if isinstance(binding, dict) else None
    if binding_state == "frozen":
        return {
            "allowed": False,
            "state": "retain-live-source-verification",
            "reason": "frozen-cohort-source-remains-required-for-live-verifiability",
            "scope": "live-cohort-source-dependency-only",
        }
    if binding_state in {"unfrozen", "revoked"}:
        return {
            "allowed": True,
            "state": "release-eligible",
            "reason": "no-live-frozen-cohort-source-dependency",
            "scope": "live-cohort-source-dependency-only",
        }
    return {
        "allowed": False,
        "state": "unknown-stop-before-release",
        "reason": "binding-state-is-not-release-safe",
        "scope": "live-cohort-source-dependency-only",
    }


def _verify_product(root: Path) -> dict[str, Any]:
    """Verify the current release contract and return a JSON-serializable report."""

    root = root.resolve()
    errors: list[str] = []
    constitution = _load_authority_json(
        root, "product/constitution.json", "product constitution", errors
    )
    program = _load_authority_json(root, "product/program.json", "product program", errors)
    acceptance = _load_authority_json(
        root, "product/acceptance.json", "product acceptance", errors
    )

    release_identity = _release_identity_valid(constitution, program, acceptance, errors)
    historical_boundary = _historical_boundary_valid(root, constitution, program, errors)
    capability_influence = _capability_influence_valid(constitution, errors)
    supporting_documents = _supporting_documents_exist(root, constitution, errors)
    frozen_v02_profile = _frozen_v02_profile_artifacts_valid(root, errors)
    normative_profile = _normative_profile_binding_valid(root, program, errors)
    terminal_release_binding = _terminal_release_binding_valid(root, program, errors)
    criteria_before = len(errors)
    criteria = _criteria(acceptance, errors)
    criteria_valid = len(errors) == criteria_before
    graph_before = len(errors)
    increments, all_work, active_increment = _program_graph(program, criteria, errors)
    graph_valid = len(errors) == graph_before
    progression_policy = _progression_policy_valid(program, errors)
    authority_before = len(errors)
    authority_files = _authority_files(root, constitution, errors)
    authority_identity = _authority_identity_valid(authority_files, errors)
    authority_identity = (
        authority_identity
        and release_identity
        and historical_boundary
        and capability_influence
        and supporting_documents
        and frozen_v02_profile
        and normative_profile
        and terminal_release_binding
        and progression_policy
        and len(errors) == authority_before
    )
    work_bindings: dict[str, tuple[str, set[str], str]] = {}
    for increment in increments:
        increment_id = increment.get("id")
        work_items = increment.get("workItems")
        if not isinstance(increment_id, str) or not isinstance(work_items, list):
            continue
        for work in work_items:
            if not isinstance(work, dict) or not isinstance(work.get("id"), str):
                continue
            mapped = _string_list(work.get("acceptanceIds")) or []
            work_state = work.get("state") if isinstance(work.get("state"), str) else ""
            work_bindings[work["id"]] = (increment_id, set(mapped), work_state)
    registration_before = len(errors)
    registration_floors, registration_validator_bindings = _task_registration_floors(
        root,
        increments,
        criteria,
        program.get("normativeProfileBinding")
        if isinstance(program.get("normativeProfileBinding"), dict)
        else {},
        errors,
    )
    registrations_valid = len(errors) == registration_before
    evidence_states, evidence_valid, validated_work_outcomes = _evidence_states(
        root,
        criteria,
        work_bindings,
        registration_floors,
        registration_validator_bindings,
        errors,
    )
    authority_guardrail = _authority_guardrail(program, all_work, errors)
    process_loss_valid = _process_loss_guardrail(
        root, increments, validated_work_outcomes, errors
    )
    process_guardrail = registrations_valid and process_loss_valid and graph_valid

    states = {criterion_id: False for criterion_id in EXPECTED_CRITERION_IDS}
    states.update(evidence_states)
    states["G1"] = authority_guardrail
    states["G2"] = criteria_valid and evidence_valid
    states["G3"] = authority_identity
    states["G4"] = process_guardrail

    guardrails_pass = all(states[criterion_id] for criterion_id in GUARDRAIL_IDS)
    if errors or not guardrails_pass:
        for criterion_id in OUTCOME_IDS:
            states[criterion_id] = False
    evidence_outcomes_pass = all(
        states[criterion_id] for criterion_id in OUTCOME_IDS
    )
    graph_terminal = (
        program.get("status") == "completed"
        and program.get("activeIncrementId") is None
        and all(
            isinstance(increment.get("state"), str)
            and increment.get("state") in TERMINAL_STATES
            for increment in increments
        )
        and all(
            isinstance(work.get("state"), str)
            and work.get("state") in TERMINAL_STATES
            for work in all_work
        )
    )
    terminal_release_state = (
        program.get("terminalReleaseBinding", {}).get("state", "invalid")
        if isinstance(program.get("terminalReleaseBinding"), dict)
        else "invalid"
    )
    terminal_release_verified = False
    if guardrails_pass and evidence_outcomes_pass and graph_terminal:
        terminal_release_verified, terminal_release_state = _terminal_release_gate(
            root, program, criteria, errors
        )
        if not terminal_release_verified:
            states["O5"] = False
    outcomes_pass = all(states[criterion_id] for criterion_id in OUTCOME_IDS)
    accepted = (
        not errors
        and guardrails_pass
        and outcomes_pass
        and graph_terminal
        and terminal_release_verified
    )
    valid = not errors and guardrails_pass
    source_carrier_release = _source_carrier_release_preflight(program, valid)
    return {
        "productId": PRODUCT_ID,
        "release": program.get("release"),
        "programStatus": program.get("status"),
        "valid": valid,
        "completionState": (
            "accepted"
            if accepted
            else "stopped"
            if program.get("status") == "stopped" and valid
            else "in-progress"
        ),
        "terminalReleaseState": terminal_release_state,
        "sourceCarrierRelease": source_carrier_release,
        "activeIncrement": program.get("activeIncrementId"),
        "outcomes": {
            "verified": sum(bool(states[item]) for item in OUTCOME_IDS),
            "total": len(OUTCOME_IDS),
        },
        "guardrails": {
            "passed": sum(bool(states[item]) for item in GUARDRAIL_IDS),
            "total": len(GUARDRAIL_IDS),
        },
        "criterionStates": {key: states[key] for key in sorted(states)},
        "errors": errors,
    }


def verify_product(root: Path) -> dict[str, Any]:
    """Verify current product state and fail closed without leaking tracebacks."""

    cache_token = _EVIDENCE_GIT_CACHE.set({})
    read_budget_token = _VERIFICATION_READ_BUDGET.set({"bytes": 0, "files": {}})
    try:
        try:
            return _verify_product(root)
        except Exception as exc:
            return {
                "productId": PRODUCT_ID,
                "release": None,
                "programStatus": None,
                "valid": False,
                "completionState": "in-progress",
                "terminalReleaseState": "invalid",
                "sourceCarrierRelease": {
                    "allowed": False,
                    "state": "unknown-stop-before-release",
                    "reason": "authority-verification-failed",
                    "scope": "live-cohort-source-dependency-only",
                },
                "activeIncrement": None,
                "outcomes": {"verified": 0, "total": len(OUTCOME_IDS)},
                "guardrails": {"passed": 0, "total": len(GUARDRAIL_IDS)},
                "criterionStates": {
                    key: False for key in sorted(EXPECTED_CRITERION_IDS)
                },
                "errors": [f"verifier failed closed: {exc.__class__.__name__}"],
            }
    finally:
        _VERIFICATION_READ_BUDGET.reset(read_budget_token)
        _EVIDENCE_GIT_CACHE.reset(cache_token)
