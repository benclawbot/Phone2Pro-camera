from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/validate-firmware-camera-interface-reference.py"
SPEC = importlib.util.spec_from_file_location("firmware_interface_validator", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FirmwareCameraInterfaceReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference = MODULE.load_reference(ROOT)

    def test_repository_reference_is_valid(self) -> None:
        MODULE.validate_reference(self.reference, ROOT)

    def test_duplicate_interface_id_is_rejected(self) -> None:
        value = copy.deepcopy(self.reference)
        value["interfaces"].append(copy.deepcopy(value["interfaces"][0]))
        with self.assertRaisesRegex(MODULE.ValidationError, "duplicate interface id"):
            MODULE.validate_reference(value, ROOT, check_paths=False)

    def test_unknown_interface_cannot_be_non_opaque(self) -> None:
        value = copy.deepcopy(self.reference)
        item = next(
            interface
            for interface in value["interfaces"]
            if interface["confidence"] == "UNKNOWN"
        )
        item["opaqueBoundary"] = False
        with self.assertRaisesRegex(MODULE.ValidationError, "UNKNOWN interfaces must be opaque"):
            MODULE.validate_reference(value, ROOT, check_paths=False)

    def test_category_gap_is_rejected(self) -> None:
        value = copy.deepcopy(self.reference)
        value["interfaces"] = [
            interface
            for interface in value["interfaces"]
            if interface["category"] != "SELINUX"
        ]
        with self.assertRaisesRegex(MODULE.ValidationError, "do not cover categories"):
            MODULE.validate_reference(value, ROOT, check_paths=False)

    def test_build_mismatch_cannot_be_erased(self) -> None:
        value = copy.deepcopy(self.reference)
        value["sourceReleaseScope"]["relationship"] = "EXACT_MATCH"
        with self.assertRaisesRegex(MODULE.ValidationError, "retain the build mismatch"):
            MODULE.validate_reference(value, ROOT, check_paths=False)

    def test_evidence_paths_are_checked(self) -> None:
        value = copy.deepcopy(self.reference)
        value["evidenceRegistry"]["build-matrix"]["path"] = "missing/evidence.json"
        with self.assertRaisesRegex(MODULE.ValidationError, "does not exist"):
            MODULE.validate_reference(value, ROOT)


if __name__ == "__main__":
    unittest.main()
