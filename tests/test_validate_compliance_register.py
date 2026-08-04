import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate-compliance-register.py"
SPEC = importlib.util.spec_from_file_location("validate_compliance_register", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ComplianceRegisterValidatorTest(unittest.TestCase):
    def register(self):
        return MODULE.load_register(ROOT)

    def document(self):
        return (ROOT / "docs" / "SOURCE_LICENCE_COMPLIANCE.md").read_text(
            encoding="utf-8"
        )

    def test_committed_register_is_valid(self):
        self.assertEqual([], MODULE.validate(ROOT, self.register(), self.document()))

    def test_removed_direct_dependency_is_detected(self):
        register = self.register()
        register["dependencies"] = [
            dependency
            for dependency in register["dependencies"]
            if dependency["id"] != "androidx-activity"
        ]
        errors = MODULE.validate(ROOT, register, self.document())
        self.assertTrue(any("unregistered Gradle dependency declaration" in error for error in errors))

    def test_unpinned_dependency_requires_release_review(self):
        register = self.register()
        dependency = next(
            dependency
            for dependency in register["dependencies"]
            if dependency["id"] == "python-jsonschema"
        )
        dependency["reviewStatus"] = "RECORDED"
        errors = MODULE.validate(ROOT, register, self.document())
        self.assertTrue(any("unpinned dependency requires release review" in error for error in errors))

    def test_restricted_artifact_cannot_be_allowed(self):
        register = self.register()
        artifact = next(
            artifact
            for artifact in register["controlledArtifacts"]
            if artifact["id"] == "stock-camera-apk-and-splits"
        )
        artifact["redistribution"] = "ALLOWED"
        errors = MODULE.validate(ROOT, register, self.document())
        self.assertTrue(any("restricted artifact cannot be marked ALLOWED" in error for error in errors))

    def test_clean_room_sections_must_be_substantive(self):
        register = self.register()
        register["cleanRoomBoundary"]["copyingProhibited"] = ["Do not copy."]
        errors = MODULE.validate(ROOT, register, self.document())
        self.assertTrue(any("copyingProhibited" in error for error in errors))

    def test_document_must_list_every_dependency(self):
        document = self.document().replace("`junit4`", "`missing-junit`", 1)
        errors = MODULE.validate(ROOT, self.register(), document)
        self.assertTrue(any("document is missing dependency id junit4" in error for error in errors))

    def test_invalid_patent_status_is_rejected(self):
        register = self.register()
        register["patentSensitiveAreas"][0]["status"] = "CLEARED_WITHOUT_REVIEW"
        errors = MODULE.validate(ROOT, register, self.document())
        self.assertTrue(any("patentSensitiveAreas[0].status is invalid" in error for error in errors))

    def test_duplicate_dependency_ids_are_rejected(self):
        register = self.register()
        register["dependencies"].append(copy.deepcopy(register["dependencies"][0]))
        errors = MODULE.validate(ROOT, register, self.document())
        self.assertTrue(any("duplicate dependency id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
