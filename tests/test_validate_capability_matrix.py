import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate-capability-matrix.py"
SPEC = importlib.util.spec_from_file_location("validate_capability_matrix", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CapabilityMatrixValidatorTest(unittest.TestCase):
    def matrix(self):
        return MODULE.load_matrix(ROOT)

    def test_committed_matrix_is_valid(self):
        self.assertEqual([], MODULE.validate(ROOT, self.matrix()))

    def test_duplicate_row_ids_are_rejected(self):
        matrix = self.matrix()
        matrix["rows"].append(copy.deepcopy(matrix["rows"][0]))
        errors = MODULE.validate(ROOT, matrix)
        self.assertTrue(any("duplicate row id" in error for error in errors))

    def test_unresolved_rows_require_active_issue_links(self):
        matrix = self.matrix()
        matrix["rows"][1]["unknownIssues"] = []
        errors = MODULE.validate(ROOT, matrix)
        self.assertTrue(any("requires unknownIssues" in error for error in errors))

    def test_inaccessible_capability_cannot_be_enabled(self):
        matrix = self.matrix()
        matrix["rows"][1]["replacementUse"] = "ENABLED"
        errors = MODULE.validate(ROOT, matrix)
        self.assertTrue(any("cannot be ENABLED" in error for error in errors))

    def test_missing_repository_evidence_is_rejected(self):
        matrix = self.matrix()
        matrix["rows"][0]["evidence"] = ["does/not/exist.md"]
        errors = MODULE.validate(ROOT, matrix)
        self.assertTrue(any("path does not exist" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
