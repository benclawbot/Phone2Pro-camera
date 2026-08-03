from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "trace" / "compare-routing-traces.py"


class CompareRoutingTracesTest(unittest.TestCase):
    def write_trace(self, directory: Path, name: str, events: list[dict]) -> Path:
        path = directory / name
        path.write_text(
            "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
            encoding="utf-8",
        )
        return path

    def test_identifies_route_specific_camera_ids_and_session_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            common = {
                "kind": "builder-set",
                "key": "android.control.zoomRatio",
                "value": 1.0,
                "timestampMs": 100,
            }
            traces = {
                "06x": self.write_trace(
                    directory,
                    "06x.log",
                    [
                        {"kind": "open-camera", "cameraId": "2", "timestampMs": 1},
                        {
                            "kind": "set-session-parameters",
                            "request": {"com.mediatek.seamlessfeature.sensorScenario": [2]},
                            "timestampMs": 2,
                        },
                        common,
                    ],
                ),
                "1x": self.write_trace(
                    directory,
                    "1x.log",
                    [
                        {"kind": "open-camera", "cameraId": "0", "timestampMs": 3},
                        {
                            "kind": "set-session-parameters",
                            "request": {"com.mediatek.seamlessfeature.sensorScenario": [0]},
                            "timestampMs": 4,
                        },
                        common,
                    ],
                ),
                "2x": self.write_trace(
                    directory,
                    "2x.log",
                    [
                        {"kind": "open-camera", "cameraId": "3", "timestampMs": 5},
                        {
                            "kind": "set-session-parameters",
                            "request": {"com.mediatek.seamlessfeature.sensorScenario": [3]},
                            "timestampMs": 6,
                        },
                        common,
                    ],
                ),
            }

            json_output = directory / "comparison.json"
            markdown_output = directory / "comparison.md"
            command = [sys.executable, str(SCRIPT)]
            for label, path in traces.items():
                command.extend(["--trace", f"{label}={path}"])
            command.extend(["--json", str(json_output), "--markdown", str(markdown_output)])

            completed = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            comparison = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(
                comparison["traces"]["06x"]["routeSummary"]["openedCameraIds"],
                ["2"],
            )
            self.assertEqual(
                comparison["traces"]["1x"]["routeSummary"]["openedCameraIds"],
                ["0"],
            )
            self.assertEqual(
                comparison["traces"]["2x"]["routeSummary"]["openedCameraIds"],
                ["3"],
            )

            route_specific = comparison["routeSpecific"]
            self.assertTrue(any(item["event"].get("cameraId") == "2" for item in route_specific["06x"]))
            self.assertTrue(any(item["event"].get("cameraId") == "0" for item in route_specific["1x"]))
            self.assertTrue(any(item["event"].get("cameraId") == "3" for item in route_specific["2x"]))

            markdown = markdown_output.read_text(encoding="utf-8")
            self.assertIn("Expert Routing Differential Report", markdown)
            self.assertIn("06x", markdown)
            self.assertIn("1x", markdown)
            self.assertIn("2x", markdown)

    def test_accepts_frida_send_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            wrapped = {
                "type": "send",
                "payload": {"kind": "open-camera", "cameraId": "4", "timestampMs": 1},
            }
            first = self.write_trace(directory, "first.log", [wrapped])
            second = self.write_trace(directory, "second.log", [wrapped])
            json_output = directory / "comparison.json"
            markdown_output = directory / "comparison.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--trace",
                    f"a={first}",
                    "--trace",
                    f"b={second}",
                    "--json",
                    str(json_output),
                    "--markdown",
                    str(markdown_output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            comparison = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(comparison["traces"]["a"]["routeSummary"]["openedCameraIds"], ["4"])
            self.assertEqual(comparison["traces"]["b"]["routeSummary"]["openedCameraIds"], ["4"])


if __name__ == "__main__":
    unittest.main()
