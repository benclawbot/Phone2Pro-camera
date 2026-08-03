from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "device" / "analyze-camera-authorization.py"
SPEC = importlib.util.spec_from_file_location("analyze_camera_authorization", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def command(text: str, exit_code: int | None = None) -> str:
    suffix = "" if exit_code is None else f"\n# command_exit_code: {exit_code}\n"
    return f"# command: fake\n\n{text.rstrip()}\n{suffix}"


class AnalyzeCameraAuthorizationTest(unittest.TestCase):
    def create_bundle(
        self,
        root: Path,
        *,
        stock_system: str = "granted",
        ordinary_system: str = "denied",
        ordinary_camera: str = "granted",
        ordinary_appop: str = "allow",
    ) -> Path:
        run = root / "20260804T000000Z"
        device = run / "device"
        stock = run / "packages" / "stock-com_nothing_camera"
        ordinary = run / "packages" / "replacement-com_phone2pro_camera"
        related = run / "packages" / "related-com_nothing_camera_service"
        for directory in (device, stock, ordinary, related):
            directory.mkdir(parents=True, exist_ok=True)
        (run / "manifest.yaml").write_text("schemaVersion: 1\n", encoding="utf-8")
        (device / "process-contexts.txt").write_text(command(
            "u:r:platform_app:s0 system 1000 1 com.nothing.camera\n"
            "u:r:untrusted_app:s0:c123,c456 u0_a123 10123 1 com.phone2pro.camera"
        ), encoding="utf-8")
        (device / "role-service.txt").write_text(command(
            "holders: com.nothing.camera"
        ), encoding="utf-8")

        self.write_package(
            stock,
            "com.nothing.camera",
            camera="granted",
            system_camera=stock_system,
            appop="allow",
            path="/product/priv-app/NothingCamera/NothingCamera.apk",
            uid=1000,
            flags="SYSTEM PRIVILEGED",
            allowlist=True,
        )
        self.write_package(
            ordinary,
            "com.phone2pro.camera",
            camera=ordinary_camera,
            system_camera=ordinary_system,
            appop=ordinary_appop,
            path="/data/app/~~abc/com.phone2pro.camera/base.apk",
            uid=10123,
            flags="HAS_CODE",
            allowlist=False,
        )
        self.write_package(
            related,
            "com.nothing.camera.service",
            camera="denied",
            system_camera="denied",
            appop="default",
            path="/system_ext/priv-app/CameraService/CameraService.apk",
            uid=1001,
            flags="SYSTEM PRIVILEGED",
            allowlist=False,
        )
        return run

    def write_package(
        self,
        directory: Path,
        package: str,
        *,
        camera: str,
        system_camera: str,
        appop: str,
        path: str,
        uid: int,
        flags: str,
        allowlist: bool,
    ) -> None:
        role = directory.name.split("-", 1)[0]
        (directory / "summary.txt").write_text(
            f"package={package}\nrole={role}\n", encoding="utf-8"
        )
        (directory / "check-camera-permission.txt").write_text(
            command(camera), encoding="utf-8"
        )
        (directory / "check-system-camera-permission.txt").write_text(
            command(system_camera), encoding="utf-8"
        )
        (directory / "appops.txt").write_text(
            command(f"CAMERA: {appop}"), encoding="utf-8"
        )
        (directory / "package-path.txt").write_text(
            command(f"package:{path}"), encoding="utf-8"
        )
        (directory / "package-uid.txt").write_text(
            command(f"package:{package} uid:{uid}"), encoding="utf-8"
        )
        (directory / "dumpsys-package.txt").write_text(
            command(
                f"userId={uid}\n"
                f"pkgFlags=[ {flags} ]\n"
                "requested permissions:\n"
                "  android.permission.CAMERA\n"
                "  android.permission.SYSTEM_CAMERA"
            ),
            encoding="utf-8",
        )
        allow_text = "android.permission.SYSTEM_CAMERA" if allowlist else "android.permission.OTHER"
        (directory / "privapp-permissions.txt").write_text(
            command(allow_text), encoding="utf-8"
        )
        (directory / "privapp-deny-permissions.txt").write_text(
            command(""), encoding="utf-8"
        )

    def test_identifies_missing_system_camera_grant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = self.create_bundle(Path(directory))
            report = MODULE.build_report(run, "stock", "replacement")

        comparison = report["comparison"]
        self.assertEqual("MISSING_SYSTEM_CAMERA_GRANT", comparison["primaryGate"]["id"])
        self.assertEqual("VERIFIED", comparison["primaryGate"]["classification"])
        finding_ids = {item["id"] for item in comparison["findings"]}
        self.assertIn("stock-only-system-camera-grant", finding_ids)
        self.assertIn("privapp-allowlist-difference", finding_ids)
        self.assertIn("install-partition-difference", finding_ids)
        self.assertIn("selinux-domain-difference", finding_ids)
        self.assertEqual(3, len(report["packages"]))

    def test_permission_parity_moves_to_deeper_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = self.create_bundle(
                Path(directory), ordinary_system="granted", ordinary_appop="allow"
            )
            report = MODULE.build_report(run, "stock", "replacement")

        gate = report["comparison"]["primaryGate"]
        self.assertEqual("PERMISSION_PARITY_DEEPER_GATE_REQUIRED", gate["id"])
        self.assertEqual("PARTIALLY_VERIFIED", gate["classification"])

    def test_appop_denial_is_separate_from_permission_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = self.create_bundle(
                Path(directory), ordinary_system="granted", ordinary_appop="deny"
            )
            report = MODULE.build_report(run, "stock", "replacement")

        self.assertEqual(
            "CAMERA_APPOP_DENIED", report["comparison"]["primaryGate"]["id"]
        )

    def test_failed_permission_command_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = self.create_bundle(Path(directory), ordinary_system="granted")
            ordinary = run / "packages" / "replacement-com_phone2pro_camera"
            (ordinary / "check-system-camera-permission.txt").write_text(
                command("Security exception", exit_code=1), encoding="utf-8"
            )
            report = MODULE.build_report(run, "stock", "replacement")

        gate = report["comparison"]["primaryGate"]
        self.assertEqual("SYSTEM_CAMERA_GRANT_UNKNOWN", gate["id"])
        self.assertEqual("UNKNOWN", gate["classification"])

    def test_selects_newest_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self.create_bundle(root)
            newest = root / "20260804T010000Z"
            old.rename(newest)
            older = root / "20260803T230000Z"
            self.create_bundle(root).rename(older)

            self.assertEqual(newest, MODULE.select_run(root))

    def test_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.create_bundle(root)
            json_path = root / "report.json"
            markdown_path = root / "report.md"
            result = MODULE.main([
                str(run),
                "--json", str(json_path),
                "--markdown", str(markdown_path),
            ])
            data = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(0, result)
        self.assertEqual(1, data["schemaVersion"])
        self.assertIn("MISSING_SYSTEM_CAMERA_GRANT", markdown)
        self.assertIn("VERIFIED", markdown)


if __name__ == "__main__":
    unittest.main()
