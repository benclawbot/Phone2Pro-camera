from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "tools" / "toolchain" / "verify-re-toolchain.py"
BOOTSTRAP = ROOT / "tools" / "toolchain" / "bootstrap-re-toolchain.sh"


def write_executable(path: Path, output: str, exit_code: int = 0) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' {output!r}
            exit {exit_code}
            """
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_lock(path: Path, tools: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "verifiedAtUtc": "2026-08-03T00:00:00Z",
                "defaultProfile": "full",
                "profiles": {"full": "test"},
                "tools": tools,
                "hostUtilities": ["sh"],
            }
        ),
        encoding="utf-8",
    )


class VerifyReverseEngineeringToolchainTest(unittest.TestCase):
    def test_strict_report_distinguishes_pass_mismatch_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "good"
            wrong = root / "wrong"
            write_executable(good, "good 1.2.3")
            write_executable(wrong, "wrong 9.9.9")
            lock = root / "lock.json"
            report = root / "report.json"
            write_lock(
                lock,
                [
                    {
                        "id": "good",
                        "version": "1.2.3",
                        "profiles": ["full"],
                        "required": True,
                        "probe": {
                            "type": "command",
                            "command": str(good),
                            "args": [],
                            "versionRegex": "good (1\\.2\\.3)",
                        },
                    },
                    {
                        "id": "wrong",
                        "version": "1.0.0",
                        "profiles": ["full"],
                        "required": True,
                        "probe": {
                            "type": "command",
                            "command": str(wrong),
                            "args": [],
                            "versionRegex": "wrong ([0-9.]+)",
                        },
                    },
                    {
                        "id": "absent",
                        "version": "1",
                        "profiles": ["full"],
                        "required": True,
                        "probe": {
                            "type": "command",
                            "command": "definitely-not-installed-phone2pro-tool",
                            "args": [],
                            "versionRegex": "(1)",
                        },
                    },
                ],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(VERIFIER),
                    "--lock",
                    str(lock),
                    "--strict",
                    "--json",
                    str(report),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(1, result.returncode)
        self.assertEqual(
            {"pass": 1, "missing": 1, "mismatch": 1, "error": 0},
            payload["summary"],
        )
        statuses = {item["id"]: item["status"] for item in payload["results"]}
        self.assertEqual("pass", statuses["good"])
        self.assertEqual("mismatch", statuses["wrong"])
        self.assertEqual("missing", statuses["absent"])

    def test_command_override_replaces_locked_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            replacement = root / "replacement"
            write_executable(replacement, "tool 4.5.6")
            lock = root / "lock.json"
            write_lock(
                lock,
                [
                    {
                        "id": "tool",
                        "version": "4.5.6",
                        "profiles": ["full"],
                        "required": True,
                        "probe": {
                            "type": "command",
                            "command": "missing-default",
                            "args": [],
                            "versionRegex": "tool (4\\.5\\.6)",
                        },
                    }
                ],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(VERIFIER),
                    "--lock",
                    str(lock),
                    "--strict",
                    "--tool",
                    f"tool={replacement}",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_invalid_lock_returns_configuration_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "lock.json"
            lock.write_text('{"schemaVersion": 99}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VERIFIER), "--lock", str(lock)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(2, result.returncode)
        self.assertIn("schemaVersion", result.stderr)

    def test_repository_lock_is_parseable_without_strict_mode(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VERIFIER), "--profile", "static"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("Reverse-engineering toolchain profile: static", result.stdout)
        self.assertIn("Summary:", result.stdout)

    def test_bootstrap_dry_run_uses_the_repository_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    "bash",
                    str(BOOTSTRAP),
                    "--dry-run",
                    "--install-dir",
                    directory,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("jadx-1.5.5.zip", result.stdout)
        self.assertIn("install pinned Frida packages", result.stdout)
        self.assertIn("Android SDK Platform-Tools 37.0.1", result.stdout)
        self.assertIn("Perfetto trace_processor_shell 55.3", result.stdout)
        self.assertIn("Verify with:", result.stdout)


if __name__ == "__main__":
    unittest.main()
