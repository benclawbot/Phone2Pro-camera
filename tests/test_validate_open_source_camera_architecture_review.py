from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-open-source-camera-architecture-review.py"
SPEC = importlib.util.spec_from_file_location("validate_open_source_camera_architecture_review", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class OpenSourceCameraArchitectureReviewValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = VALIDATOR.load_index(ROOT)
        cls.document = (ROOT / VALIDATOR.DOCUMENT_PATH).read_text(encoding="utf-8")

    def validate(self, index: dict) -> list[str]:
        return VALIDATOR.validate(ROOT, index=index, document=self.document)

    def test_repository_review_is_valid(self) -> None:
        self.assertEqual([], self.validate(copy.deepcopy(self.index)))

    def test_rejects_gpl_direct_reuse(self) -> None:
        index = copy.deepcopy(self.index)
        project = next(item for item in index["projects"] if item["license"].startswith("GPL-"))
        project["reuseDecision"] = "DIRECT_REUSE_APPROVED"
        project["copiedCodeAllowed"] = True
        errors = self.validate(index)
        self.assertTrue(any("GPL project must be clean-room-only" in error for error in errors))

    def test_rejects_gpl_recommendation_with_direct_mode(self) -> None:
        index = copy.deepcopy(self.index)
        recommendation = next(
            item
            for item in index["recommendations"]
            if "motioncam" in item["sourceProjectIds"]
        )
        recommendation["implementationMode"] = "DIRECT_REUSE_OR_ADAPTATION"
        errors = self.validate(index)
        self.assertTrue(any("GPL-derived recommendation" in error for error in errors))

    def test_rejects_missing_coverage_domain(self) -> None:
        index = copy.deepcopy(self.index)
        del index["projects"][0]["coverage"]["GYRO"]
        errors = self.validate(index)
        self.assertTrue(any("coverage must define every domain" in error for error in errors))

    def test_rejects_unknown_recommendation_source(self) -> None:
        index = copy.deepcopy(self.index)
        index["recommendations"][0]["sourceProjectIds"] = ["missing-project"]
        errors = self.validate(index)
        self.assertTrue(any("references unknown projects" in error for error in errors))

    def test_rejects_missing_target_file(self) -> None:
        index = copy.deepcopy(self.index)
        index["recommendations"][0]["targetPaths"] = ["docs/does-not-exist.md"]
        errors = self.validate(index)
        self.assertTrue(any("references missing file" in error for error in errors))

    def test_rejects_unpinned_github_revision(self) -> None:
        index = copy.deepcopy(self.index)
        project = next(item for item in index["projects"] if item["revisionType"] == "GIT_COMMIT")
        project["revision"] = "main"
        errors = self.validate(index)
        self.assertTrue(any("40-character commit" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
