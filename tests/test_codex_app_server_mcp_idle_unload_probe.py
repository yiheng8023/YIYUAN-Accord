import os
from pathlib import Path
import tempfile
import unittest

from scripts.probe_codex_app_server_mcp_idle_unload import (
    DOCUMENTED_IDLE_SECONDS,
    classify_idle_observation,
    process_identity_complete,
    run_probe,
    same_process_identity,
    snapshot_process,
)


ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / "scripts/mcp_lifecycle_sentinel.py"


class CodexAppServerMcpIdleUnloadProbeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "exact process identity is Windows-only")
    def test_current_process_identity_is_complete(self) -> None:
        identity = snapshot_process(os.getpid())
        self.assertTrue(process_identity_complete(identity))
        self.assertEqual(os.getpid(), identity["pid"])
        self.assertTrue(str(identity["imagePath"]).lower().endswith(".exe"))

    def test_process_identity_rejects_pid_reuse_or_parent_drift(self) -> None:
        baseline = {
            "pid": 10,
            "exists": True,
            "imagePath": "C:/python.exe",
            "creationTime100ns": 100,
            "parentPid": 5,
        }
        self.assertTrue(same_process_identity(baseline, dict(baseline)))
        for key, value in (
            ("creationTime100ns", 101),
            ("imagePath", "C:/other.exe"),
            ("parentPid", 6),
        ):
            changed = dict(baseline)
            changed[key] = value
            self.assertFalse(same_process_identity(baseline, changed))
        missing = dict(baseline)
        missing["exists"] = False
        self.assertFalse(same_process_identity(baseline, missing))

    def test_short_observation_cannot_prove_documented_idle_unload(self) -> None:
        result = classify_idle_observation(
            {
                "requestedObservationSeconds": DOCUMENTED_IDLE_SECONDS - 1,
                "durationMilliseconds": (DOCUMENTED_IDLE_SECONDS - 1) * 1000,
                "threadClosedObserved": True,
                "sentinelExactIdentityAbsentObserved": True,
                "stdoutClosedBeforeObservationFinished": False,
            },
            natural_instance_stop_observed=True,
            recovery_call_succeeded=True,
        )
        self.assertEqual(
            "short-preflight-does-not-test-thirty-minute-idle-unload",
            result,
        )

    def test_long_observation_requires_thread_child_stop_and_recovery(self) -> None:
        base = {
            "requestedObservationSeconds": DOCUMENTED_IDLE_SECONDS,
            "durationMilliseconds": DOCUMENTED_IDLE_SECONDS * 1000,
            "threadClosedObserved": True,
            "sentinelExactIdentityAbsentObserved": True,
            "stdoutClosedBeforeObservationFinished": False,
        }
        self.assertEqual(
            "observed-single-host-sentinel-idle-unload-and-new-thread-recovery",
            classify_idle_observation(base, True, True),
        )
        self.assertEqual(
            "partial-process-absent-natural-sentinel-stop-event-missing",
            classify_idle_observation(base, False, True),
        )
        self.assertEqual(
            "partial-idle-unload-observed-recovery-call-failed",
            classify_idle_observation(base, True, False),
        )
        ended_early = dict(base)
        ended_early["durationMilliseconds"] -= 1
        self.assertEqual(
            "blocked-observation-ended-before-thirty-minute-threshold",
            classify_idle_observation(ended_early, True, True),
        )
        no_close = dict(base)
        no_close["threadClosedObserved"] = False
        self.assertEqual(
            "not-observed-thread-remained-loaded-after-idle-window",
            classify_idle_observation(no_close, True, True),
        )

    def test_probe_rejects_default_or_nonempty_home_before_launch(self) -> None:
        if os.name != "nt":
            with self.assertRaisesRegex(RuntimeError, "requires Windows"):
                run_probe(
                    Path.home() / ".codex",
                    Path(tempfile.gettempdir()) / "unused-mcp-idle-workspace",
                    SENTINEL,
                    None,
                    0,
                    0.1,
                    1,
                )
            return
        with self.assertRaisesRegex(RuntimeError, "default Codex home"):
            run_probe(
                Path.home() / ".codex",
                Path(tempfile.gettempdir()) / "unused-mcp-idle-workspace",
                SENTINEL,
                None,
                0,
                0.1,
                1,
            )
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "preserve.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "absent or empty"):
                run_probe(
                    home,
                    home / "workspace",
                    SENTINEL,
                    None,
                    0,
                    0.1,
                    1,
                )


if __name__ == "__main__":
    unittest.main()
