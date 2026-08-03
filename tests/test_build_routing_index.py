from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "apk" / "build-routing-index.py"
SPEC = importlib.util.spec_from_file_location("build_routing_index", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuildRoutingIndexTest(unittest.TestCase):
    def test_ranks_ui_to_session_vendor_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run = root / "20260803T120000Z"
            source = run / "jadx" / "sources" / "com" / "nothing" / "camera"
            source.mkdir(parents=True)
            (source / "ExpertController.java").write_text(
                """package com.nothing.camera;
                class ExpertController {
                    void onLensButton() {
                        String route = "0.6x";
                        cameraManager.openCamera(cameraId, callback, handler);
                        sessionConfiguration.setSessionParameters(request);
                        request.set(KEY_SENSOR, "com.mediatek.seamlessfeature.sensorScenario");
                    }
                }
                """,
                encoding="utf-8",
            )
            (source / "Utility.java").write_text(
                'package com.nothing.camera; class Utility { String widget = "widget"; }',
                encoding="utf-8",
            )

            report = MODULE.build_report(root)
            self.assertEqual(report["matchedFileCount"], 2)
            self.assertTrue(report["routeCandidateFiles"])
            top = report["files"][0]
            self.assertEqual(top["identity"]["className"], "ExpertController")
            self.assertIn("expert-ui", top["signalIds"])
            self.assertIn("camera-id-routing", top["signalIds"])
            self.assertIn("vendor-routing-key", top["signalIds"])
            self.assertGreater(top["bridgeBonus"], 0)

    def test_selects_latest_analysis_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            old = root / "20260801"
            new = root / "20260802"
            (old / "jadx").mkdir(parents=True)
            (new / "jadx").mkdir(parents=True)
            self.assertEqual(MODULE.find_analysis_root(root), new)


if __name__ == "__main__":
    unittest.main()
