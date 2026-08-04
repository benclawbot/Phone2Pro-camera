import hashlib
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "index-firmware-images.py"
SPEC = importlib.util.spec_from_file_location("index_firmware_images", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FirmwareImageIndexerTest(unittest.TestCase):
    def source_index(self):
        return MODULE.load_source_index(ROOT)

    def test_committed_source_index_is_valid_and_blocked(self):
        source = self.source_index()
        self.assertEqual([], MODULE.validate_source_index(source))
        self.assertEqual("BLOCKED_PENDING_LOCAL_ARTIFACTS", source["status"])
        self.assertTrue(
            all(
                record["status"] == "NOT_VERIFIED"
                for record in source["requiredPartitionCoverage"]
            )
        )

    def test_indexes_partition_files_with_sha256_and_missing_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            (directory / "system.img").write_bytes(b"system-bytes")
            (directory / "vendor_a.img").write_bytes(b"vendor-bytes")
            (directory / "notes.txt").write_text("ignored", encoding="utf-8")

            inventory = MODULE.index_directory(
                directory,
                self.source_index(),
                "oem-incremental-ota",
                "unit-test",
                "2026-08-04T10:00:00+02:00",
            )

        self.assertEqual(2, inventory["artifactCount"])
        self.assertEqual(["system", "vendor"], [item["partition"] for item in inventory["artifacts"]])
        self.assertEqual(
            hashlib.sha256(b"system-bytes").hexdigest(),
            inventory["artifacts"][0]["sha256"],
        )
        self.assertNotIn("system", inventory["missingRequiredPartitions"])
        self.assertNotIn("vendor", inventory["missingRequiredPartitions"])
        self.assertIn("odm", inventory["missingRequiredPartitions"])
        self.assertEqual([], MODULE.validate_inventory(inventory))

    def test_longest_partition_name_wins(self):
        required = {"vendor", "vendor_boot", "vendor_dlkm"}
        self.assertEqual("vendor_boot", MODULE.infer_partition("vendor_boot_a.img", required))
        self.assertEqual("vendor_dlkm", MODULE.infer_partition("vendor_dlkm.image.img", required))
        self.assertEqual("vendor", MODULE.infer_partition("vendor.img", required))

    def test_unknown_files_are_not_invented_as_partitions(self):
        required = MODULE.required_partitions(self.source_index())
        self.assertIsNone(MODULE.infer_partition("camera-provider.so", required))
        self.assertIsNone(MODULE.infer_partition("release-notes.zip", required))

    def test_empty_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            (directory / "system.img").write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "artifact is empty"):
                MODULE.index_directory(
                    directory,
                    self.source_index(),
                    "oem-incremental-ota",
                    "unit-test",
                    "2026-08-04T10:00:00+02:00",
                )

    def test_symlink_is_rejected_when_supported(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks are unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            target = directory / "target.img"
            target.write_bytes(b"target")
            link = directory / "system.img"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink creation is not permitted")
            with self.assertRaisesRegex(ValueError, "symlinks are not allowed"):
                MODULE.index_directory(
                    directory,
                    self.source_index(),
                    "oem-incremental-ota",
                    "unit-test",
                    "2026-08-04T10:00:00+02:00",
                )

    def test_invalid_inventory_digest_is_rejected(self):
        inventory = {
            "schemaVersion": 1,
            "artifactCount": 1,
            "artifacts": [
                {
                    "sourceId": "oem-incremental-ota",
                    "relativePath": "system.img",
                    "partition": "system",
                    "sizeBytes": 1,
                    "sha256": "not-a-digest",
                    "collectedAt": "2026-08-04T10:00:00+02:00",
                    "collector": "unit-test",
                    "status": "VERIFIED_LOCAL_SHA256",
                }
            ],
            "missingRequiredPartitions": [],
        }
        errors = MODULE.validate_inventory(inventory)
        self.assertTrue(any("lowercase SHA-256" in error for error in errors))

    def test_cli_output_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            (directory / "boot.img").write_bytes(b"boot")
            inventory = MODULE.index_directory(
                directory,
                self.source_index(),
                "oem-incremental-ota",
                "unit-test",
                "2026-08-04T10:00:00+02:00",
            )
            encoded = json.dumps(inventory)
        self.assertIn('"partition": "boot"', encoded)


if __name__ == "__main__":
    unittest.main()
