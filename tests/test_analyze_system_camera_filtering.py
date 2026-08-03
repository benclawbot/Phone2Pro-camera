from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "device" / "analyze-system-camera-filtering.py"
SPEC = importlib.util.spec_from_file_location("analyze_system_camera_filtering", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AnalyzeSystemCameraFilteringTest(unittest.TestCase):
    def fixture(self) -> dict:
        return {
            "wrapper": {
                "cameraOpen": {
                    "data": {
                        "publicCameraIds": ["0", "1"],
                        "probes": [
                            {
                                "cameraId": "0",
                                "publiclyListed": True,
                                "characteristicsReadable": True,
                                "openOutcome": "opened",
                            },
                            {
                                "cameraId": "2",
                                "publiclyListed": False,
                                "characteristicsReadable": False,
                                "characteristicsError": {
                                    "message": "CAMERA_ERROR (3): getCameraCharacteristics: Unable to retrieve cameracharacteristics for system only device 2: "
                                },
                                "openOutcome": "exception",
                                "openError": {
                                    "message": "CAMERA_ERROR (3): getCameraCharacteristics: Unable to retrieve cameracharacteristics for system only device 2: "
                                },
                            },
                            {
                                "cameraId": "6",
                                "publiclyListed": False,
                                "characteristicsReadable": False,
                                "characteristicsError": {
                                    "message": "Unable to retrieve camera characteristics for unknown device 6"
                                },
                                "openOutcome": "exception",
                                "openError": {
                                    "message": "Unable to retrieve camera characteristics for unknown device 6"
                                },
                            },
                        ],
                    }
                }
            }
        }

    def test_separates_enumeration_characteristics_and_connect(self) -> None:
        report = MODULE.build_report(self.fixture())
        by_id = {item["cameraId"]: item for item in report["probes"]}
        self.assertEqual("PUBLIC", by_id["0"]["deviceKind"])
        self.assertEqual("SYSTEM_ONLY_CAMERA", by_id["2"]["deviceKind"])
        self.assertEqual("NOT_PUBLICLY_LISTED", by_id["2"]["enumeration"]["state"])
        self.assertEqual("SYSTEM_ONLY_REJECTED", by_id["2"]["characteristics"]["state"])
        self.assertEqual("BLOCKED_BY_CHARACTERISTICS_PREFLIGHT", by_id["2"]["open"]["state"])
        self.assertFalse(by_id["2"]["open"]["connectIndependentlyReached"])
        self.assertEqual("UNKNOWN_DEVICE", by_id["6"]["deviceKind"])

    def test_classifies_direct_connect_rejection_separately(self) -> None:
        document = self.fixture()
        probe = document["wrapper"]["cameraOpen"]["data"]["probes"][1]
        probe["openError"]["message"] = 'No camera device with ID "2" is available'
        report = MODULE.build_report(document)
        item = next(item for item in report["probes"] if item["cameraId"] == "2")
        self.assertEqual("CONNECT_REJECTED", item["open"]["state"])
        self.assertTrue(item["open"]["connectIndependentlyReached"])

    def test_finds_nested_camera_open_object(self) -> None:
        data, path = MODULE.find_camera_open(self.fixture())
        self.assertEqual(("wrapper", "cameraOpen", "data"), path)
        self.assertEqual(["0", "1"], data["publicCameraIds"])

    def test_rejects_document_without_probes(self) -> None:
        with self.assertRaises(MODULE.AnalysisError):
            MODULE.build_report({"publicCameraIds": ["0"]})

    def test_cli_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            json_out = root / "report.json"
            md_out = root / "report.md"
            source.write_text(json.dumps(self.fixture()), encoding="utf-8")
            result = MODULE.main([
                str(source), "--json", str(json_out), "--markdown", str(md_out)
            ])
            report = json.loads(json_out.read_text(encoding="utf-8"))
            markdown = md_out.read_text(encoding="utf-8")
        self.assertEqual(0, result)
        self.assertEqual(["2"], report["summary"]["systemOnlyCameraIds"])
        self.assertIn("BLOCKED_BY_CHARACTERISTICS_PREFLIGHT", markdown)


if __name__ == "__main__":
    unittest.main()
