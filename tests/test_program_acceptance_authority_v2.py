import json
from pathlib import Path
import unittest

from scripts.harness_decision_packet import strict_json_equal
from scripts.program_acceptance_authority_v2 import (
    AcceptanceAuthorityError,
    binding_for_bytes,
    validate_legacy_locks,
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATHS = {
    "authority": ROOT / "schemas/program-acceptance-authority-v2.schema.json",
    "selector": ROOT / "schemas/program-acceptance-current-selector-v1.schema.json",
    "receipt": ROOT / "schemas/program-acceptance-transition-receipt-v1.schema.json",
    "inventory": ROOT / "schemas/program-acceptance-migration-inventory-v1.schema.json",
}
REQUIRED_FIELDS = {
    "authority": {
        "schema",
        "id",
        "authoritySeriesId",
        "generation",
        "predecessorBinding",
        "programPlanBinding",
        "assessmentVocabulary",
        "objectives",
        "acceptanceCriteria",
        "verifications",
        "evidence",
    },
    "selector": {
        "schema",
        "id",
        "authoritySeriesId",
        "selectionMode",
        "activeSnapshotBinding",
        "activeTransitionBinding",
        "programPlanBinding",
        "activationAuthorized",
        "executionCounters",
    },
    "receipt": {
        "schema",
        "id",
        "authoritySeriesId",
        "transactionType",
        "fromSnapshotBinding",
        "toSnapshotBinding",
        "fromProgramPlanBinding",
        "toProgramPlanBinding",
        "delta",
        "invariants",
        "authorizationBoundary",
        "executionCounters",
        "claimBoundary",
    },
    "inventory": {
        "schema",
        "id",
        "date",
        "status",
        "sourcePatternIds",
        "baselineObservation",
        "occurrences",
        "claimBoundary",
    },
}


def schema_accepts_scalar(schema: dict[str, object], value: object) -> bool:
    expected_type = schema.get("type")
    if expected_type == "integer" and type(value) is not int:
        return False
    if expected_type == "boolean" and type(value) is not bool:
        return False
    if "const" in schema and not strict_json_equal(value, schema["const"]):
        return False
    return True


def resolve_schema_reference(
    root_schema: dict[str, object], schema: dict[str, object]
) -> dict[str, object]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    prefix = "#/$defs/"
    if not isinstance(reference, str) or not reference.startswith(prefix):
        raise AssertionError(f"Unexpected schema reference: {reference!r}")
    return root_schema["$defs"][reference.removeprefix(prefix)]


class ProgramAcceptanceAuthorityLegacyTests(unittest.TestCase):
    def test_exact_legacy_locks_are_current(self) -> None:
        locks = validate_legacy_locks(ROOT)
        self.assertEqual(
            "c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f",
            locks["acceptance"]["sha256"],
        )
        self.assertEqual(
            "38bba19b4f4f8471ea7ebaa80765e4110fa169ff892eec3784e3316783a88bd3",
            locks["programPlan"]["sha256"],
        )
        self.assertEqual(
            "58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22",
            locks["packetFixture"]["sha256"],
        )
        self.assertEqual(
            "ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3",
            locks["manifestFixture"]["sha256"],
        )

    def test_legacy_lock_drift_has_a_typed_code(self) -> None:
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            validate_legacy_locks(ROOT, expected={"acceptance": "0" * 64})
        self.assertEqual("legacy-authority-drift", raised.exception.code)


class ProgramAcceptanceAuthoritySchemaTests(unittest.TestCase):
    def load_schemas(self) -> dict[str, dict[str, object]]:
        return {
            name: json.loads(path.read_text(encoding="utf-8"))
            for name, path in SCHEMA_PATHS.items()
        }

    def test_schema_roots_have_exact_required_fields(self) -> None:
        for name, schema in self.load_schemas().items():
            with self.subTest(schema=name):
                self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
                self.assertEqual("object", schema["type"])
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(REQUIRED_FIELDS[name], set(schema["required"]))

    def test_schema_scalars_reject_boolean_and_float_aliases(self) -> None:
        schemas = self.load_schemas()
        for name, schema in schemas.items():
            with self.subTest(schema=name, field="schema"):
                property_schema = schema["properties"]["schema"]
                values = (True, 1, 1.0) if name == "authority" else (True, 1.0)
                for value in values:
                    self.assertFalse(schema_accepts_scalar(property_schema, value))

        authority = schemas["authority"]
        generation = authority["properties"]["generation"]
        self.assertTrue(schema_accepts_scalar(generation, 1))
        for value in (True, 1.0):
            self.assertFalse(schema_accepts_scalar(generation, value))

        selector = schemas["selector"]
        activation = selector["properties"]["activationAuthorized"]
        for value in (True, 1, 1.0):
            self.assertFalse(schema_accepts_scalar(activation, value))

        for schema_name in ("selector", "receipt"):
            counters = resolve_schema_reference(
                schemas[schema_name],
                schemas[schema_name]["properties"]["executionCounters"],
            )
            for counter_name, counter_schema in counters["properties"].items():
                with self.subTest(schema=schema_name, counter=counter_name):
                    self.assertTrue(schema_accepts_scalar(counter_schema, 0))
                    for value in (True, 1, 1.0):
                        self.assertFalse(schema_accepts_scalar(counter_schema, value))


class ProgramAcceptanceAuthorityBindingTests(unittest.TestCase):
    def test_only_legacy_v1_bindings_may_have_null_generation(self) -> None:
        for authority_schema, generation in ((1, 1), (2, None)):
            with self.subTest(authority_schema=authority_schema, generation=generation):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    binding_for_bytes(
                        authority_schema=authority_schema,
                        authority_id="bound-authority",
                        generation=generation,
                        path="bound.json",
                        data=b"bound bytes",
                    )
                self.assertEqual(
                    "acceptance-authority-generation-invalid", raised.exception.code
                )
