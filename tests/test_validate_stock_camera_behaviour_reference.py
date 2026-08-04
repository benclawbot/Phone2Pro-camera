from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "tools" / "validate-stock-camera-behaviour-reference.py"
SPEC = importlib.util.spec_from_file_location("stock_reference_validator", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StockCameraBehaviourReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = MODULE.load_reference(ROOT)

    def validate(self, value) -> None:
        MODULE.validate_reference(value, ROOT)

    def test_reference_validates(self) -> None:
        self.validate(self.reference)

    def test_missing_mode_is_rejected(self) -> None:
        value = copy.deepcopy(self.reference)
        value["modes"] = [m for m in value["modes"] if m["id"] != "video"]
        with self.assertRaisesRegex(ValueError, "five required modes"):
            self.validate(value)

    def test_expert_route_drift_is_rejected(self) -> None:
        value = copy.deepcopy(self.reference)
        expert = next(m for m in value["modes"] if m["id"] == "expert")
        expert["routes"][0]["endpoint"] = 0
        with self.assertRaisesRegex(ValueError, "route table drift"):
            self.validate(value)

    def test_inference_cannot_be_verified(self) -> None:
        value = copy.deepcopy(self.reference)
        photo = next(m for m in value["modes"] if m["id"] == "photo")
        photo["inferredClaims"][0]["class"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "inference cannot be VERIFIED"):
            self.validate(value)

    def test_night_diagnostic_must_remain_non_stock(self) -> None:
        value = copy.deepcopy(self.reference)
        night = next(m for m in value["modes"] if m["id"] == "night")
        night["observedClaims"][0].pop("nonStock")
        with self.assertRaisesRegex(ValueError, "Night diagnostic"):
            self.validate(value)

    def test_unknown_latency_cannot_contain_estimate(self) -> None:
        value = copy.deepcopy(self.reference)
        video = next(m for m in value["modes"] if m["id"] == "video")
        video["latency"]["metrics"]["recordStartMs"] = 500
        with self.assertRaisesRegex(ValueError, "unknown latency"):
            self.validate(value)


if __name__ == "__main__":
    unittest.main()
