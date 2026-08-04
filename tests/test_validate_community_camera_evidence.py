from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-community-camera-evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_community_camera_evidence", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class CommunityCameraEvidenceValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = VALIDATOR.load_index(ROOT)
        cls.document = (ROOT / VALIDATOR.DOCUMENT_PATH).read_text(encoding="utf-8")

    def validate(self, index: dict) -> list[str]:
        return VALIDATOR.validate(ROOT, index=index, document=self.document)

    def test_repository_register_is_valid(self) -> None:
        self.assertEqual([], self.validate(copy.deepcopy(self.index)))

    def test_rejects_report_as_implementation_proof(self) -> None:
        index = copy.deepcopy(self.index)
        index["reports"][0]["implementationProof"] = True
        errors = self.validate(index)
        self.assertTrue(any("implementationProof must be false" in error for error in errors))

    def test_rejects_multiple_report_grade_without_corroboration(self) -> None:
        index = copy.deepcopy(self.index)
        report = next(item for item in index["reports"] if item["grade"] == "MULTIPLE_INDEPENDENT_REPORTS")
        report["independentCorroboration"] = False
        errors = self.validate(index)
        self.assertTrue(any("requires independent corroboration" in error for error in errors))

    def test_rejects_unknown_test_link(self) -> None:
        index = copy.deepcopy(self.index)
        index["reports"][0]["testIds"] = ["missing-test"]
        errors = self.validate(index)
        self.assertTrue(any("reports reference unknown tests" in error for error in errors))

    def test_rejects_unlinked_report(self) -> None:
        index = copy.deepcopy(self.index)
        report_id = index["reports"][0]["id"]
        for test in index["controlledTests"]:
            test["relatedReportIds"] = [item for item in test["relatedReportIds"] if item != report_id]
        errors = self.validate(index)
        self.assertTrue(any("reports without a reverse-linked controlled test" in error for error in errors))

    def test_rejects_exact_build_without_value(self) -> None:
        index = copy.deepcopy(self.index)
        source = next(item for item in index["sources"] if item["buildContext"]["status"] == "EXACT")
        source["buildContext"]["value"] = ""
        errors = self.validate(index)
        self.assertTrue(any("exact value is required" in error for error in errors))

    def test_rejects_non_https_source(self) -> None:
        index = copy.deepcopy(self.index)
        index["sources"][0]["url"] = "http://example.invalid/report"
        errors = self.validate(index)
        self.assertTrue(any("url must be an https URL" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
