from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-computational-photography-literature.py"
SPEC = importlib.util.spec_from_file_location("validate_computational_photography_literature", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ComputationalPhotographyLiteratureValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = VALIDATOR.load_index(ROOT)
        cls.document = (ROOT / VALIDATOR.DOCUMENT_PATH).read_text(encoding="utf-8")

    def validate(self, index: dict) -> list[str]:
        return VALIDATOR.validate(ROOT, index=index, document=self.document)

    def test_repository_register_is_valid(self) -> None:
        self.assertEqual([], self.validate(copy.deepcopy(self.index)))

    def test_rejects_method_without_assumptions(self) -> None:
        index = copy.deepcopy(self.index)
        index["methods"][0]["assumptions"] = []
        errors = self.validate(index)
        self.assertTrue(any(".assumptions must be a non-empty" in error for error in errors))

    def test_rejects_unknown_paper_link(self) -> None:
        index = copy.deepcopy(self.index)
        index["methods"][0]["paperIds"] = ["missing-paper"]
        errors = self.validate(index)
        self.assertTrue(any("paperIds references unknown papers" in error for error in errors))

    def test_rejects_high_cost_method_in_quick(self) -> None:
        index = copy.deepcopy(self.index)
        method = next(item for item in index["methods"] if item["id"] == "method-kpn-burst-denoising")
        method["modeAssignments"] = ["QUICK", "MAX_DETAIL"]
        errors = self.validate(index)
        self.assertTrue(any("cannot be assigned to QUICK" in error for error in errors))

    def test_rejects_method_without_target_benchmark(self) -> None:
        index = copy.deepcopy(self.index)
        index["methods"][0]["benchmarkIds"] = ["benchmark-hdrplus-burst"]
        errors = self.validate(index)
        self.assertTrue(any("must include benchmark-galaga-controlled" in error for error in errors))

    def test_rejects_unpinned_implementation(self) -> None:
        index = copy.deepcopy(self.index)
        index["implementations"][0]["revision"] = "main"
        errors = self.validate(index)
        self.assertTrue(any("40-character commit" in error for error in errors))

    def test_rejects_missing_scope_contract(self) -> None:
        index = copy.deepcopy(self.index)
        index["scope"]["alignmentContract"] = "docs/architecture/missing.md"
        errors = self.validate(index)
        self.assertTrue(any("scope.alignmentContract must reference an existing file" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
