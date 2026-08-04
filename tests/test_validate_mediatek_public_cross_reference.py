from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-mediatek-public-cross-reference.py"
SPEC = importlib.util.spec_from_file_location("validate_mediatek_public_cross_reference", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class MediatekPublicCrossReferenceValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = VALIDATOR.load_index(ROOT)
        cls.document = (ROOT / VALIDATOR.DOCUMENT_PATH).read_text(encoding="utf-8")

    def validate(self, index: dict) -> list[str]:
        return VALIDATOR.validate(ROOT, index=index, document=self.document)

    def test_repository_index_is_valid(self) -> None:
        self.assertEqual([], self.validate(copy.deepcopy(self.index)))

    def test_rejects_equivalence_claim(self) -> None:
        index = copy.deepcopy(self.index)
        index["matches"][0]["equivalenceClaimed"] = True
        errors = self.validate(index)
        self.assertTrue(any("equivalenceClaimed must be false" in error for error in errors))

    def test_rejects_unknown_match_source(self) -> None:
        index = copy.deepcopy(self.index)
        index["matches"][0]["sourceId"] = "missing-source"
        errors = self.validate(index)
        self.assertTrue(any("sourceId references unknown source" in error for error in errors))

    def test_rejects_hypothesis_without_falsifier(self) -> None:
        index = copy.deepcopy(self.index)
        index["hypotheses"][0]["falsifier"] = ""
        errors = self.validate(index)
        self.assertTrue(any(".falsifier must be non-empty" in error for error in errors))

    def test_rejects_missing_required_family_coverage(self) -> None:
        index = copy.deepcopy(self.index)
        for match in index["matches"]:
            match["targetFamilies"] = [
                family
                for family in match["targetFamilies"]
                if family not in {"mediatek.mfnrfeature", "MFNR/AIS"}
            ]
            if not match["targetFamilies"]:
                match["targetFamilies"] = ["other-family"]
        errors = self.validate(index)
        self.assertTrue(any("missing required family coverage" in error and "MFNR/AIS" in error for error in errors))

    def test_rejects_revision_url_without_sha(self) -> None:
        index = copy.deepcopy(self.index)
        index["sources"][0]["url"] = "https://chromium.googlesource.com/chromiumos/platform/camera/"
        errors = self.validate(index)
        self.assertTrue(any("url must include the pinned revision" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
