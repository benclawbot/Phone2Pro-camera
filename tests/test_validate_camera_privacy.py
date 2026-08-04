import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "tools" / "validate-camera-privacy.py"
SPEC = importlib.util.spec_from_file_location("validate_camera_privacy", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CameraPrivacyValidatorTest(unittest.TestCase):
    def make_repo(self, manifest: str, java: str = "", build: str = "") -> pathlib.Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        app = root / "camera-app" / "app"
        manifest_path = app / "src" / "main" / "AndroidManifest.xml"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(manifest, encoding="utf-8")
        java_path = app / "src" / "main" / "java" / "example" / "Stage.java"
        java_path.parent.mkdir(parents=True)
        java_path.write_text(java, encoding="utf-8")
        (app / "build.gradle").write_text(build, encoding="utf-8")
        return root

    def safe_manifest(self) -> str:
        return """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-permission android:name="android.permission.CAMERA" />
  <application android:allowBackup="false" android:usesCleartextTraffic="false" />
</manifest>
"""

    def test_safe_camera_app_passes(self):
        self.assertEqual([], MODULE.validate(self.make_repo(self.safe_manifest())))

    def test_network_permissions_are_rejected(self):
        manifest = self.safe_manifest().replace(
            '<uses-permission android:name="android.permission.CAMERA" />',
            '<uses-permission android:name="android.permission.CAMERA" />\n'
            '  <uses-permission android:name="android.permission.INTERNET" />',
        )
        errors = MODULE.validate(self.make_repo(manifest))
        self.assertTrue(any("INTERNET" in error for error in errors))

    def test_backup_and_cleartext_must_be_disabled(self):
        manifest = self.safe_manifest().replace(
            'android:allowBackup="false" android:usesCleartextTraffic="false"',
            'android:allowBackup="true" android:usesCleartextTraffic="true"',
        )
        errors = MODULE.validate(self.make_repo(manifest))
        self.assertTrue(any("allowBackup" in error for error in errors))
        self.assertTrue(any("usesCleartextTraffic" in error for error in errors))

    def test_network_source_and_dependencies_are_rejected(self):
        root = self.make_repo(
            self.safe_manifest(),
            java="import java.net.URL;\nfinal class Stage {}\n",
            build='dependencies { implementation "com.squareup.okhttp3:okhttp:5.0.0" }',
        )
        errors = MODULE.validate(root)
        self.assertTrue(any("java.net" in error for error in errors))
        self.assertTrue(any("okhttp" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
