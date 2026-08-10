import json
import copy
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.program_acceptance_authority_v2 import (
    AcceptanceAuthorityError,
    TARGET_CRITERION_ID,
    MANIFEST_EVIDENCE_ID,
    assessment_inventory,
    binding_for_bytes,
    build_candidate_program_plan_v2,
    build_evidence_snapshot_v2,
    build_structural_snapshot_v2,
    canonical_file_bytes,
    authority_business_projection,
    validate_legacy_locks,
    validate_authority_snapshot,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = ROOT / "tests/fixtures/program-acceptance-authority-v2-rehearsal"
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
NESTED_RECORD_FIELDS = {
    "authority": {
        "binding": ("authoritySchema", "id", "generation", "path", "sha256"),
        "objective": ("id", "acceptanceIds"),
        "graduationSubgate": ("id", "requiredEvidence", "promotionBoundary", "status"),
        "basicAcceptanceCriterion": ("id", "statement", "assessment", "verificationIds", "evidenceIds"),
        "currentApplicabilityAcceptanceCriterion": ("id", "statement", "assessment", "verificationIds", "evidenceIds", "currentApplicability"),
        "semanticProjectionAcceptanceCriterion": ("id", "statement", "assessment", "verificationIds", "evidenceIds", "semanticProjectionId"),
        "graduationSubgatesAcceptanceCriterion": ("id", "statement", "assessment", "verificationIds", "evidenceIds", "graduationSubgates"),
        "verificationWithoutCommand": ("id", "method", "evidenceRequirement", "expectedResult"),
        "verificationWithCommand": ("id", "method", "command", "evidenceRequirement", "expectedResult"),
        "evidence": ("id", "path", "kind", "asOf", "supports"),
    },
    "selector": {
        "binding": ("authoritySchema", "id", "generation", "path", "sha256"),
        "zeroExecutionCounters": ("modelRequestCount", "candidateExecutionCount", "pluginExecutionCount", "installCount", "enableCount", "accountConnectionCount", "managerMutationCount", "consumerMutationCount", "publicationCount", "releaseCount", "productionActivationCount"),
    },
    "receipt": {
        "binding": ("authoritySchema", "id", "generation", "path", "sha256"),
        "criterionEvidenceLink": ("criterionId", "evidenceId"),
        "assessmentChange": ("criterionId", "fromAssessment", "toAssessment"),
        "delta": ("evidenceAdded", "evidenceRemoved", "criterionEvidenceLinksAdded", "criterionEvidenceLinksRemoved", "assessmentsChanged", "selectorTargetGeneration"),
        "invariants": ("authoritySeriesPreserved", "generationStepValid", "immutableHistoryPreserved", "programPlanBindingsValid", "acceptanceInventory"),
        "acceptanceInventory": ("verified", "partial", "planned"),
        "authorizationBoundary": ("rehearsalAuthorized", "liveMigrationAuthorized", "assessmentTransitionAuthorized", "productionActivationAuthorized"),
        "zeroExecutionCounters": ("modelRequestCount", "candidateExecutionCount", "pluginExecutionCount", "installCount", "enableCount", "accountConnectionCount", "managerMutationCount", "consumerMutationCount", "publicationCount", "releaseCount", "productionActivationCount"),
        "claimBoundary": ("provesBehavior", "provesValue", "provesCrossHostPortability", "provesProductionReadiness", "provesReleaseEligibility", "provesOverallHarnessCompletion"),
    },
    "inventory": {
        "baselineObservation": ("trackedReferenceCount", "occurrenceCount", "referenceSetSha256"),
        "occurrence": ("path", "line", "patternId", "lineSha256", "purpose", "classification", "currentBinding", "candidateBinding", "rehearsalAction", "liveMigrationAction", "rollbackAction", "verificationSurface", "separateAuthorizationRequired"),
        "claimBoundary": ("provesLiveMigration", "provesCurrentSelectorActivation", "provesBehavior", "provesValue", "provesCrossHostPortability", "provesProductionReadiness", "provesReleaseEligibility", "provesOverallHarnessCompletion"),
    },
}
REQUIRED_LOCAL_REFERENCE_EDGES = {
    "authority": {
        ("properties", "predecessorBinding"): "#/$defs/binding",
        ("properties", "programPlanBinding"): "#/$defs/binding",
        ("properties", "assessmentVocabulary"): "#/$defs/assessmentVocabulary",
        ("properties", "objectives", "items"): "#/$defs/objective",
        ("properties", "acceptanceCriteria", "items"): "#/$defs/acceptanceCriterion",
        ("properties", "verifications", "items"): "#/$defs/verification",
        ("properties", "evidence", "items"): "#/$defs/evidence",
        ("$defs", "assessmentVocabulary", "items"): "#/$defs/assessment",
        ("$defs", "objective", "properties", "acceptanceIds"): "#/$defs/stringList",
        ("$defs", "acceptanceCriterion", "oneOf", 0): "#/$defs/basicAcceptanceCriterion",
        ("$defs", "acceptanceCriterion", "oneOf", 1): "#/$defs/currentApplicabilityAcceptanceCriterion",
        ("$defs", "acceptanceCriterion", "oneOf", 2): "#/$defs/semanticProjectionAcceptanceCriterion",
        ("$defs", "acceptanceCriterion", "oneOf", 3): "#/$defs/graduationSubgatesAcceptanceCriterion",
        ("$defs", "basicAcceptanceCriterion", "properties", "assessment"): "#/$defs/assessment",
        ("$defs", "basicAcceptanceCriterion", "properties", "verificationIds"): "#/$defs/stringList",
        ("$defs", "basicAcceptanceCriterion", "properties", "evidenceIds"): "#/$defs/stringList",
        ("$defs", "currentApplicabilityAcceptanceCriterion", "properties", "assessment"): "#/$defs/assessment",
        ("$defs", "currentApplicabilityAcceptanceCriterion", "properties", "verificationIds"): "#/$defs/stringList",
        ("$defs", "currentApplicabilityAcceptanceCriterion", "properties", "evidenceIds"): "#/$defs/stringList",
        ("$defs", "semanticProjectionAcceptanceCriterion", "properties", "assessment"): "#/$defs/assessment",
        ("$defs", "semanticProjectionAcceptanceCriterion", "properties", "verificationIds"): "#/$defs/stringList",
        ("$defs", "semanticProjectionAcceptanceCriterion", "properties", "evidenceIds"): "#/$defs/stringList",
        ("$defs", "graduationSubgatesAcceptanceCriterion", "properties", "assessment"): "#/$defs/assessment",
        ("$defs", "graduationSubgatesAcceptanceCriterion", "properties", "verificationIds"): "#/$defs/stringList",
        ("$defs", "graduationSubgatesAcceptanceCriterion", "properties", "evidenceIds"): "#/$defs/stringList",
        ("$defs", "graduationSubgatesAcceptanceCriterion", "properties", "graduationSubgates", "items"): "#/$defs/graduationSubgate",
        ("$defs", "verification", "oneOf", 0): "#/$defs/verificationWithoutCommand",
        ("$defs", "verification", "oneOf", 1): "#/$defs/verificationWithCommand",
        ("$defs", "evidence", "properties", "supports"): "#/$defs/stringList",
    },
    "selector": {
        ("properties", "activeSnapshotBinding"): "#/$defs/binding",
        ("properties", "activeTransitionBinding"): "#/$defs/binding",
        ("properties", "programPlanBinding"): "#/$defs/binding",
        ("properties", "executionCounters"): "#/$defs/zeroExecutionCounters",
    },
    "receipt": {
        ("properties", "fromSnapshotBinding"): "#/$defs/binding",
        ("properties", "toSnapshotBinding"): "#/$defs/binding",
        ("properties", "fromProgramPlanBinding"): "#/$defs/binding",
        ("properties", "toProgramPlanBinding"): "#/$defs/binding",
        ("properties", "delta"): "#/$defs/delta",
        ("properties", "invariants"): "#/$defs/invariants",
        ("properties", "authorizationBoundary"): "#/$defs/authorizationBoundary",
        ("properties", "executionCounters"): "#/$defs/zeroExecutionCounters",
        ("properties", "claimBoundary"): "#/$defs/claimBoundary",
        ("$defs", "assessmentChange", "properties", "fromAssessment"): "#/$defs/assessment",
        ("$defs", "assessmentChange", "properties", "toAssessment"): "#/$defs/assessment",
        ("$defs", "delta", "properties", "criterionEvidenceLinksAdded", "items"): "#/$defs/criterionEvidenceLink",
        ("$defs", "delta", "properties", "criterionEvidenceLinksRemoved", "items"): "#/$defs/criterionEvidenceLink",
        ("$defs", "delta", "properties", "assessmentsChanged", "items"): "#/$defs/assessmentChange",
        ("$defs", "invariants", "properties", "acceptanceInventory"): "#/$defs/acceptanceInventory",
    },
    "inventory": {
        ("properties", "baselineObservation"): "#/$defs/baselineObservation",
        ("properties", "occurrences", "items"): "#/$defs/occurrence",
        ("properties", "claimBoundary"): "#/$defs/claimBoundary",
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


def schema_value_at(document: dict[str, object], path: tuple[str | int, ...]) -> object:
    value: object = document
    for part in path:
        if isinstance(value, dict) and isinstance(part, str):
            value = value[part]
        elif isinstance(value, list) and type(part) is int:
            value = value[part]
        else:
            raise AssertionError(f"Schema path is invalid: {'.'.join(map(str, path))}")
    return value


def assert_schema_declaration_contract(schemas: dict[str, dict[str, object]]) -> None:
    for schema_name, expected_records in NESTED_RECORD_FIELDS.items():
        definitions = schemas[schema_name]["$defs"]
        for record_name, expected_fields in expected_records.items():
            record = definitions[record_name]
            if record.get("type") != "object":
                raise AssertionError(f"{schema_name}.{record_name} is not an object record")
            if set(record.get("properties", ())) != set(expected_fields):
                raise AssertionError(f"{schema_name}.{record_name} property set drifted")
            if set(record.get("required", ())) != set(expected_fields):
                raise AssertionError(f"{schema_name}.{record_name} required set drifted")
            if record.get("additionalProperties") is not False:
                raise AssertionError(f"{schema_name}.{record_name} is not closed")

    for schema_name, expected_edges in REQUIRED_LOCAL_REFERENCE_EDGES.items():
        schema = schemas[schema_name]
        for path, expected_reference in expected_edges.items():
            value = schema_value_at(schema, path)
            if not isinstance(value, dict) or value.get("$ref") != expected_reference:
                raise AssertionError(
                    f"{schema_name}.{'.'.join(map(str, path))} reference drifted"
                )

    for schema_name in ("authority", "selector", "receipt"):
        branches = schemas[schema_name]["$defs"]["binding"].get("allOf")
        if not isinstance(branches, list) or len(branches) != 2:
            raise AssertionError(f"{schema_name}.binding generation branches drifted")
        v1 = branches[0]
        v2 = branches[1]
        if v1.get("if", {}).get("properties", {}).get("authoritySchema", {}).get("const") != 1:
            raise AssertionError(f"{schema_name}.binding v1 branch drifted")
        if v1.get("then", {}).get("properties", {}).get("generation") != {"type": "null"}:
            raise AssertionError(f"{schema_name}.binding v1 generation contract drifted")
        if v2.get("if", {}).get("properties", {}).get("authoritySchema", {}).get("const") != 2:
            raise AssertionError(f"{schema_name}.binding v2 branch drifted")
        if v2.get("then", {}).get("properties", {}).get("generation") != {"type": "integer", "minimum": 1}:
            raise AssertionError(f"{schema_name}.binding v2 generation contract drifted")


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

    def test_legacy_lock_drift_cannot_be_overridden(self) -> None:
        """Adding a digest override must not bypass the immutable legacy lock."""

        with tempfile.TemporaryDirectory() as directory:
            copied_root = Path(directory)
            for relative in (
                Path("registry/program-acceptance-map.json"),
                Path("registry/curation-program-plan.json"),
                Path("tests/fixtures/harness-decision-packet-gen-research-01.json"),
                Path("tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json"),
            ):
                destination = copied_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)

            acceptance = copied_root / "registry/program-acceptance-map.json"
            acceptance.write_bytes(acceptance.read_bytes() + b" ")
            with self.assertRaises(AcceptanceAuthorityError) as raised:
                validate_legacy_locks(copied_root)
            self.assertEqual("legacy-authority-drift", raised.exception.code)

            drifted_digest = hashlib.sha256(acceptance.read_bytes()).hexdigest()
            with self.assertRaises(TypeError):
                validate_legacy_locks(
                    copied_root,
                    expected={"acceptance": drifted_digest},
                )


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
        assert_schema_declaration_contract(schemas)
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

    def test_literal_contract_rejects_required_reference_and_minimum_mutations(self) -> None:
        """Weakening a required field, reference edge, or v2 minimum must fail this test."""

        for mutate in (
            lambda schemas: schemas["authority"]["$defs"]["objective"]["required"].remove(
                "acceptanceIds"
            ),
            lambda schemas: schemas["authority"]["$defs"]["objective"]["properties"].__setitem__(
                "acceptanceIds", copy.deepcopy(schemas["authority"]["$defs"]["stringList"])
            ),
            lambda schemas: schemas["authority"]["properties"].__setitem__(
                "predecessorBinding", copy.deepcopy(schemas["authority"]["$defs"]["binding"])
            ),
            lambda schemas: schemas["receipt"]["$defs"]["binding"]["allOf"][1]["then"][
                "properties"
            ]["generation"].pop("minimum"),
        ):
            with self.subTest(mutation=mutate):
                schemas = copy.deepcopy(self.load_schemas())
                mutate(schemas)
                with self.assertRaises(AssertionError):
                    assert_schema_declaration_contract(schemas)

    def test_reference_drift_at_array_index_raises_readable_assertion(self) -> None:
        """A reference drift at oneOf[0] must fail as a contract assertion."""

        schemas = copy.deepcopy(self.load_schemas())
        schemas["authority"]["$defs"]["acceptanceCriterion"]["oneOf"][0]["$ref"] = (
            "#/$defs/driftedAcceptanceCriterion"
        )

        try:
            assert_schema_declaration_contract(schemas)
        except Exception as error:
            raised = error
        else:
            self.fail("reference drift did not raise")

        self.assertIsInstance(raised, AssertionError)
        self.assertEqual(
            "authority.$defs.acceptanceCriterion.oneOf.0 reference drifted",
            str(raised),
        )


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


class ProgramAcceptanceAuthoritySnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.legacy = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        self.plan = json.loads(
            (ROOT / "registry/curation-program-plan.json").read_text(encoding="utf-8")
        )
        self.locks = validate_legacy_locks(ROOT)

    def build_g1(self) -> dict[str, object]:
        candidate_plan = build_candidate_program_plan_v2(self.plan)
        plan_binding = binding_for_bytes(
            authority_schema=2,
            authority_id="curation-program-plan-v2",
            generation=1,
            path="curation-program-plan-v2.json",
            data=canonical_file_bytes(candidate_plan),
        )
        return build_structural_snapshot_v2(
            self.legacy,
            predecessor_binding={
                **self.locks["acceptance"],
                "authoritySchema": 1,
                "generation": None,
            },
            program_plan_binding=plan_binding,
        )

    def test_g000001_is_business_semantics_equivalent_to_v1(self) -> None:
        """Changing g000001 business state or generation must fail this test."""

        g1 = self.build_g1()
        self.assertEqual(
            authority_business_projection(self.legacy), authority_business_projection(g1)
        )
        self.assertEqual(1, g1["generation"])

    def test_candidate_plan_changes_only_the_versioned_authority_relationship(self) -> None:
        """Changing a carried program-plan value must fail this exact structural migration test."""

        candidate = build_candidate_program_plan_v2(self.plan)
        expected = copy.deepcopy(self.plan)
        expected["schema"] = 2
        expected["id"] = "curation-program-plan-v2"
        expected["acceptanceAuthoritySelector"] = "program-acceptance-authority/current.json"
        del expected["acceptanceMap"]
        self.assertEqual(expected, candidate)

    def test_g000002_adds_only_manifest_evidence_and_reciprocal_link(self) -> None:
        """Adding unrelated state or promoting the target criterion must fail this test."""

        g1 = self.build_g1()
        g2 = build_evidence_snapshot_v2(g1)
        self.assertEqual(2, g2["generation"])
        self.assertEqual(len(g1["evidence"]) + 1, len(g2["evidence"]))
        criterion = next(
            row for row in g2["acceptanceCriteria"] if row["id"] == TARGET_CRITERION_ID
        )
        self.assertEqual("partial", criterion["assessment"])
        self.assertEqual({"verified": 46, "partial": 15, "planned": 0}, assessment_inventory(g2))

    def test_snapshot_validator_rejects_typed_authority_and_binding_drift(self) -> None:
        """Weak schema, generation, predecessor, or plan binding checks must fail closed."""

        g1 = self.build_g1()
        aliases = (
            ("schema", True, "acceptance-authority-schema-invalid"),
            ("schema", 1, "acceptance-authority-schema-invalid"),
            ("schema", 1.0, "acceptance-authority-schema-invalid"),
            ("generation", True, "acceptance-authority-generation-invalid"),
            ("generation", 1.0, "acceptance-authority-generation-invalid"),
        )
        for field, value, expected_code in aliases:
            with self.subTest(field=field, value=value):
                mutated = copy.deepcopy(g1)
                mutated[field] = value
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_authority_snapshot(
                        mutated,
                        predecessor=self.legacy,
                        program_plan_binding=g1["programPlanBinding"],
                    )
                self.assertEqual(expected_code, raised.exception.code)

        for mutate, expected_code in (
            (
                lambda snapshot: snapshot.__setitem__(
                    "authoritySeriesId", "wrong-authority-series"
                ),
                "acceptance-authority-series-invalid",
            ),
            (
                lambda snapshot: snapshot["predecessorBinding"].__setitem__(
                    "generation", 1
                ),
                "acceptance-authority-predecessor-mismatch",
            ),
            (
                lambda snapshot: snapshot["programPlanBinding"].__setitem__(
                    "sha256", "0" * 64
                ),
                "acceptance-program-plan-binding-drift",
            ),
        ):
            with self.subTest(mutation=mutate):
                mutated = copy.deepcopy(g1)
                mutate(mutated)
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_authority_snapshot(
                        mutated,
                        predecessor=self.legacy,
                        program_plan_binding=g1["programPlanBinding"],
                    )
                self.assertEqual(expected_code, raised.exception.code)

    def test_snapshot_validator_rejects_structural_and_evidence_delta_overreach(self) -> None:
        """Business changes outside the two named deltas must retain their typed boundary."""

        g1 = self.build_g1()
        g2 = build_evidence_snapshot_v2(g1)
        cases = (
            (
                g1,
                self.legacy,
                lambda snapshot: snapshot["acceptanceCriteria"][0].__setitem__(
                    "statement", "drifted structural statement"
                ),
                "acceptance-structural-migration-overreach",
            ),
            (
                g2,
                g1,
                lambda snapshot: snapshot["acceptanceCriteria"][0].__setitem__(
                    "statement", "drifted evidence registration statement"
                ),
                "acceptance-evidence-registration-overreach",
            ),
            (
                g2,
                g1,
                lambda snapshot: snapshot["acceptanceCriteria"].append(
                    copy.deepcopy(snapshot["acceptanceCriteria"][0])
                ),
                "acceptance-structural-migration-overreach",
            ),
        )
        for document, predecessor, mutate, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                mutated = copy.deepcopy(document)
                mutate(mutated)
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_authority_snapshot(
                        mutated,
                        predecessor=predecessor,
                        program_plan_binding=document["programPlanBinding"],
                    )
                self.assertEqual(expected_code, raised.exception.code)

    def test_evidence_registration_delta_rejects_nested_json_type_aliases(self) -> None:
        """Using Python equality here would accept true/1 and float aliases as no-op deltas."""

        g1 = self.build_g1()
        g2 = build_evidence_snapshot_v2(g1)
        auxiliary_criterion = next(
            row
            for row in g1["acceptanceCriteria"]
            if "currentApplicability" in row
        )
        cases = (
            (
                lambda before, after: (
                    before["objectives"][0].__setitem__("nonGoals", [True]),
                    after["objectives"][0].__setitem__("nonGoals", [1]),
                ),
                "acceptance-evidence-registration-overreach",
            ),
            (
                lambda before, after: (
                    before["evidence"][0].__setitem__("kind", True),
                    after["evidence"][0].__setitem__("kind", 1),
                ),
                "acceptance-evidence-source-drift",
            ),
            (
                lambda before, after: (
                    next(
                        row
                        for row in before["acceptanceCriteria"]
                        if row["id"] == auxiliary_criterion["id"]
                    ).__setitem__("currentApplicability", 1.0),
                    next(
                        row
                        for row in after["acceptanceCriteria"]
                        if row["id"] == auxiliary_criterion["id"]
                    ).__setitem__("currentApplicability", True),
                ),
                "acceptance-evidence-registration-overreach",
            ),
        )
        for mutate, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                before = copy.deepcopy(g1)
                after = copy.deepcopy(g2)
                mutate(before, after)
                after["predecessorBinding"] = binding_for_bytes(
                    authority_schema=2,
                    authority_id=before["id"],
                    generation=1,
                    path="snapshots/v2/g000001.json",
                    data=canonical_file_bytes(before),
                )
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_authority_snapshot(
                        after,
                        predecessor=before,
                        program_plan_binding=g1["programPlanBinding"],
                    )
                self.assertEqual(expected_code, raised.exception.code)

    def test_candidate_plan_rejects_boolean_schema_alias(self) -> None:
        """Treating JSON true as the legacy numeric schema must fail closed."""

        aliased_legacy = copy.deepcopy(self.plan)
        aliased_legacy["schema"] = True
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            build_candidate_program_plan_v2(aliased_legacy)
        self.assertEqual("acceptance-structural-migration-overreach", raised.exception.code)

    def test_snapshot_validator_rejects_inventory_and_evidence_integrity_drift(self) -> None:
        """Inventory aliases and asymmetric or altered manifest evidence must fail closed."""

        g1 = self.build_g1()
        g2 = build_evidence_snapshot_v2(g1)

        promoted = copy.deepcopy(g2)
        target = next(
            row for row in promoted["acceptanceCriteria"] if row["id"] == TARGET_CRITERION_ID
        )
        target["assessment"] = "verified"
        next(
            row
            for row in promoted["acceptanceCriteria"]
            if row["assessment"] == "verified" and row["id"] != TARGET_CRITERION_ID
        )["assessment"] = "partial"

        missing = copy.deepcopy(g2)
        missing["evidence"] = [
            row for row in missing["evidence"] if row["id"] != MANIFEST_EVIDENCE_ID
        ]
        missing_target = next(
            row for row in missing["acceptanceCriteria"] if row["id"] == TARGET_CRITERION_ID
        )
        missing_target["evidenceIds"].remove(MANIFEST_EVIDENCE_ID)

        drifted = copy.deepcopy(g2)
        next(
            row for row in drifted["evidence"] if row["id"] == MANIFEST_EVIDENCE_ID
        )["path"] = "registry/not-the-manifest.json"

        asymmetric = copy.deepcopy(g2)
        next(
            row for row in asymmetric["acceptanceCriteria"] if row["id"] == TARGET_CRITERION_ID
        )["evidenceIds"].remove(MANIFEST_EVIDENCE_ID)

        duplicate = copy.deepcopy(g2)
        duplicate["evidence"].append(copy.deepcopy(duplicate["evidence"][0]))

        inventory_aliases = []
        for value in (True, 1, 1.0):
            inventory_alias = copy.deepcopy(g1)
            inventory_alias["acceptanceCriteria"][0]["assessment"] = value
            inventory_aliases.append(inventory_alias)

        cases = (
            (promoted, "acceptance-assessment-promotion-forbidden"),
            (missing, "acceptance-evidence-source-missing"),
            (drifted, "acceptance-evidence-source-drift"),
            (asymmetric, "acceptance-evidence-link-asymmetric"),
            (duplicate, "acceptance-evidence-id-duplicate"),
            *(
                (inventory_alias, "acceptance-inventory-count-drift")
                for inventory_alias in inventory_aliases
            ),
        )
        for mutated, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_authority_snapshot(
                        mutated,
                        predecessor=(
                            self.legacy if mutated in inventory_aliases else g1
                        ),
                        program_plan_binding=g1["programPlanBinding"],
                    )
                self.assertEqual(expected_code, raised.exception.code)

    def test_checked_candidate_fixtures_replay_from_locked_v1_inputs(self) -> None:
        """Changing a builder result or checked bytes must fail this canonical replay test."""

        candidate = build_candidate_program_plan_v2(self.plan)
        g1 = self.build_g1()
        g2 = build_evidence_snapshot_v2(g1)
        expected = {
            FIXTURE_ROOT / "curation-program-plan-v2.json": candidate,
            FIXTURE_ROOT / "snapshots/v2/g000001.json": g1,
            FIXTURE_ROOT / "snapshots/v2/g000002.json": g2,
        }
        for path, document in expected.items():
            with self.subTest(path=path):
                self.assertEqual(canonical_file_bytes(document), path.read_bytes())
