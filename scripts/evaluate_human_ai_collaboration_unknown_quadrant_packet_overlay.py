#!/usr/bin/env python3
"""Evaluate deterministic private-oracle overlay compatibility and faults."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/human-ai-collaboration-unknown-quadrant-"
    "packet-overlay-2026-07-27.json"
)
EXPECTED_CLASSES = {
    "known-knowns",
    "known-unknowns",
    "unknown-knowns",
    "unknown-unknowns",
    "method-attribution",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_overlay(
    overlay: dict[str, Any],
    *,
    binding: dict[str, Any] | None,
    root: Path = ROOT,
) -> str:
    if binding is None:
        return "fail-source-binding-missing"
    if overlay.get("unknownClass") != binding.get("unknownClass"):
        return "fail-unknown-class-binding"
    source_path = overlay.get("sourcePath")
    if source_path != binding.get("path"):
        return "fail-source-path-binding"
    source = root / str(source_path)
    if not source.is_file():
        return "fail-source-file-missing"
    source_bytes = source.read_bytes()
    if (
        len(source_bytes) != binding.get("bytes")
        or _sha256(source) != binding.get("sha256")
    ):
        return "fail-source-byte-identity"
    source_document = json.loads(source_bytes.decode("utf-8"))
    if source_document.get("id") != binding.get("documentId"):
        return "fail-source-document-identity"
    if overlay.get("sourceIdentityVerified") is not True:
        return "fail-source-identity-unverified"
    if (
        overlay.get("publicPacketUnchanged") is not True
        or overlay.get("sourcePacketModified") is not False
    ):
        return "fail-source-packet-mutation"
    if overlay.get("privateOracleExposedToAgent") is not False:
        return "fail-private-oracle-exposure"
    if overlay.get("hardStandardsChanged") is not False:
        return "fail-hard-standard-drift"
    if overlay.get("modelDispatchAuthorized") is not False:
        return "fail-live-authority-expansion"
    return "compatible-zero-model-private-overlay"


def evaluate_document(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    bindings = {
        item["path"]: item for item in document.get("sourceBindings", [])
    }
    overlays = {
        item["id"]: item for item in document.get("overlays", [])
    }
    base_results = [
        {
            "id": overlay_id,
            "actual": evaluate_overlay(
                overlay,
                binding=bindings.get(str(overlay.get("sourcePath", ""))),
                root=root,
            ),
        }
        for overlay_id, overlay in overlays.items()
    ]
    fault_results: list[dict[str, str]] = []
    for fault in document.get("faultInjections", []):
        target = overlays.get(str(fault.get("targetOverlayId", "")))
        if target is None:
            actual = "fail-fault-target-missing"
        else:
            mutated = copy.deepcopy(target)
            changes = fault.get("changes", {})
            if not isinstance(changes, dict):
                actual = "fail-fault-changes-invalid"
            else:
                mutated.update(copy.deepcopy(changes))
                actual = evaluate_overlay(
                    mutated,
                    binding=bindings.get(
                        str(mutated.get("sourcePath", ""))
                    ),
                    root=root,
                )
        fault_results.append(
            {
                "id": str(fault.get("id", "")),
                "expected": str(fault.get("expected", "")),
                "actual": actual,
            }
        )
    return {
        "baseResults": base_results,
        "faultResults": fault_results,
        "unknownClasses": sorted(
            {
                str(item.get("unknownClass", ""))
                for item in document.get("overlays", [])
            }
        ),
    }


def main() -> int:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    result = evaluate_document(document)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    expected_base = document.get("expectedBaseResult")
    base_pass = all(
        item["actual"] == expected_base for item in result["baseResults"]
    )
    fault_pass = all(
        item["actual"] == item["expected"] for item in result["faultResults"]
    )
    class_pass = set(result["unknownClasses"]) == EXPECTED_CLASSES
    return 0 if base_pass and fault_pass and class_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
