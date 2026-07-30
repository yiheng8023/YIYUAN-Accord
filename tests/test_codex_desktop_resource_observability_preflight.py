import unittest

from scripts.validate_codex_desktop_resource_observability_preflight import (
    validate_preflight,
)


class CodexDesktopResourceObservabilityPreflightTests(unittest.TestCase):
    def test_preflight_is_consistent(self) -> None:
        validate_preflight()


if __name__ == "__main__":
    unittest.main()
