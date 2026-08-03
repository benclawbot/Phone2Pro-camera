from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "trace" / "analyze-camera-error-taxonomy.py"
SPEC = importlib.util.spec_from_file_location("analyze_camera_error_taxonomy", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AnalyzeCameraErrorTaxonomyTest(unittest.TestCase):
    def system_probe_document(self) -> dict:
        message = (
            "CAMERA_ERROR (3): getCameraCharacteristics:1339: Unable to retrieve "
            "cameracharacteristics for system only device 2: "
        )
        error = {
            "type": "android.hardware.camera2.CameraAccessException",
            "message": message,
            "cameraAccessReason": 3,
        }
        return {
            "cameraOpen": {
                "data": {
                    "publicCameraIds": ["0", "1"],
                    "probes": [
                        {
                            "cameraId": "2",
                            "characteristicsReadable": False,
                            "characteristicsError": error,
                            "openOutcome": "exception",
                            "openError": error,
                            "durationMillis": 7,
                        }
                    ],
                }
            }
        }

    def test_system_only_error_overrides_generic_reason_three(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe.json"
            path.write_text(json.dumps(self.system_probe_document()), encoding="utf-8")
            report = MODULE.build_report(
                [MODULE.SourceInput("ordinary", path)],
                MODULE.CallerIdentity(package_name="com.phone2pro.camera", uid=10123),
            )

        self.assertEqual(2, len(report["observations"]))
        by_stage = {item["stage"]: item for item in report["observations"]}
        self.assertEqual("SECURITY", by_stage["CHARACTERISTICS"]["category"])
        self.assertEqual("SYSTEM_CAMERA_PERMISSION", by_stage["CHARACTERISTICS"]["family"])
        self.assertEqual("OPEN_PREFLIGHT", by_stage["OPEN_PREFLIGHT"]["stage"])
        self.assertEqual(7, by_stage["OPEN_PREFLIGHT"]["duration_ms"])
        self.assertEqual("com.phone2pro.camera", by_stage["OPEN_PREFLIGHT"]["caller"]["package_name"])

    def test_numeric_code_is_interpreted_by_namespace(self) -> None:
        access = MODULE.classify_error(
            "OPEN_CONNECT", None, None,
            namespace="CameraAccessException.reason", code=4,
        )
        callback = MODULE.classify_error(
            "OPEN_CONNECT", None, None,
            namespace="CameraDevice.StateCallback.error", code=4,
        )
        self.assertEqual("IN_USE", access[0])
        self.assertEqual("CAMERA_IN_USE", access[1])
        self.assertEqual("DEVICE_SPECIFIC", callback[0])
        self.assertEqual("ERROR_CAMERA_DEVICE", callback[1])

    def test_classifies_session_and_request_events(self) -> None:
        events = [
            {
                "kind": "session-configure-failed",
                "cameraId": "0",
                "error": "onConfigureFailed",
                "timestampMs": 100,
                "durationMs": 18,
                "pid": 12,
                "tid": 13,
            },
            {
                "kind": "capture-failed",
                "cameraId": "0",
                "reason": 1,
                "failure": {"message": "capture flushed"},
                "timestampMs": 130,
            },
        ]
        observations = MODULE.event_observations(
            MODULE.SourceInput("trace", Path("trace.log")),
            events,
            MODULE.CallerIdentity(process_name="com.nothing.camera"),
        )
        self.assertEqual("CONFIGURATION", observations[0].category)
        self.assertEqual("SESSION_CONFIGURE_FAILED", observations[0].family)
        self.assertEqual("REQUEST_FAILURE", observations[1].category)
        self.assertEqual("REASON_FLUSHED", observations[1].family)
        self.assertEqual(12, observations[0].caller.pid)
        self.assertEqual(18, observations[0].duration_ms)

    def test_separates_in_use_max_camera_disconnected_and_invalid(self) -> None:
        cases = [
            ("CameraAccessException.reason", 2, "DISCONNECTED"),
            ("CameraAccessException.reason", 4, "IN_USE"),
            ("CameraAccessException.reason", 5, "MAX_CAMERAS"),
        ]
        for namespace, code, expected in cases:
            with self.subTest(code=code):
                result = MODULE.classify_error(
                    "OPEN_CONNECT", None, None, namespace=namespace, code=code
                )
                self.assertEqual(expected, result[0])
        invalid = MODULE.classify_error(
            "CHARACTERISTICS",
            "java.lang.IllegalArgumentException",
            "unknown device 9",
        )
        self.assertEqual("INVALID_ARGUMENT", invalid[0])
        self.assertEqual("CAMERA_ID_NOT_FOUND", invalid[1])

    def test_reports_incomplete_caller_and_timing_coverage(self) -> None:
        observation = MODULE.ErrorObservation(
            source_label="x",
            source_path="x",
            stage="OPEN_CONNECT",
            operation="openCamera",
            outcome="ERROR",
            camera_id="0",
            category="SERVICE",
            family="ERROR_CAMERA_SERVICE",
            classification="VERIFIED",
            code_namespace="CameraDevice.StateCallback.error",
            code=5,
            code_name="ERROR_CAMERA_SERVICE",
            exception_type=None,
            message=None,
            timestamp_ms=None,
            duration_ms=None,
            caller=MODULE.CallerIdentity(),
            enforcing_paths=[],
            evidence={},
        )
        result = MODULE.coverage([observation])
        self.assertFalse(result["timingComplete"])
        self.assertFalse(result["callerIdentityComplete"])
        self.assertEqual(0, result["withCallerUid"])

    def test_cli_accepts_json_lines_and_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "events.log"
            json_out = root / "report.json"
            markdown_out = root / "report.md"
            source.write_text(
                json.dumps({
                    "type": "send",
                    "payload": {
                        "kind": "camera-device-error",
                        "cameraId": "0",
                        "errorCode": 2,
                        "error": "max cameras",
                        "timestampMs": 9,
                    },
                }) + "\n",
                encoding="utf-8",
            )
            result = MODULE.main([
                f"stock={source}",
                "--caller-package", "com.nothing.camera",
                "--caller-uid", "1000",
                "--json", str(json_out),
                "--markdown", str(markdown_out),
            ])
            report = json.loads(json_out.read_text(encoding="utf-8"))
            markdown = markdown_out.read_text(encoding="utf-8")
        self.assertEqual(0, result)
        self.assertEqual("MAX_CAMERAS", report["observations"][0]["category"])
        self.assertTrue(report["coverage"]["callerIdentityComplete"])
        self.assertIn("ERROR_MAX_CAMERAS_IN_USE", markdown)


if __name__ == "__main__":
    unittest.main()
