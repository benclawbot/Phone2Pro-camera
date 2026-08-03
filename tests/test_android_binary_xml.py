from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APK_TOOLS = ROOT / "tools" / "apk"
sys.path.insert(0, str(APK_TOOLS))

from android_binary_xml import (
    BinaryXmlError,
    _read_length16,
    _read_length8,
    parse_manifest,
    read_manifest_input,
)

NO_INDEX = 0xFFFFFFFF


def _length8(value: int) -> bytes:
    if value > 0x7FFF:
        raise ValueError(value)
    if value > 0x7F:
        return bytes((0x80 | (value >> 8), value & 0xFF))
    return bytes((value,))


def _string_pool(strings: list[str]) -> bytes:
    encoded: list[bytes] = []
    offsets: list[int] = []
    cursor = 0
    for value in strings:
        raw = value.encode("utf-8")
        item = _length8(len(value)) + _length8(len(raw)) + raw + b"\x00"
        offsets.append(cursor)
        encoded.append(item)
        cursor += len(item)
    payload = b"".join(encoded)
    while len(payload) % 4:
        payload += b"\x00"
    header_size = 28
    strings_start = header_size + len(offsets) * 4
    size = strings_start + len(payload)
    header = struct.pack(
        "<HHIIIIII",
        0x0001,
        header_size,
        size,
        len(strings),
        0,
        0x00000100,
        strings_start,
        0,
    )
    return header + b"".join(struct.pack("<I", offset) for offset in offsets) + payload


def _start_element(strings: dict[str, int], name: str, attributes: list[tuple[str, str]]) -> bytes:
    node_header_size = 16
    attr_ext_size = 20
    attribute_size = 20
    chunk_size = node_header_size + attr_ext_size + attribute_size * len(attributes)
    node = struct.pack("<HHIII", 0x0102, node_header_size, chunk_size, 1, NO_INDEX)
    extension = struct.pack(
        "<IIHHHHHH",
        NO_INDEX,
        strings[name],
        attr_ext_size,
        attribute_size,
        len(attributes),
        0,
        0,
        0,
    )
    attrs = []
    for attribute_name, value in attributes:
        attrs.append(
            struct.pack(
                "<IIIHBBI",
                NO_INDEX,
                strings[attribute_name],
                strings[value],
                8,
                0,
                0x03,
                strings[value],
            )
        )
    return node + extension + b"".join(attrs)


def build_manifest(permissions: list[str]) -> bytes:
    values = [
        "manifest",
        "package",
        "com.nothing.camera",
        "uses-permission",
        "name",
        *permissions,
    ]
    strings = list(dict.fromkeys(values))
    indexes = {value: index for index, value in enumerate(strings)}
    chunks = [
        _string_pool(strings),
        _start_element(indexes, "manifest", [("package", "com.nothing.camera")]),
    ]
    chunks.extend(
        _start_element(indexes, "uses-permission", [("name", permission)])
        for permission in permissions
    )
    body = b"".join(chunks)
    return struct.pack("<HHI", 0x0003, 8, 8 + len(body)) + body


class AndroidBinaryXmlTest(unittest.TestCase):
    def test_extracts_package_and_permissions_in_order(self) -> None:
        manifest = build_manifest(
            [
                "android.permission.CAMERA",
                "android.permission.SYSTEM_CAMERA",
                "android.permission.CAMERA",
            ]
        )

        summary = parse_manifest(manifest)

        self.assertEqual("com.nothing.camera", summary.package_name)
        self.assertEqual(
            (
                "android.permission.CAMERA",
                "android.permission.SYSTEM_CAMERA",
            ),
            summary.uses_permissions,
        )

    def test_reads_manifest_from_apk(self) -> None:
        manifest = build_manifest(["android.permission.SYSTEM_CAMERA"])
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "camera.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("AndroidManifest.xml", manifest)

            loaded, source_kind = read_manifest_input(apk)

        self.assertEqual("apk", source_kind)
        self.assertEqual(manifest, loaded)

    def test_cli_reports_evidence_boundary_and_expected_permission(self) -> None:
        manifest = build_manifest(
            ["android.permission.CAMERA", "android.permission.SYSTEM_CAMERA"]
        )
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "AndroidManifest.xml"
            report_path = Path(directory) / "report.json"
            manifest_path.write_bytes(manifest)
            result = subprocess.run(
                [
                    sys.executable,
                    str(APK_TOOLS / "extract-manifest-permissions.py"),
                    str(manifest_path),
                    "--json",
                    str(report_path),
                    "--expect-permission",
                    "android.permission.SYSTEM_CAMERA",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(report["requested_system_camera"])
        self.assertEqual([], report["missing_expected_permissions"])
        self.assertIn("does not prove", report["evidence_boundary"]["unknown"])

    def test_cli_fails_when_expected_permission_is_missing(self) -> None:
        manifest = build_manifest(["android.permission.CAMERA"])
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "AndroidManifest.xml"
            manifest_path.write_bytes(manifest)
            result = subprocess.run(
                [
                    sys.executable,
                    str(APK_TOOLS / "extract-manifest-permissions.py"),
                    str(manifest_path),
                    "--expect-permission",
                    "android.permission.SYSTEM_CAMERA",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(1, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual(
            ["android.permission.SYSTEM_CAMERA"],
            report["missing_expected_permissions"],
        )

    def test_rejects_truncated_variable_length_prefixes(self) -> None:
        with self.assertRaises(BinaryXmlError):
            _read_length8(b"\x80", 0, 1)
        with self.assertRaises(BinaryXmlError):
            _read_length16(b"\x00\x80", 0, 2)

    def test_rejects_plain_text_xml(self) -> None:
        with self.assertRaises(BinaryXmlError):
            parse_manifest(b"<manifest />")


if __name__ == "__main__":
    unittest.main()
