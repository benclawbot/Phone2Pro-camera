from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "trace" / "normalize-trace-clocks.py"
SPEC = importlib.util.spec_from_file_location("normalize_trace_clocks_android", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AndroidEpochLogcatNormalizationTest(unittest.TestCase):
    def normalization(self):
        return {
            "deviceBoottimeToDeviceRealtimeOffsetNs": 1_700_000_000_000_000_000,
            "deviceRealtimeToHostEpochOffsetNs": 2_000_000,
            "estimatedUncertaintyNs": 50_000_000,
        }

    def test_accepts_android_padding_and_windows_line_endings(self):
        events = MODULE.normalize_logcat_lines(
            [
                "--------- beginning of main",
                "         1700000100.125  1507 13872 I CameraService: CameraService::connect call (PID 99 \"com.nothing.camera\", camera ID 2) and Camera API version 2\r\n",
            ],
            self.normalization(),
        )
        self.assertEqual(1, len(events))
        event = events[0]
        self.assertEqual(2, event["sourceLine"])
        self.assertEqual(1_700_000_100_125_000_000, event["deviceRealtimeNs"])
        self.assertEqual(100_125_000_000, event["deviceBoottimeNs"])
        self.assertEqual(1_700_000_100_127_000_000, event["hostEpochNs"])
        self.assertTrue(event["message"].startswith("1507 13872 I CameraService"))

    def test_requires_both_realtime_offsets(self):
        with self.assertRaisesRegex(ValueError, "realtime/host"):
            MODULE.normalize_logcat_lines(
                ["1700000100.125 CameraService: opened 2"],
                {
                    "deviceBoottimeToDeviceRealtimeOffsetNs": 1,
                    "estimatedUncertaintyNs": 1,
                },
            )


if __name__ == "__main__":
    unittest.main()
