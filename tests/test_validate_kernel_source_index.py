import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate-kernel-source-index.py"
SPEC = importlib.util.spec_from_file_location("validate_kernel_source_index", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class KernelSourceIndexValidatorTest(unittest.TestCase):
    def index(self):
        return MODULE.load_index(ROOT)

    def document(self):
        return (ROOT / "docs" / "GALAGA_KERNEL_SOURCE_REFERENCE.md").read_text(
            encoding="utf-8"
        )

    def test_committed_index_is_valid(self):
        self.assertEqual([], MODULE.validate(ROOT, self.index(), self.document()))

    def test_repository_commit_must_be_full_sha(self):
        index = self.index()
        index["repositories"][0]["commit"] = "6bed54e"
        errors = MODULE.validate(ROOT, index, self.document())
        self.assertTrue(any("40-character SHA" in error for error in errors))

    def test_known_build_mismatch_cannot_be_marked_exact(self):
        index = self.index()
        index["officialSourceRelease"]["relationToObservedFirmware"] = "EXACT_BUILD_MATCH"
        errors = MODULE.validate(ROOT, index, self.document())
        self.assertTrue(any("exact build match" in error or "mismatch" in error for error in errors))

    def test_duplicate_source_paths_are_rejected(self):
        index = self.index()
        duplicate = copy.deepcopy(index["cameraSources"][0])
        duplicate["id"] = "duplicate-source-id"
        index["cameraSources"].append(duplicate)
        errors = MODULE.validate(ROOT, index, self.document())
        self.assertTrue(any("duplicate indexed source path" in error for error in errors))

    def test_missing_userspace_item_requires_issue_links(self):
        index = self.index()
        index["missingUserspaceAndFirmware"][0]["unknownIssues"] = []
        errors = MODULE.validate(ROOT, index, self.document())
        self.assertTrue(any("must link active unknown issues" in error for error in errors))

    def test_document_must_include_every_source_id(self):
        document = self.document().replace("`galaga-camera-device-tree`", "`removed-source`", 1)
        errors = MODULE.validate(ROOT, self.index(), document)
        self.assertTrue(any("document is missing camera source id galaga-camera-device-tree" in error for error in errors))

    def test_non_official_owner_is_rejected(self):
        index = self.index()
        index["repositories"][0]["owner"] = "ExampleOrg"
        errors = MODULE.validate(ROOT, index, self.document())
        self.assertTrue(any("owner must be NothingOSS" in error for error in errors))

    def test_duplicate_repository_ids_are_rejected(self):
        index = self.index()
        duplicate = copy.deepcopy(index["repositories"][0])
        duplicate["repository"] = "android_kernel_modules_nothing_mt6878"
        index["repositories"].append(duplicate)
        errors = MODULE.validate(ROOT, index, self.document())
        self.assertTrue(any("repositories must contain" in error or "duplicate repository id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
