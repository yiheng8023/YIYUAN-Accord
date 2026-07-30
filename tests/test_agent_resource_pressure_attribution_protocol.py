import unittest

from scripts.validate_agent_resource_pressure_attribution_protocol import (
    validate_protocol,
)


class AgentResourcePressureAttributionProtocolTests(unittest.TestCase):
    def test_protocol_is_consistent(self) -> None:
        validate_protocol()


if __name__ == "__main__":
    unittest.main()
