from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.harness_decision_packet import strict_json_equal


LEGACY_LOCKS = {
    "acceptance": (
        Path("registry/program-acceptance-map.json"),
        "id",
        "curation-program-acceptance-map-v1",
        "c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f",
        "legacy-authority-drift",
    ),
    "programPlan": (
        Path("registry/curation-program-plan.json"),
        "id",
        "curation-program-plan-v1",
        "38bba19b4f4f8471ea7ebaa80765e4110fa169ff892eec3784e3316783a88bd3",
        "legacy-program-plan-drift",
    ),
    "packetFixture": (
        Path("tests/fixtures/harness-decision-packet-gen-research-01.json"),
        "packetId",
        "harness-decision-packet-v1:fixture.gen-research-01",
        "58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22",
        "legacy-packet-fixture-drift",
    ),
    "manifestFixture": (
        Path("tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json"),
        "id",
        "harness-decision-packet-thirteen-scenario-manifest-v1",
        "ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3",
        "legacy-manifest-fixture-drift",
    ),
}


class AcceptanceAuthorityError(ValueError):
    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


def canonical_file_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
        + b"\n"
    )


def file_sha256(root: Path, relative: Path) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def binding_for_bytes(
    *,
    authority_schema: int,
    authority_id: str,
    generation: int | None,
    path: str,
    data: bytes,
) -> dict[str, object]:
    if type(authority_schema) is not int:
        raise AcceptanceAuthorityError(
            "acceptance-authority-schema-invalid",
            "Authority schema must be an integer.",
            path=path,
        )
    if authority_schema not in (1, 2):
        raise AcceptanceAuthorityError(
            "acceptance-authority-schema-invalid",
            "Authority schema must be version 1 or 2.",
            path=path,
        )
    if (authority_schema == 1 and generation is not None) or (
        authority_schema != 1 and (type(generation) is not int or generation < 1)
    ):
        raise AcceptanceAuthorityError(
            "acceptance-authority-generation-invalid",
            "Only legacy v1 bindings may have a null generation.",
            path=path,
        )
    return {
        "authoritySchema": authority_schema,
        "id": authority_id,
        "generation": generation,
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def validate_legacy_locks(
    root: Path,
    *,
    expected: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    locks: dict[str, dict[str, Any]] = {}
    for name, (
        relative,
        identity_field,
        expected_identity,
        locked_sha256,
        error_code,
    ) in LEGACY_LOCKS.items():
        expected_sha256 = expected.get(name, locked_sha256) if expected is not None else locked_sha256
        actual_sha256 = file_sha256(root, relative)
        path = relative.as_posix()
        if not strict_json_equal(actual_sha256, expected_sha256):
            raise AcceptanceAuthorityError(
                error_code,
                "Legacy authority bytes do not match the locked SHA-256.",
                path=path,
            )
        document = json.loads((root / relative).read_bytes())
        if not isinstance(document, dict) or not strict_json_equal(
            document.get(identity_field), expected_identity
        ):
            raise AcceptanceAuthorityError(
                error_code,
                "Legacy authority identity does not match the lock.",
                path=path,
            )
        locks[name] = {
            "id": expected_identity,
            "path": path,
            "sha256": actual_sha256,
        }
    return locks
