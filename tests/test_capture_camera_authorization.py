from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "device" / "capture-camera-authorization.sh"


class CaptureCameraAuthorizationTest(unittest.TestCase):
    def test_collects_package_and_camera_service_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_adb = root / "fake-adb"
            output_root = root / "output"
            fake_adb.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -eu
                    command="$*"
                    case "$command" in
                      "get-state")
                        printf 'device\\n'
                        ;;
                      "get-serialno")
                        printf 'FAKE123\\n'
                        ;;
                      "shell getprop")
                        printf '[ro.build.fingerprint]: [nothing/fake]\\n'
                        ;;
                      "shell getenforce")
                        printf 'Enforcing\\n'
                        ;;
                      "shell ps -AZ")
                        printf 'u:r:platform_app:s0 system 1000 1 com.nothing.camera\\n'
                        printf 'u:r:untrusted_app:s0 u0_a123 10123 1 com.phone2pro.camera\\n'
                        ;;
                      "shell dumpsys package permissions")
                        printf 'Permission [android.permission.SYSTEM_CAMERA] (signature|privileged)\\n'
                        ;;
                      "shell cmd package list packages -U")
                        printf 'package:com.nothing.camera uid:1000\\n'
                        printf 'package:com.phone2pro.camera uid:10123\\n'
                        ;;
                      "shell dumpsys media.camera")
                        printf 'Camera ID 0 available\\nCamera ID 2 system only\\nCamera ID 3 system only\\n'
                        ;;
                      "shell dumpsys media.camera.proxy")
                        printf 'camera proxy active\\n'
                        ;;
                      "shell service list")
                        printf 'media.camera: [android.hardware.ICameraService]\\n'
                        ;;
                      *"dumpsys package com.nothing.camera")
                        printf 'userId=1000\\nandroid.permission.CAMERA: granted=true\\nandroid.permission.SYSTEM_CAMERA: granted=true\\n'
                        ;;
                      *"dumpsys package com.phone2pro.camera")
                        printf 'userId=10123\\nandroid.permission.CAMERA: granted=true\\nandroid.permission.SYSTEM_CAMERA: granted=false\\n'
                        ;;
                      *"check-permission android.permission.CAMERA"*)
                        printf 'granted\\n'
                        ;;
                      *"check-permission android.permission.SYSTEM_CAMERA com.nothing.camera"*)
                        printf 'granted\\n'
                        ;;
                      *"check-permission android.permission.SYSTEM_CAMERA com.phone2pro.camera"*)
                        printf 'denied\\n'
                        ;;
                      *)
                        printf 'fake adb output: %s\\n' "$command"
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            fake_adb.chmod(0o755)

            result = subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--adb",
                    str(fake_adb),
                    "--output",
                    str(output_root),
                    "--stock-package",
                    "com.nothing.camera",
                    "--replacement-package",
                    "com.phone2pro.camera",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            run_directories = sorted(path for path in output_root.iterdir() if path.is_dir())
            self.assertEqual(1, len(run_directories), result.stdout + result.stderr)
            run_directory = run_directories[0]
            manifest = (run_directory / "manifest.yaml").read_text(encoding="utf-8")
            readme = (run_directory / "README.txt").read_text(encoding="utf-8")
            stock_summary = next(
                (run_directory / "packages").glob("stock-*/summary.txt")
            ).read_text(encoding="utf-8")
            replacement_summary = next(
                (run_directory / "packages").glob("replacement-*/summary.txt")
            ).read_text(encoding="utf-8")

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("stockPackage: com.nothing.camera", manifest)
        self.assertIn("replacementPackage: com.phone2pro.camera", manifest)
        self.assertIn("CameraService state", readme)
        self.assertIn("android.permission.SYSTEM_CAMERA", stock_summary)
        self.assertIn("granted", stock_summary)
        self.assertIn("denied", replacement_summary)

    def test_rejects_invalid_package_name_before_adb(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--stock-package",
                "not a package",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("Invalid package name", result.stderr)


if __name__ == "__main__":
    unittest.main()
