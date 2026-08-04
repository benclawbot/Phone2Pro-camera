from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "research" / "build-camera-privilege-boundary.py"
MODEL = ROOT / "research" / "boundaries" / "galaga-camera-privilege-boundaries.json"
DOC = ROOT / "docs" / "research" / "CAMERA_PRIVILEGE_BOUNDARY.md"
SPEC = importlib.util.spec_from_file_location("build_camera_privilege_boundary", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuildCameraPrivilegeBoundaryTest(unittest.TestCase):
    def model(self) -> dict:
        return MODULE.load_model(MODEL)

    def test_default_model_contains_all_required_access_classes(self) -> None:
        report = MODULE.build_report(self.model())
        self.assertEqual(
            MODULE.ACCESS_CLASSES,
            set(report["summary"]["byAccessClass"]),
        )
        self.assertGreaterEqual(report["summary"]["featureCount"], 10)

    def test_auxiliary_routes_preserve_observed_camera_service_boundary(self) -> None:
        report = MODULE.build_report(self.model())
        by_id = {item["id"]: item for item in report["features"]}
        for feature_id in ("direct-ultrawide", "direct-telephoto"):
            feature = by_id[feature_id]
            self.assertEqual("PRIVILEGED", feature["accessClass"])
            self.assertEqual(
                "CAMERA_SERVICE_ENUMERATION",
                feature["firstBoundary"]["layer"],
            )
            self.assertEqual("FILTERED", feature["firstBoundary"]["state"])
            self.assertEqual("VERIFIED", feature["firstBoundary"]["classification"])
            self.assertEqual(
                "CAMERA_SERVICE_CHARACTERISTICS",
                feature["hardRejection"]["layer"],
            )
            self.assertEqual("REJECTED", feature["hardRejection"]["state"])

    def test_vendor_and_isp_routes_remain_unknown(self) -> None:
        report = MODULE.build_report(self.model())
        by_id = {item["id"]: item for item in report["features"]}
        self.assertEqual(
            "UNKNOWN",
            by_id["public-id-vendor-routing"]["firstBoundary"]["classification"],
        )
        self.assertEqual(
            "UNKNOWN",
            by_id["isp-tuning-controls"]["firstBoundary"]["classification"],
        )
        self.assertIn("public-id-vendor-routing", report["summary"]["unresolvedFeatureIds"])

    def test_rejects_missing_evidence_reference(self) -> None:
        model = copy.deepcopy(self.model())
        model["features"][0]["evidence"] = ["does-not-exist"]
        with self.assertRaises(MODULE.BoundaryModelError):
            MODULE.build_report(model)

    def test_render_contains_diagrams_consequences_and_links(self) -> None:
        markdown = MODULE.render_markdown(MODULE.build_report(self.model()))
        self.assertGreaterEqual(markdown.count("```mermaid"), 2)
        self.assertIn("Direct ultrawide endpoint", markdown)
        self.assertIn("CAMERA_SERVICE_ENUMERATION", markdown)
        self.assertIn("CAMERA_SERVICE_CHARACTERISTICS", markdown)
        self.assertIn("Keep the Galaga auxiliary backend fail-closed", markdown)
        self.assertIn("./GALAGA_EXPERT_DIRECT_ROUTE.md", markdown)
        self.assertIn("Ordinary public application", markdown)

    def test_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "boundary.json"
            markdown_path = root / "boundary.md"
            result = MODULE.main([
                str(MODEL),
                "--json", str(json_path),
                "--markdown", str(markdown_path),
            ])
            data = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")
        self.assertEqual(0, result)
        self.assertEqual(1, data["schemaVersion"])
        self.assertIn("Feature-to-boundary diagram", markdown)

    def test_checked_in_markdown_matches_generator(self) -> None:
        expected = MODULE.render_markdown(MODULE.build_report(self.model()))
        self.assertEqual(expected, DOC.read_text(encoding="utf-8"))
        self.assertEqual(0, MODULE.main([str(MODEL), "--check-markdown", str(DOC)]))


if __name__ == "__main__":
    unittest.main()
