from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-galaga-camera-hardware-map.py"
SPEC = importlib.util.spec_from_file_location("validate_galaga_camera_hardware_map", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class GalagaCameraHardwareMapValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hardware_map = VALIDATOR.load_map(ROOT)
        cls.document = (ROOT / VALIDATOR.DOCUMENT_PATH).read_text(encoding="utf-8")

    def validate(self, hardware_map: dict) -> list[str]:
        return VALIDATOR.validate(ROOT, hardware_map=hardware_map, document=self.document)

    def test_repository_map_is_valid(self) -> None:
        self.assertEqual([], self.validate(copy.deepcopy(self.hardware_map)))

    def test_rejects_confirmed_candidate_identity(self) -> None:
        hardware_map = copy.deepcopy(self.hardware_map)
        hardware_map["routes"][0]["shippedModuleIdentity"]["status"] = "CONFIRMED"
        errors = self.validate(hardware_map)
        self.assertTrue(any("shippedModuleIdentity must remain unresolved" in error for error in errors))

    def test_rejects_ois_claim(self) -> None:
        hardware_map = copy.deepcopy(self.hardware_map)
        hardware_map["routes"][1]["ois"]["confidence"] = "SOURCE_CONFIRMED_TOPOLOGY"
        errors = self.validate(hardware_map)
        self.assertTrue(any("ois must remain not evidenced" in error for error in errors))

    def test_rejects_duplicate_csi_port(self) -> None:
        hardware_map = copy.deepcopy(self.hardware_map)
        hardware_map["routes"][1]["csi"]["port"] = hardware_map["routes"][0]["csi"]["port"]
        errors = self.validate(hardware_map)
        self.assertTrue(any("csi.port must be unique" in error for error in errors))

    def test_rejects_unmapped_power_rail(self) -> None:
        hardware_map = copy.deepcopy(self.hardware_map)
        hardware_map["routes"][0]["power"]["avdd"] = "missing-rail"
        errors = self.validate(hardware_map)
        self.assertTrue(any("routes reference unmapped rails" in error for error in errors))

    def test_rejects_stable_device_node_claim(self) -> None:
        hardware_map = copy.deepcopy(self.hardware_map)
        hardware_map["kernelInterfaces"][0]["nodeStability"] = "FIXED_MINOR"
        errors = self.validate(hardware_map)
        self.assertTrue(any("must retain dynamic node enumeration" in error for error in errors))

    def test_rejects_missing_relevant_sensor_ioctl(self) -> None:
        hardware_map = copy.deepcopy(self.hardware_map)
        interface = next(item for item in hardware_map["kernelInterfaces"] if item["id"] == "imgsensor-v4l2-subdev")
        interface["privateIoctls"].remove("VIDIOC_MTK_G_HDR_CAP")
        errors = self.validate(hardware_map)
        self.assertTrue(any("sensor interface is missing ioctls" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
