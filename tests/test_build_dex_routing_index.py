from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "apk" / "build-dex-routing-index.py"
SPEC = importlib.util.spec_from_file_location("build_dex_routing_index", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuildDexRoutingIndexTest(unittest.TestCase):
    def test_decodes_string_and_invoke_references(self) -> None:
        # const-string v0, string@1
        # invoke-virtual {v0}, method@2
        # return-void
        instructions = [0x001A, 0x0001, 0x106E, 0x0002, 0x0000, 0x000E]
        strings, methods = MODULE.decode_code_references(
            instructions,
            string_count=4,
            method_count=5,
        )
        self.assertEqual(strings, [1])
        self.assertEqual(methods, [2])

    def test_skips_switch_payload_without_false_invoke(self) -> None:
        # packed-switch-payload with one target. The target data deliberately has
        # an invoke opcode in its low byte and must not be interpreted as code.
        instructions = [0x0100, 0x0001, 0x0000, 0x0000, 0x006E, 0x0002, 0x000E]
        strings, methods = MODULE.decode_code_references(
            instructions,
            string_count=1,
            method_count=8,
        )
        self.assertEqual(strings, [])
        self.assertEqual(methods, [])

    def test_classifies_open_camera_vendor_bridge(self) -> None:
        method = MODULE.DefinedMethod(
            dex_name="classes.dex",
            method_index=0,
            ref=MODULE.MethodRef("Lx/Controller;", "open", "()V"),
            access_flags=0,
            code_offset=1,
            string_indexes=[0, 1],
            invoked_method_indexes=[0],
        )
        reader = SimpleNamespace(
            strings=[
                "Expert 0.6x",
                "com.mediatek.seamlessfeature.sensorScenario",
            ],
            methods=[
                MODULE.MethodRef(
                    "Landroid/hardware/camera2/CameraManager;",
                    "openCamera",
                    "(Ljava/lang/String;Landroid/hardware/camera2/CameraDevice$StateCallback;Landroid/os/Handler;)V",
                )
            ],
        )
        result = MODULE.classify_method(method, reader)
        self.assertIn("camera-open", result["signalIds"])
        self.assertIn("expert-ui", result["signalIds"])
        self.assertIn("vendor-routing-key", result["signalIds"])
        self.assertGreater(result["bridgeBonus"], 0)

    def test_ignores_oversized_semantic_strings(self) -> None:
        method = MODULE.DefinedMethod(
            dex_name="classes.dex",
            method_index=0,
            ref=MODULE.MethodRef("Lx/Regex;", "init", "()V"),
            access_flags=0,
            code_offset=1,
            string_indexes=[0],
            invoked_method_indexes=[],
        )
        reader = SimpleNamespace(
            strings=["x" * 600 + "expert"],
            methods=[],
        )
        result = MODULE.classify_method(method, reader)
        self.assertNotIn("expert-ui", result["signalIds"])

    def test_builds_reverse_caller_paths(self) -> None:
        analyzed = {
            "Lx/Ui;->select()V": {"signalIds": ["expert-ui"], "score": 10},
            "Lx/Router;->route()V": {"signalIds": ["vendor-routing-key"], "score": 20},
            "Lx/Open;->open()V": {"signalIds": ["camera-open"], "score": 24},
        }
        reverse_calls = {
            "Lx/Open;->open()V": {"Lx/Router;->route()V"},
            "Lx/Router;->route()V": {"Lx/Ui;->select()V"},
        }
        paths = MODULE.build_caller_paths(
            analyzed,
            reverse_calls,
            ["Lx/Open;->open()V"],
            max_depth=3,
        )
        self.assertTrue(paths)
        self.assertEqual(
            paths[0]["methods"],
            ["Lx/Ui;->select()V", "Lx/Router;->route()V", "Lx/Open;->open()V"],
        )
        self.assertIn("expert-ui", paths[0]["signalIds"])


if __name__ == "__main__":
    unittest.main()
