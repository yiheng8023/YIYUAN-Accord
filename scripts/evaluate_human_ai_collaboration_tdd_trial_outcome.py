#!/usr/bin/env python3
"""Evaluate final TDD fixture behavior with a parent-owned oracle and mutants."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

try:
    from .build_human_ai_collaboration_tdd_trial import (
        PRIVATE_ORACLE,
        canonical_sha256,
    )
except ImportError:
    from build_human_ai_collaboration_tdd_trial import (
        PRIVATE_ORACLE,
        canonical_sha256,
    )


EVALUATOR_CONTRACT_VERSION = "capped-backoff-parent-outcome-evaluator-v1"
VISIBLE_TEST_COMMAND = [
    sys.executable,
    "-B",
    "-m",
    "unittest",
    "-v",
    "test_feature.py",
]
FORBIDDEN_TEST_SOURCE_PATTERNS = {
    "implementation-source-read": re.compile(
        r"\b(?:inspect|getsource|read_text|read_bytes|open)\b"
    ),
    "bytecode-or-code-object-introspection": re.compile(
        r"\b(?:dis|__code__|co_code|co_consts)\b"
    ),
    "private-oracle-reference": re.compile(
        r"\b(?:PRIVATE_ORACLE|MUTANT_IMPLEMENTATIONS|hidden oracle)\b",
        re.IGNORECASE,
    ),
}
HIDDEN_ORACLE_SOURCE = r'''
import unittest

from feature import capped_backoff_delay


class ParentOwnedCappedBackoffOracle(unittest.TestCase):
    def test_literal_functional_cases(self):
        cases = (
            (1, [3, 7, 15], 3),
            (2, [3, 7, 15], 7),
            (3, [3, 7, 15], 15),
            (8, [3, 7, 15], 15),
        )
        for attempt, schedule, expected in cases:
            with self.subTest(attempt=attempt, schedule=schedule):
                actual = capped_backoff_delay(attempt, schedule)
                self.assertIs(type(actual), int)
                self.assertEqual(expected, actual)

    def test_invalid_inputs_raise_value_error(self):
        invalid = (
            (0, [3]),
            (True, [3]),
            (1.5, [3]),
            (1, []),
            (1, "3,7"),
            (1, [0, 3]),
            (1, [True, 3]),
        )
        for attempt, schedule in invalid:
            with self.subTest(attempt=attempt, schedule=schedule):
                with self.assertRaises(ValueError):
                    capped_backoff_delay(attempt, schedule)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    ParentOwnedCappedBackoffOracle
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''

VALIDATION_PREAMBLE = '''"""Mutant implementation for parent-owned evaluation."""


def _validate_attempt(attempt):
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")


def _validate_schedule(schedule):
    if not isinstance(schedule, (list, tuple)) or not schedule:
        raise ValueError("schedule must be a non-empty list or tuple")
    if any(
        isinstance(delay, bool) or not isinstance(delay, int) or delay <= 0
        for delay in schedule
    ):
        raise ValueError("schedule entries must be positive integers")
'''

MUTANT_IMPLEMENTATIONS = {
    "off-by-one-attempt-index": VALIDATION_PREAMBLE
    + '''

def capped_backoff_delay(attempt, schedule):
    _validate_attempt(attempt)
    _validate_schedule(schedule)
    return schedule[min(attempt, len(schedule) - 1)]
''',
    "no-cap-after-final-entry": VALIDATION_PREAMBLE
    + '''

def capped_backoff_delay(attempt, schedule):
    _validate_attempt(attempt)
    _validate_schedule(schedule)
    return schedule[attempt - 1]
''',
    "bool-attempt-accepted": '''"""Mutant implementation."""


def capped_backoff_delay(attempt, schedule):
    if not isinstance(attempt, int) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(schedule, (list, tuple)) or not schedule:
        raise ValueError("schedule must be a non-empty list or tuple")
    if any(
        isinstance(delay, bool) or not isinstance(delay, int) or delay <= 0
        for delay in schedule
    ):
        raise ValueError("schedule entries must be positive integers")
    return schedule[min(attempt - 1, len(schedule) - 1)]
''',
    "empty-schedule-accepted": '''"""Mutant implementation."""


def capped_backoff_delay(attempt, schedule):
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(schedule, (list, tuple)):
        raise ValueError("schedule must be a list or tuple")
    if not schedule:
        return None
    if any(
        isinstance(delay, bool) or not isinstance(delay, int) or delay <= 0
        for delay in schedule
    ):
        raise ValueError("schedule entries must be positive integers")
    return schedule[min(attempt - 1, len(schedule) - 1)]
''',
    "nonpositive-delay-accepted": '''"""Mutant implementation."""


def capped_backoff_delay(attempt, schedule):
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(schedule, (list, tuple)) or not schedule:
        raise ValueError("schedule must be a non-empty list or tuple")
    if any(
        isinstance(delay, bool) or not isinstance(delay, int)
        for delay in schedule
    ):
        raise ValueError("schedule entries must be integers")
    return schedule[min(attempt - 1, len(schedule) - 1)]
''',
    "string-schedule-accepted": '''"""Mutant implementation."""


def capped_backoff_delay(attempt, schedule):
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(schedule, (list, tuple, str)) or not schedule:
        raise ValueError("schedule must be non-empty")
    if not isinstance(schedule, str) and any(
        isinstance(delay, bool) or not isinstance(delay, int) or delay <= 0
        for delay in schedule
    ):
        raise ValueError("schedule entries must be positive integers")
    return schedule[min(attempt - 1, len(schedule) - 1)]
''',
    "bool-delay-accepted": '''"""Mutant implementation."""


def capped_backoff_delay(attempt, schedule):
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(schedule, (list, tuple)) or not schedule:
        raise ValueError("schedule must be a non-empty list or tuple")
    if any(not isinstance(delay, int) or delay <= 0 for delay in schedule):
        raise ValueError("schedule entries must be positive integers")
    return schedule[min(attempt - 1, len(schedule) - 1)]
''',
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_python(
    command: list[str],
    *,
    cwd: Path,
    stdin_text: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=timeout_seconds,
        check=False,
    )
    output = completed.stdout + completed.stderr
    return {
        "exitCode": completed.returncode,
        "outputBytes": len(output.encode("utf-8")),
        "outputSha256": sha256_bytes(output.encode("utf-8")),
        "ranTestCount": (
            int(match.group(1))
            if (
                match := re.search(
                    r"Ran\s+(\d+)\s+tests?",
                    output,
                    re.IGNORECASE,
                )
            )
            else None
        ),
        "greenProved": (
            completed.returncode == 0
            and re.search(r"Ran\s+[1-9]\d*\s+tests?", output, re.IGNORECASE)
            is not None
            and re.search(r"(?m)^OK$", output) is not None
        ),
        "assertionFailureObserved": (
            completed.returncode != 0
            and "AssertionError" in output
            and "FAILED (failures=" in output
        ),
        "syntaxOrImportErrorObserved": any(
            token in output
            for token in (
                "SyntaxError",
                "ImportError",
                "ModuleNotFoundError",
                "Failed to import test module",
            )
        ),
    }


def test_source_boundary(test_source: str) -> dict[str, Any]:
    violations = [
        name
        for name, pattern in FORBIDDEN_TEST_SOURCE_PATTERNS.items()
        if pattern.search(test_source)
    ]
    return {
        "status": "accepted" if not violations else "rejected",
        "failureCodes": violations,
        "testSourceBytes": len(test_source.encode("utf-8")),
        "testSourceSha256": sha256_bytes(test_source.encode("utf-8")),
    }


def validate_oracle_alignment() -> None:
    if set(MUTANT_IMPLEMENTATIONS) != set(PRIVATE_ORACLE["mutants"]):
        raise RuntimeError("executable mutant ids drifted from private oracle")
    expected_hidden_hash = canonical_sha256(
        {
            "functionalCases": PRIVATE_ORACLE["functionalCases"],
            "invalidCases": PRIVATE_ORACLE["invalidCases"],
            "mutants": PRIVATE_ORACLE["mutants"],
        }
    )
    if expected_hidden_hash != canonical_sha256(PRIVATE_ORACLE):
        raise RuntimeError("private oracle projection drifted")


def evaluate_trial_outcome(
    trial_root: Path,
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    validate_oracle_alignment()
    trial_root = trial_root.resolve()
    feature_path = trial_root / "feature.py"
    test_path = trial_root / "test_feature.py"
    if not feature_path.is_file() or not test_path.is_file():
        raise RuntimeError("trial outcome requires feature.py and test_feature.py")
    test_source = test_path.read_text(encoding="utf-8")
    source_boundary = test_source_boundary(test_source)
    visible = run_python(
        VISIBLE_TEST_COMMAND,
        cwd=trial_root,
        timeout_seconds=timeout_seconds,
    )
    hidden = run_python(
        [sys.executable, "-B", "-"],
        cwd=trial_root,
        stdin_text=HIDDEN_ORACLE_SOURCE,
        timeout_seconds=timeout_seconds,
    )
    mutants: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="aah-tdd-mutants-") as temporary:
        mutant_root = Path(temporary)
        for mutant_id, implementation in MUTANT_IMPLEMENTATIONS.items():
            case_root = mutant_root / mutant_id
            case_root.mkdir()
            shutil.copy2(test_path, case_root / "test_feature.py")
            (case_root / "feature.py").write_text(
                implementation,
                encoding="utf-8",
            )
            result = run_python(
                VISIBLE_TEST_COMMAND,
                cwd=case_root,
                timeout_seconds=timeout_seconds,
            )
            killed = (
                result["exitCode"] != 0
                and isinstance(result["ranTestCount"], int)
                and result["ranTestCount"] > 0
                and not result["syntaxOrImportErrorObserved"]
            )
            mutants.append(
                {
                    "id": mutant_id,
                    "implementationSha256": sha256_bytes(
                        implementation.encode("utf-8")
                    ),
                    "killed": killed,
                    "result": result,
                }
            )
    failures: list[str] = []
    if source_boundary["status"] != "accepted":
        failures.append("agent-test-source-boundary-rejected")
    if not visible["greenProved"]:
        failures.append("visible-suite-not-green")
    if not hidden["greenProved"]:
        failures.append("parent-hidden-oracle-not-green")
    survivors = [item["id"] for item in mutants if not item["killed"]]
    if survivors:
        failures.append("predeclared-mutants-survived")
    return {
        "evaluatorContractVersion": EVALUATOR_CONTRACT_VERSION,
        "status": (
            "parent-outcome-accepted"
            if not failures
            else "parent-outcome-rejected"
        ),
        "failureCodes": failures,
        "sourceBoundary": source_boundary,
        "visibleSuite": visible,
        "hiddenOracle": {
            **hidden,
            "oracleSourceBytes": len(HIDDEN_ORACLE_SOURCE.encode("utf-8")),
            "oracleSourceSha256": sha256_bytes(
                HIDDEN_ORACLE_SOURCE.encode("utf-8")
            ),
            "contentWrittenIntoTrial": False,
        },
        "mutants": mutants,
        "mutantCount": len(mutants),
        "killedMutantCount": sum(item["killed"] for item in mutants),
        "survivingMutantIds": survivors,
        "mutantSourcesWrittenIntoTrial": False,
        "claimBoundary": {
            "provesBoundFixtureFinalBehavior": not failures,
            "provesOrderedTddProcess": False,
            "provesSkillCausation": False,
            "provesProductionReadiness": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    arguments = parser.parse_args()
    result = evaluate_trial_outcome(
        arguments.trial_root,
        timeout_seconds=arguments.timeout_seconds,
    )
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output_report is not None:
        arguments.output_report.parent.mkdir(parents=True, exist_ok=True)
        arguments.output_report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if result["status"] == "parent-outcome-accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
