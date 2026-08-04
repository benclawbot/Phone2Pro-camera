import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate-platform-spec.py"
SPEC = importlib.util.spec_from_file_location("validate_platform_spec", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PlatformSpecValidatorTest(unittest.TestCase):
    def manifest(self):
        return MODULE.load_manifest(ROOT)

    def document(self):
        return (
            ROOT / "docs" / "CMF_PHONE_2_PRO_CAMERA_PLATFORM_SPEC.md"
        ).read_text(encoding="utf-8")

    def test_committed_platform_spec_is_valid(self):
        self.assertEqual([], MODULE.validate(ROOT, self.manifest(), self.document()))

    def test_unknown_claim_cannot_be_enabled(self):
        manifest = self.manifest()
        claim = next(claim for claim in manifest["claims"] if claim["id"] == "C-API-003")
        claim["implementationUse"] = "ENABLED"
        errors = MODULE.validate(ROOT, manifest, self.document())
        self.assertTrue(any("unresolved claim cannot be enabled" in error for error in errors))

    def test_unresolved_claim_requires_issue_links(self):
        manifest = self.manifest()
        claim = next(claim for claim in manifest["claims"] if claim["id"] == "C-FW-002")
        claim["unknownIssues"] = []
        errors = MODULE.validate(ROOT, manifest, self.document())
        self.assertTrue(any("unresolved confidence requires unknownIssues" in error for error in errors))

    def test_missing_evidence_path_is_rejected(self):
        manifest = self.manifest()
        manifest["claims"][0]["evidence"] = ["missing/evidence.json"]
        errors = MODULE.validate(ROOT, manifest, self.document())
        self.assertTrue(any("path does not exist" in error for error in errors))

    def test_decision_must_reference_existing_claim(self):
        manifest = self.manifest()
        manifest["decisions"][0]["rationaleClaims"] = ["C-MISSING-001"]
        errors = MODULE.validate(ROOT, manifest, self.document())
        self.assertTrue(any("references unknown claim" in error for error in errors))

    def test_document_must_include_every_claim_id(self):
        document = self.document().replace("C-HW-001", "REMOVED-CLAIM", 1)
        errors = MODULE.validate(ROOT, self.manifest(), document)
        self.assertTrue(any("document is missing claim id C-HW-001" in error for error in errors))

    def test_duplicate_claim_ids_are_rejected(self):
        manifest = self.manifest()
        manifest["claims"].append(copy.deepcopy(manifest["claims"][0]))
        errors = MODULE.validate(ROOT, manifest, self.document())
        self.assertTrue(any("duplicate claim id" in error for error in errors))

    def test_required_section_coverage_is_enforced(self):
        manifest = self.manifest()
        manifest["claims"] = [
            claim for claim in manifest["claims"] if claim["section"] != "firmware"
        ]
        errors = MODULE.validate(ROOT, manifest, self.document())
        self.assertTrue(any("claims do not cover required sections" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
