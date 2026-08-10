import json
from pathlib import Path
import unittest

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


def strict_object_records(value: object) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if isinstance(value, dict):
        if value.get("type") == "object":
            records.append(value)
        for nested in value.values():
            records.extend(strict_object_records(nested))
    elif isinstance(value, list):
        for nested in value:
            records.extend(strict_object_records(nested))
    return records


def schema_references(value: object) -> list[str]:
    references: list[str] = []
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            references.append(reference)
        for nested in value.values():
            references.extend(schema_references(nested))
    elif isinstance(value, list):
        for nested in value:
            references.extend(schema_references(nested))
    return references


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

    def test_schema_owned_object_records_declare_closed_field_sets(self) -> None:
        """Removing a nested record's field contract must fail this test."""

        schemas = self.load_schemas()
        for schema_name, schema in schemas.items():
            for record in strict_object_records(schema):
                with self.subTest(schema=schema_name, record=record.get("title")):
                    self.assertIn("properties", record)
                    self.assertIn("required", record)
                    self.assertFalse(record.get("additionalProperties", True))

    def test_schema_metadata_targets_bound_records_and_scalar_contracts(self) -> None:
        """Replacing a bound record, counter, or scalar contract must fail this test."""

        schemas = self.load_schemas()
        for schema_name, schema in schemas.items():
            with self.subTest(schema=schema_name, field="schema"):
                scalar = schema["properties"]["schema"]
                self.assertEqual("integer", scalar["type"])
                self.assertEqual(2 if schema_name == "authority" else 1, scalar["const"])

        authority = schemas["authority"]
        self.assertEqual("integer", authority["properties"]["generation"]["type"])
        for property_name in ("predecessorBinding", "programPlanBinding"):
            binding = resolve_schema_reference(
                authority, authority["properties"][property_name]
            )
            self.assertEqual(
                {"authoritySchema", "id", "generation", "path", "sha256"},
                set(binding["required"]),
            )

        selector = schemas["selector"]
        activation = selector["properties"]["activationAuthorized"]
        self.assertEqual("boolean", activation["type"])
        self.assertIs(False, activation["const"])
        for schema_name in ("selector", "receipt"):
            counters = resolve_schema_reference(
                schemas[schema_name],
                schemas[schema_name]["properties"]["executionCounters"],
            )
            for counter_schema in counters["properties"].values():
                self.assertEqual("integer", counter_schema["type"])
                self.assertEqual(0, counter_schema["const"])

    def test_binding_references_declare_the_v1_v2_generation_conditions(self) -> None:
        """Dropping a binding reference or generation condition must fail this test."""

        schemas = self.load_schemas()
        for schema_name, schema in schemas.items():
            for reference in schema_references(schema):
                with self.subTest(schema=schema_name, reference=reference):
                    self.assertTrue(reference.startswith("#/$defs/"))
                    self.assertIn(reference.removeprefix("#/$defs/"), schema["$defs"])

        for schema_name in ("authority", "selector", "receipt"):
            binding = schemas[schema_name]["$defs"]["binding"]
            branches = binding["allOf"]
            self.assertEqual(2, len(branches))
            self.assertEqual(1, branches[0]["if"]["properties"]["authoritySchema"]["const"])
            self.assertEqual("null", branches[0]["then"]["properties"]["generation"]["type"])
            self.assertEqual(2, branches[1]["if"]["properties"]["authoritySchema"]["const"])
            self.assertEqual("integer", branches[1]["then"]["properties"]["generation"]["type"])


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

    def test_binding_rejects_boolean_and_float_numeric_aliases(self) -> None:
        """Weakening exact runtime numeric checks must fail this test."""

        for authority_schema, generation, expected_code in (
            (True, None, "acceptance-authority-schema-invalid"),
            (2, True, "acceptance-authority-generation-invalid"),
            (2, 1.0, "acceptance-authority-generation-invalid"),
        ):
            with self.subTest(authority_schema=authority_schema, generation=generation):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    binding_for_bytes(
                        authority_schema=authority_schema,
                        authority_id="bound-authority",
                        generation=generation,
                        path="bound.json",
                        data=b"bound bytes",
                    )
                self.assertEqual(expected_code, raised.exception.code)
