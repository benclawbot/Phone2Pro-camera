from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "research" / "build-aosp-camera-contract-reference.py"
CATALOG = ROOT / "research" / "contracts" / "android16-camera-contracts.json"
DOC = ROOT / "docs" / "research" / "AOSP_CAMERA_CONTRACT_REFERENCE.md"
SPEC = importlib.util.spec_from_file_location("build_aosp_camera_contract_reference", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuildAospCameraContractReferenceTest(unittest.TestCase):
    def catalog(self) -> dict:
        return MODULE.load_catalog(CATALOG)

    def test_catalog_is_android16_pinned_and_complete(self) -> None:
        report = MODULE.build_report(self.catalog())
        self.assertEqual(36, report["referencePlatform"]["apiLevel"])
        self.assertEqual(12, report["summary"]["contractCount"])
        for source_id in (
            "frameworks-base-android16",
            "frameworks-av-android16",
            "system-media-android16",
            "hardware-interfaces-android16",
        ):
            self.assertRegex(report["sources"][source_id]["revision"], r"^[0-9a-f]{40}$")

    def test_system_camera_target_behavior_is_conforming(self) -> None:
        report = MODULE.build_report(self.catalog())
        by_id = {item["id"]: item for item in report["contracts"]}
        comparison = by_id["system-cameras"]["targetComparison"]
        self.assertEqual("CONFORMING", comparison["state"])
        self.assertEqual("VERIFIED", comparison["classification"])
        symbols = {
            symbol
            for anchor in by_id["system-cameras"]["android16Anchors"]
            for symbol in anchor.get("symbols", [])
        }
        self.assertIn("shouldRejectSystemCameraConnection", symbols)
        self.assertIn("shouldSkipStatusUpdates", symbols)

    def test_optional_public_multicamera_absence_is_not_deviation(self) -> None:
        report = MODULE.build_report(self.catalog())
        by_id = {item["id"]: item for item in report["contracts"]}
        self.assertEqual("NOT_ADVERTISED", by_id["logical-multi-camera"]["targetComparison"]["state"])
        self.assertEqual("NOT_ADVERTISED", by_id["hidden-physical-id-query"]["targetComparison"]["state"])
        self.assertEqual([], report["summary"]["confirmedDeviationIds"])

    def test_vendor_and_session_contracts_keep_semantics_separate(self) -> None:
        report = MODULE.build_report(self.catalog())
        by_id = {item["id"]: item for item in report["contracts"]}
        self.assertEqual("OEM_EXTENSION", by_id["vendor-tags"]["targetComparison"]["state"])
        self.assertEqual("UNKNOWN", by_id["session-parameters"]["targetComparison"]["state"])
        self.assertIn("session-parameters", report["summary"]["unresolvedContractIds"])

    def test_rejects_unpinned_android16_source(self) -> None:
        catalog = copy.deepcopy(self.catalog())
        catalog["sources"]["frameworks-av-android16"]["revision"] = "android16-release"
        with self.assertRaises(MODULE.ContractCatalogError):
            MODULE.build_report(catalog)

    def test_render_includes_version_differences_and_target_states(self) -> None:
        markdown = MODULE.render_markdown(MODULE.build_report(self.catalog()))
        self.assertIn("No target deviation is currently confirmed", markdown)
        self.assertIn("Android 9 introduced public logical/physical multi-camera APIs", markdown)
        self.assertIn("Android 13 added AIDL camera HAL support", markdown)
        self.assertIn("`CONFORMING`", markdown)
        self.assertIn("`OEM_EXTENSION`", markdown)
        self.assertIn("shouldRejectSystemCameraConnection", markdown)
        self.assertIn("./SYSTEM_CAMERA_FILTERING_MODEL.md", markdown)
        self.assertNotIn("(docs/research/SYSTEM_CAMERA_FILTERING_MODEL.md)", markdown)

    def test_cli_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "contracts.json"
            markdown_path = root / "contracts.md"
            result = MODULE.main([
                str(CATALOG),
                "--json", str(json_path),
                "--markdown", str(markdown_path),
            ])
            data = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")
        self.assertEqual(0, result)
        self.assertEqual(12, data["summary"]["contractCount"])
        self.assertIn("Pinned Android 16 source revisions", markdown)

    def test_checked_in_markdown_matches_generator(self) -> None:
        expected = MODULE.render_markdown(MODULE.build_report(self.catalog()))
        self.assertEqual(expected, DOC.read_text(encoding="utf-8"))
        self.assertEqual(0, MODULE.main([str(CATALOG), "--check-markdown", str(DOC)]))


if __name__ == "__main__":
    unittest.main()
