from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CAPTURE = load(
    "capture_adb_clock_sample",
    ROOT / "tools" / "trace" / "capture-adb-clock-sample.py",
)
NORMALIZE = load(
    "normalize_trace_clocks",
    ROOT / "tools" / "trace" / "normalize-trace-clocks.py",
)


class ClockCaptureTest(unittest.TestCase):
    def test_parses_nanosecond_and_second_realtime(self):
        self.assertEqual(
            (12_345_000_000, 1_700_000_000_123_456_789, 1),
            CAPTURE.parse_device_clock_output(
                "uptime=12.345\nrealtime_ns=1700000000123456789\n"
            ),
        )
        self.assertEqual(
            (12_000_000_000, 1_700_000_000_000_000_000, 1_000_000_000),
            CAPTURE.parse_device_clock_output(
                "uptime=12\r\nrealtime_s=1700000000\r\n"
            ),
        )

    def test_capture_uses_host_midpoint_and_round_trip(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="uptime=100.25\nrealtime_ns=1700000000000000000\n",
            stderr="",
        )
        times = iter([1_700_000_000_100_000_000, 1_700_000_000_300_000_000])
        sample = CAPTURE.capture_sample(
            "before",
            ["adb"],
            runner=lambda *args, **kwargs: completed,
            time_ns=lambda: next(times),
        )
        self.assertEqual(200_000_000, sample["roundTripNs"])
        self.assertEqual(1_700_000_000_200_000_000, sample["hostMidpointEpochNs"])
        self.assertEqual(100_250_000_000, sample["deviceBoottimeNs"])
        self.assertEqual([], CAPTURE.validate_sample(sample))

    def test_failed_adb_sample_is_rejected(self):
        completed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="device offline"
        )
        times = iter([1, 2])
        with self.assertRaisesRegex(ValueError, "device offline"):
            CAPTURE.capture_sample(
                "before",
                ["adb"],
                runner=lambda *args, **kwargs: completed,
                time_ns=lambda: next(times),
            )


class ClockNormalizationTest(unittest.TestCase):
    def samples(self):
        base_epoch = 1_700_000_000_000_000_000
        base_boot = 100_000_000_000
        offset = base_epoch - base_boot
        return [
            {
                "schemaVersion": 1,
                "phase": "before",
                "hostSendEpochNs": base_epoch - 10_000_000,
                "hostReceiveEpochNs": base_epoch + 10_000_000,
                "hostMidpointEpochNs": base_epoch,
                "roundTripNs": 20_000_000,
                "deviceBoottimeNs": base_boot,
                "deviceRealtimeNs": base_epoch,
                "deviceRealtimePrecisionNs": 1,
            },
            {
                "schemaVersion": 1,
                "phase": "after",
                "hostSendEpochNs": base_epoch + 10_000_000_000 - 5_000_000,
                "hostReceiveEpochNs": base_epoch + 10_000_000_000 + 5_000_000,
                "hostMidpointEpochNs": base_epoch + 10_000_000_000,
                "roundTripNs": 10_000_000,
                "deviceBoottimeNs": base_boot + 10_000_000_000,
                "deviceRealtimeNs": base_epoch + 10_000_000_000,
                "deviceRealtimePrecisionNs": 1,
            },
        ], offset

    def test_builds_boottime_mapping_and_normalizes_epoch_logcat(self):
        samples, expected_offset = self.samples()
        normalization = NORMALIZE.build_normalization(samples)
        self.assertEqual(
            expected_offset,
            normalization["deviceBoottimeToHostEpochOffsetNs"],
        )
        events = NORMALIZE.normalize_logcat_lines(
            ["1700000001.500 CameraService: opened 2", "not an epoch line"],
            normalization,
        )
        self.assertEqual(1, len(events))
        self.assertEqual(101_500_000_000, events[0]["deviceBoottimeNs"])
        self.assertIn("CameraService", events[0]["message"])

    def test_requires_two_samples_and_consistent_midpoints(self):
        samples, _ = self.samples()
        with self.assertRaisesRegex(ValueError, "at least two"):
            NORMALIZE.build_normalization(samples[:1])
        samples[0]["hostMidpointEpochNs"] += 1
        with self.assertRaisesRegex(ValueError, "midpoint"):
            NORMALIZE.build_normalization(samples)

    def test_load_samples_rejects_invalid_json_and_supports_jsonl(self):
        samples, _ = self.samples()
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "samples.jsonl"
            path.write_text(
                "\n".join(__import__("json").dumps(item) for item in samples) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(2, len(NORMALIZE.load_samples(path)))
            path.write_text("not-json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                NORMALIZE.load_samples(path)


if __name__ == "__main__":
    unittest.main()
