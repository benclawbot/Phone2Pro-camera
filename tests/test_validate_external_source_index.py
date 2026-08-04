from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-external-source-index.py"
SPEC = importlib.util.spec_from_file_location("validate_external_source_index", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ExternalSourceIndexValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = VALIDATOR.load_index(ROOT)
        cls.document = (ROOT / VALIDATOR.DOCUMENT_PATH).read_text(encoding="utf-8")

    def validate(self, index: dict) -> list[str]:
        return VALIDATOR.validate(ROOT, index=index, document=self.document)

    def test_repository_index_is_valid(self) -> None:
        self.assertEqual([], self.validate(copy.deepcopy(self.index)))

    def test_rejects_duplicate_source_id(self) -> None:
        index = copy.deepcopy(self.index)
        index["sources"][1]["sourceId"] = index["sources"][0]["sourceId"]
        errors = self.validate(index)
        self.assertTrue(any("duplicate sourceId" in error for error in errors))

    def test_rejects_generic_git_url(self) -> None:
        index = copy.deepcopy(self.index)
        source = next(item for item in index["sources"] if item["locatorType"] == "GIT_COMMIT")
        source["url"] = "https://github.com/example/project"
        errors = self.validate(index)
        self.assertTrue(any("url must contain the exact commit" in error for error in errors))

    def test_rejects_community_implementation_proof(self) -> None:
        index = copy.deepcopy(self.index)
        source = next(item for item in index["sources"] if item["classification"] == "COMMUNITY_REPORT")
        source["implementationProof"] = True
        errors = self.validate(index)
        self.assertTrue(any("community source cannot be implementation proof" in error for error in errors))

    def test_rejects_missing_mismatch_notes(self) -> None:
        index = copy.deepcopy(self.index)
        source = next(item for item in index["sources"] if item["freshness"] == "BUILD_MISMATCH")
        source["mismatchNotes"] = None
        errors = self.validate(index)
        self.assertTrue(any("mismatchNotes is required" in error for error in errors))

    def test_rejects_unverified_ota_as_verified(self) -> None:
        index = copy.deepcopy(self.index)
        source = next(item for item in index["sources"] if item["sourceId"] == "oem-incremental-ota")
        source["artifactVerified"] = True
        errors = self.validate(index)
        self.assertTrue(any("cannot be marked verified" in error for error in errors))

    def test_rejects_missing_registry_record(self) -> None:
        index = copy.deepcopy(self.index)
        index["sources"] = [
            item
            for item in index["sources"]
            if item["sourceId"] != "androidx-camera-pipe"
        ]
        errors = self.validate(index)
        self.assertTrue(any("is missing indexed ids" in error and "androidx-camera-pipe" in error for error in errors))

    def test_rejects_locator_drift_from_registry(self) -> None:
        index = copy.deepcopy(self.index)
        source = next(item for item in index["sources"] if item["sourceId"] == "paper-hasinoff-hdrplus-2016")
        source["locatorValue"] = "2015"
        source["citationKey"] = "paper-hasinoff-hdrplus-2016@2015"
        errors = self.validate(index)
        self.assertTrue(any("paper locator must equal the registered publication year" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
