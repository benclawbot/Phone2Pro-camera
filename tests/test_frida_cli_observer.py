from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RUNNER = load(
    "run_frida_cli_observer",
    ROOT / "tools" / "trace" / "run-frida-cli-observer.py",
)
SHIM = load(
    "frida_durable_shim",
    ROOT / "tools" / "trace" / "frida-durable-shim.py",
)


class DurableFridaRunnerTest(unittest.TestCase):
    def test_build_command_requires_existing_script(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = pathlib.Path(temporary) / "observer.js"
            script.write_text("send({kind: 'ready'});", encoding="utf-8")
            self.assertEqual(
                ["frida", "-U", "-f", "com.nothing.camera", "-l", str(script)],
                RUNNER.build_command(
                    "frida", "-U", "com.nothing.camera", script
                ),
            )
        with self.assertRaisesRegex(ValueError, "not found"):
            RUNNER.build_command(
                "frida", "-U", "com.nothing.camera", pathlib.Path("missing.js")
            )

    def test_output_is_flushed_and_clean_eof_is_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            child = root / "child.py"
            child.write_text(
                textwrap.dedent(
                    """
                    import sys
                    print('{"type":"send","payload":{"kind":"observer-ready"}}', flush=True)
                    sys.stdin.read()
                    print('{"type":"send","payload":{"kind":"observer-detached"}}', flush=True)
                    """
                ),
                encoding="utf-8",
            )
            output = root / "frida.log"
            status = root / "frida-runner-status.json"
            mirror = io.StringIO()
            exit_status = RUNNER.run_observer(
                [sys.executable, str(child)],
                output,
                status,
                input_stream=io.StringIO("\n"),
                mirror=mirror,
                graceful_timeout_seconds=2,
            )

            self.assertEqual(0, exit_status)
            text = output.read_text(encoding="utf-8")
            self.assertIn("observer-ready", text)
            self.assertIn("observer-detached", text)
            state = json.loads(status.read_text(encoding="utf-8"))
            self.assertEqual("enter", state["completionMode"])
            self.assertFalse(state["forcedTermination"])
            self.assertEqual(2, state["lineCount"])
            self.assertGreater(state["outputBytes"], 0)

    def test_launch_error_is_preserved_in_output_and_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            output = root / "frida.log"
            status = root / "frida-runner-status.json"
            exit_status = RUNNER.run_observer(
                ["definitely-not-a-real-command-p2p"],
                output,
                status,
                input_stream=io.StringIO(""),
                mirror=None,
            )
            self.assertEqual(127, exit_status)
            self.assertIn("observer-launch-error", output.read_text(encoding="utf-8"))
            state = json.loads(status.read_text(encoding="utf-8"))
            self.assertEqual("launch-error", state["completionMode"])
            self.assertGreater(state["outputBytes"], 0)

    def test_shim_parses_the_existing_runner_invocation(self):
        parsed = SHIM.parse_existing_invocation(
            [
                "-U",
                "-f",
                "com.nothing.camera",
                "-l",
                "observer.js",
                "-o",
                "frida.log",
            ]
        )
        self.assertEqual("-U", parsed["deviceArg"])
        self.assertEqual("com.nothing.camera", parsed["package"])
        self.assertEqual(pathlib.Path("observer.js"), parsed["script"])
        self.assertEqual(pathlib.Path("frida.log"), parsed["output"])
        with self.assertRaisesRegex(ValueError, "missing -o"):
            SHIM.parse_existing_invocation(
                ["-U", "-f", "com.nothing.camera", "-l", "observer.js"]
            )


if __name__ == "__main__":
    unittest.main()
