from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "trace" / "analyze-expert-routing-bundles.py"
SPEC = importlib.util.spec_from_file_location("analyze_expert_routing_bundles", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

OPTICS = {
    "06x": (1.64, 15, 3264, 2448),
    "1x": (5.56, 24, 4080, 3072),
    "2x": (7.10, 50, 4096, 3072),
}


class AnalyzeExpertRoutingBundlesTest(unittest.TestCase):
    def write_bundle(
        self,
        root: Path,
        route: str,
        mode: str,
        events: list[dict],
        *,
        open_id: str | None = None,
    ) -> Path:
        directory = root / f"20260803T120000Z-{route}-{mode}"
        directory.mkdir(parents=True)
        (directory / "run-metadata.json").write_text(
            json.dumps(
                {
                    "route": route,
                    "traceMode": mode,
                    "createdAtUtc": "2026-08-03T12:00:00Z",
                }
            ),
            encoding="utf-8",
        )

        focal, equivalent, width, height = OPTICS[route]
        (directory / "output-association-template.json").write_text(
            json.dumps(
                {
                    "capture": {
                        "focalLengthMm": focal,
                        "focalLength35mmEquivalent": equivalent,
                        "width": width,
                        "height": height,
                    },
                    "validation": {"matchesAssignedOpticalRoute": True},
                }
            ),
            encoding="utf-8",
        )

        trace_events = list(events)
        if open_id is not None:
            trace_events.insert(0, {"kind": "open-camera", "cameraId": open_id})
        (directory / "frida.log").write_text(
            "\n".join(json.dumps(event) for event in trace_events) + "\n",
            encoding="utf-8",
        )
        (directory / "package-dumpsys-after.txt").write_text(
            "android.permission.SYSTEM_CAMERA: granted=true\n"
            "codePath=/system_ext/priv-app/NothingCamera\n"
            "flags=[ SYSTEM PRIVILEGED ]\n",
            encoding="utf-8",
        )
        (directory / "appops-after.txt").write_text(
            "CAMERA: allow\n",
            encoding="utf-8",
        )
        (directory / "run-status.txt").write_text(
            "completeUtc=2026-08-03T12:01:00Z\n",
            encoding="utf-8",
        )
        (directory / "SHA256SUMS").write_text("synthetic\n", encoding="utf-8")
        return directory

    def test_classifies_direct_system_camera_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for route, camera_id in (("06x", "2"), ("1x", "0"), ("2x", "3")):
                self.write_bundle(root, route, "camera2", [], open_id=camera_id)
                self.write_bundle(
                    root,
                    route,
                    "key-types",
                    [
                        {
                            "kind": "key-definition",
                            "key": {
                                "name": "com.mediatek.seamlessfeature.sensorScenario",
                                "javaType": "int[]",
                                "nativeType": "TYPE_INT32",
                            },
                        }
                    ],
                )

            report = MODULE.build_report(root)
            self.assertEqual(
                report["architecture"]["classification"],
                "direct-system-camera-route",
            )
            self.assertEqual(report["architecture"]["confidence"], 4)
            self.assertTrue(report["completeSixRunMatrix"])
            self.assertTrue(report["privilege"]["systemCameraGranted"])

    def test_classifies_public_id_vendor_sat_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for route, value in (("06x", [2]), ("1x", [0]), ("2x", [3])):
                self.write_bundle(
                    root,
                    route,
                    "camera2",
                    [
                        {
                            "kind": "builder-set",
                            "key": "com.mediatek.seamlessfeature.sensorScenario",
                            "value": value,
                        }
                    ],
                    open_id="0",
                )

            report = MODULE.build_report(root)
            self.assertEqual(
                report["architecture"]["classification"],
                "public-id-vendor-sat-route",
            )
            self.assertIn(
                "com.mediatek.seamlessfeature.sensorScenario",
                report["routeSpecificRoutingKeys"],
            )

    def test_requires_all_three_verified_camera2_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_bundle(root, "06x", "camera2", [], open_id="2")

            report = MODULE.build_report(root)
            self.assertEqual(report["architecture"]["classification"], "incomplete")
            self.assertIn("1x", report["architecture"]["missingRoutes"])
            self.assertIn("2x", report["architecture"]["missingRoutes"])


if __name__ == "__main__":
    unittest.main()
