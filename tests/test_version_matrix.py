from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
MATRIX_TOOLS = ROOT / "tools" / "matrix"
sys.path.insert(0, str(MATRIX_TOOLS))

from version_matrix import build_index, diff_builds, identity_sha256, load_matrix


MATRIX_PATH = ROOT / "data" / "builds" / "version-matrix.json"
ARTIFACT_PATH = ROOT / "data" / "artifacts" / "diagnostic-manifest.yaml"
DIFF_CLI = MATRIX_TOOLS / "diff-version-matrix.py"


class VersionMatrixTest(unittest.TestCase):
    def test_repository_entry_identity_and_experiment_links(self) -> None:
        matrix = load_matrix(MATRIX_PATH)
        builds = build_index(matrix)
        artifacts = yaml.safe_load(ARTIFACT_PATH.read_text(encoding="utf-8"))

        for build_id, build in builds.items():
            digest = identity_sha256(build)
            self.assertEqual(digest, build["identitySha256"])
            self.assertTrue(build_id.endswith("-" + digest[:8]))

        self.assertIn(artifacts["deviceBuild"]["matrixEntryId"], builds)
        artifact_by_id = {artifact["id"]: artifact for artifact in artifacts["artifacts"]}
        for artifact in artifact_by_id.values():
            self.assertIn(artifact["buildMatrixEntryId"], builds)

        for build_id, build in builds.items():
            for diagnostic in build["diagnosticBuilds"]:
                for artifact_id in diagnostic["sourceArtifacts"]:
                    self.assertIn(artifact_id, artifact_by_id)
                    self.assertEqual(
                        build_id,
                        artifact_by_id[artifact_id]["buildMatrixEntryId"],
                    )

    def test_identity_is_independent_of_camera_package_order(self) -> None:
        matrix = load_matrix(MATRIX_PATH)
        build = copy.deepcopy(next(iter(build_index(matrix).values())))
        second = copy.deepcopy(build["cameraPackages"][0])
        second["packageName"] = "com.nothing.camera.extension"
        second["versionName"] = "1.0"
        second["sha256"] = "1" * 64
        build["cameraPackages"].append(second)

        forward = identity_sha256(build)
        build["cameraPackages"].reverse()

        self.assertEqual(forward, identity_sha256(build))

    def test_diff_separates_firmware_and_camera_package_changes(self) -> None:
        matrix = load_matrix(MATRIX_PATH)
        before = copy.deepcopy(next(iter(build_index(matrix).values())))
        after = copy.deepcopy(before)
        after["id"] = "synthetic-after-00000000"
        after["platform"]["securityPatch"] = "2026-07-01"
        after["cameraPackages"][0]["versionName"] = "16.1.01.99.1"
        after["cameraPackages"][0]["sha256"] = "2" * 64
        after["identitySha256"] = identity_sha256(after)
        after["id"] = "synthetic-after-" + after["identitySha256"][:8]

        report = diff_builds(before, after)

        self.assertTrue(report["summary"]["firmwareOrPlatformChanged"])
        self.assertTrue(report["summary"]["cameraPackageChanged"])
        self.assertEqual(1, report["summary"]["generalChanges"])
        self.assertEqual(1, report["summary"]["cameraPackageChanges"])
        package_change = report["cameraPackageChanges"][0]
        paths = {field["path"] for field in package_change["fields"]}
        self.assertIn("versionName", paths)
        self.assertIn("sha256", paths)

    def test_diff_cli_writes_json_and_can_fail_on_change(self) -> None:
        matrix = load_matrix(MATRIX_PATH)
        before = copy.deepcopy(next(iter(build_index(matrix).values())))
        after = copy.deepcopy(before)
        after["platform"]["buildNumber"] = "2607000000"
        after["identitySha256"] = identity_sha256(after)
        after["id"] = "synthetic-after-" + after["identitySha256"][:8]
        synthetic = {"schemaVersion": 1, "updatedAt": "2026-08-03T00:00:00Z", "builds": [before, after]}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            matrix_path = root / "matrix.json"
            report_path = root / "report.json"
            matrix_path.write_text(json.dumps(synthetic), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(DIFF_CLI),
                    "--matrix",
                    str(matrix_path),
                    "--from",
                    before["id"],
                    "--to",
                    after["id"],
                    "--json",
                    str(report_path),
                    "--fail-on-change",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(1, result.returncode)
        self.assertEqual(1, report["summary"]["generalChanges"])
        self.assertIn("Version matrix diff:", result.stdout)

    def test_diff_cli_rejects_unknown_build_id(self) -> None:
        matrix = load_matrix(MATRIX_PATH)
        existing = next(iter(build_index(matrix)))
        result = subprocess.run(
            [
                sys.executable,
                str(DIFF_CLI),
                "--matrix",
                str(MATRIX_PATH),
                "--from",
                existing,
                "--to",
                "missing-build",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("unknown build id", result.stderr)


if __name__ == "__main__":
    unittest.main()
