import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate-sdk-guide.py"
SPEC = importlib.util.spec_from_file_location("validate_sdk_guide", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SdkGuideValidatorTest(unittest.TestCase):
    def manifest(self):
        return MODULE.load_manifest(ROOT)

    def guide(self):
        return (ROOT / "docs" / "REPLACEMENT_CAMERA_SDK.md").read_text(encoding="utf-8")

    def test_committed_guide_is_valid(self):
        self.assertEqual([], MODULE.validate(ROOT, self.manifest(), self.guide()))

    def test_experimental_module_must_remain_disabled(self):
        manifest = self.manifest()
        vendor = next(module for module in manifest["modules"] if module["id"] == "vendor-adapter")
        vendor["productionUse"] = "ENABLED_WITH_FALLBACK"
        errors = MODULE.validate(ROOT, manifest, self.guide())
        self.assertTrue(any("experimental adapter must be DISABLED" in error for error in errors))

    def test_verified_example_cannot_use_experimental_module(self):
        manifest = self.manifest()
        verified = next(
            example for example in manifest["examples"] if example["id"] == "public-main-session"
        )
        verified["usesModules"].append("vendor-adapter")
        errors = MODULE.validate(ROOT, manifest, self.guide())
        self.assertTrue(any("verified example cannot use" in error for error in errors))

    def test_missing_entry_point_is_rejected(self):
        manifest = self.manifest()
        manifest["modules"][0]["entryPoints"] = ["missing/Backend.java"]
        errors = MODULE.validate(ROOT, manifest, self.guide())
        self.assertTrue(any("path does not exist" in error for error in errors))

    def test_experimental_example_requires_issue_links(self):
        manifest = self.manifest()
        experimental = next(
            example for example in manifest["examples"] if example["id"] == "vendor-feature-probe"
        )
        experimental["unknownIssues"] = []
        errors = MODULE.validate(ROOT, manifest, self.guide())
        self.assertTrue(any("experimental example requires unknownIssues" in error for error in errors))

    def test_missing_guide_anchor_is_rejected(self):
        manifest = self.manifest()
        manifest["examples"][0]["guideAnchor"] = "missing-anchor"
        errors = MODULE.validate(ROOT, manifest, self.guide())
        self.assertTrue(any("is missing from the guide" in error for error in errors))

    def test_duplicate_modules_are_rejected(self):
        manifest = self.manifest()
        manifest["modules"].append(copy.deepcopy(manifest["modules"][0]))
        errors = MODULE.validate(ROOT, manifest, self.guide())
        self.assertTrue(any("duplicate module id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
