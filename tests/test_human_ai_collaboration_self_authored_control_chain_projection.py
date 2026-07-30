from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.build_human_ai_collaboration_self_authored_control_chain_projection import (
    materialize_current_chain,
)


class SelfAuthoredControlChainProjectionTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict]:
        source = root / "source"
        files = {
            ("intent-contract", "SKILL.md"): b"intent\n",
            (
                "intent-contract",
                "references/intake-contract.md",
            ): b"intake\n",
            ("capability-router", "SKILL.md"): b"router\n",
            (
                "capability-router",
                "references/routing-contract.md",
            ): b"routing\n",
            ("closure-contract", "SKILL.md"): b"closure\n",
        }
        for (skill, relative), payload in files.items():
            path = source / skill / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        skill_rows = []
        dependency_rows = []
        for (skill, relative), payload in files.items():
            record = {
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            if relative == "SKILL.md":
                skill_rows.append({"name": skill, **record})
            else:
                dependency_rows.append(
                    {
                        "skillName": skill,
                        "relativePath": relative,
                        **record,
                    }
                )
        protocol = {
            "factors": {
                "chain": {
                    "exactSkillPins": skill_rows,
                    "exactDependencyPins": dependency_rows,
                }
            }
        }
        return source, protocol

    def test_materializes_five_verified_files_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, protocol = self.fixture(root)
            output = root / "projection"
            manifest = materialize_current_chain(
                output,
                source_root=source,
                protocol=protocol,
            )
            self.assertEqual(5, manifest["requiredFileCount"])
            self.assertEqual(3, len(manifest["skillPaths"]))
            self.assertTrue(
                all(
                    Path(path).is_relative_to(output)
                    for path in manifest["skillPaths"].values()
                )
            )
            self.assertEqual(
                5,
                len(
                    [
                        path
                        for path in output.rglob("*")
                        if path.is_file()
                        and path.name
                        != "SELF-AUTHORED-CONTROL-CHAIN-PROJECTION.json"
                    ]
                ),
            )

    def test_digest_drift_leaves_no_projection_or_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, protocol = self.fixture(root)
            drifted = copy.deepcopy(protocol)
            drifted["factors"]["chain"]["exactDependencyPins"][0][
                "sha256"
            ] = "0" * 64
            output = root / "projection"
            with self.assertRaisesRegex(RuntimeError, "digest drifted"):
                materialize_current_chain(
                    output,
                    source_root=source,
                    protocol=drifted,
                )
            self.assertFalse(output.exists())
            self.assertEqual([], list(root.glob("projection.partial-*")))

    def test_existing_output_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, protocol = self.fixture(root)
            output = root / "projection"
            output.mkdir()
            with self.assertRaisesRegex(RuntimeError, "must not already exist"):
                materialize_current_chain(
                    output,
                    source_root=source,
                    protocol=protocol,
                )


if __name__ == "__main__":
    unittest.main()
