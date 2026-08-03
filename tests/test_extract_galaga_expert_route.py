from __future__ import annotations

import importlib.util
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "apk" / "extract-galaga-expert-route.py"
SPEC = importlib.util.spec_from_file_location("extract_galaga_expert_route", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeReader:
    def __init__(self, instructions: list[int]) -> None:
        header = struct.pack("<HHHHII", 6, 1, 3, 0, 0, len(instructions))
        self.data = b"\0" * 16 + header + struct.pack(f"<{len(instructions)}H", *instructions)
        self.name = "classes5.dex"
        self.strings = ["[0.6,1)", "[1,2)", "[2,10]"]
        self.types = ["Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;"]
        self.methods = [
            MODULE.DEX.MethodRef(
                "Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;",
                "setMaxZoom",
                "(I)Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;",
            ),
            MODULE.DEX.MethodRef(
                "Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;",
                "addZoomRegionCameraIdItem",
                "(Ljava/lang/String;I)Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;",
            ),
        ]

    def u16(self, offset: int) -> int:
        return struct.unpack_from("<H", self.data, offset)[0]

    def u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.data, offset)[0]

    def _check_range(self, offset: int, size: int, _label: str) -> None:
        if offset < 0 or offset + size > len(self.data):
            raise ValueError("out of bounds")


def const4(register: int, value: int) -> int:
    return 0x12 | (register << 8) | ((value & 0xF) << 12)


def const_string(register: int, string_index: int) -> list[int]:
    return [0x1A | (register << 8), string_index]


def invoke35(method_index: int, registers: list[int]) -> list[int]:
    padded = registers + [0] * (5 - len(registers))
    c, d, e, f, g = padded
    first = 0x6E | (g << 8) | (len(registers) << 12)
    third = c | (d << 4) | (e << 8) | (f << 12)
    return [first, method_index, third]


class ExtractGalagaExpertRouteTest(unittest.TestCase):
    def manual_instructions(self) -> list[int]:
        instructions: list[int] = []
        instructions += [const4(0, 2)]
        instructions += [0x0513, 10]  # const/16 v5, 10
        instructions += invoke35(0, [4, 5])
        instructions += [0x040C]  # move-result-object v4
        instructions += const_string(5, 0)
        instructions += invoke35(1, [4, 5, 0])
        instructions += [0x040C]
        instructions += const_string(5, 1)
        instructions += [const4(0, 0)]
        instructions += invoke35(1, [4, 5, 0])
        instructions += [0x040C]
        instructions += const_string(5, 2)
        instructions += [const4(0, 3)]
        instructions += invoke35(1, [4, 5, 0])
        instructions += [0x040C, 0x000E]
        return instructions

    def test_extracts_expected_manual_mapping(self) -> None:
        reader = FakeReader(self.manual_instructions())
        method = SimpleNamespace(
            code_offset=16,
            ref=MODULE.DEX.MethodRef(
                "Lcom/nothing/common/utils/config/zoom/ProductGalagaZoomConfigBuilder;",
                "addManualZoomConfig",
                "()V",
            ),
        )

        result = MODULE.extract_manual_route(reader, method)

        self.assertEqual(10, result["maxZoom"])
        self.assertTrue(result["expectedMappingRecovered"])
        self.assertEqual(
            MODULE.EXPECTED_MAPPING,
            [
                {"zoomRegion": item["zoomRegion"], "cameraId": item["cameraId"]}
                for item in result["mappings"]
            ],
        )

    def test_rejects_changed_camera_id(self) -> None:
        instructions = self.manual_instructions()
        # Replace the final const/4 v0, 3 with v0, 4.
        instructions[-6] = const4(0, 4)
        reader = FakeReader(instructions)
        method = SimpleNamespace(
            code_offset=16,
            ref=MODULE.DEX.MethodRef("Lx;", "addManualZoomConfig", "()V"),
        )

        result = MODULE.extract_manual_route(reader, method)

        self.assertFalse(result["expectedMappingRecovered"])
        self.assertEqual(4, result["mappings"][-1]["cameraId"])

    def test_invoke_register_decoder_preserves_order(self) -> None:
        unit = 0x6E | (3 << 12)
        third = 4 | (5 << 4) | (2 << 8)
        self.assertEqual([4, 5, 2], MODULE._invoke_registers35(unit, third))


if __name__ == "__main__":
    unittest.main()
