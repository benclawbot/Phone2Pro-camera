#!/usr/bin/env python3
"""Minimal, dependency-free reader for Android binary XML manifests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import struct
import zipfile

RES_STRING_POOL_TYPE = 0x0001
RES_XML_TYPE = 0x0003
RES_XML_START_ELEMENT_TYPE = 0x0102
UTF8_FLAG = 0x00000100
NO_INDEX = 0xFFFFFFFF
TYPE_STRING = 0x03


class BinaryXmlError(ValueError):
    """Raised when an Android binary XML document is malformed or unsupported."""


@dataclass(frozen=True)
class ManifestSummary:
    package_name: str | None
    uses_permissions: tuple[str, ...]


def _u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise BinaryXmlError(f"u16 read exceeds document at offset {offset}")
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise BinaryXmlError(f"u32 read exceeds document at offset {offset}")
    return struct.unpack_from("<I", data, offset)[0]


def _read_length8(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    if offset < 0 or offset >= limit or limit > len(data):
        raise BinaryXmlError("truncated UTF-8 string length")
    first = data[offset]
    if first & 0x80:
        if offset + 1 >= limit:
            raise BinaryXmlError("truncated UTF-8 string length")
        return ((first & 0x7F) << 8) | data[offset + 1], 2
    return first, 1


def _read_length16(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    if offset < 0 or offset + 2 > limit or limit > len(data):
        raise BinaryXmlError("truncated UTF-16 string length")
    first = struct.unpack_from("<H", data, offset)[0]
    if first & 0x8000:
        if offset + 4 > limit:
            raise BinaryXmlError("truncated UTF-16 string length")
        second = struct.unpack_from("<H", data, offset + 2)[0]
        return ((first & 0x7FFF) << 16) | second, 4
    return first, 2


class StringPool:
    def __init__(self, data: bytes, offset: int, header_size: int, chunk_size: int) -> None:
        if header_size < 28:
            raise BinaryXmlError("string-pool header is too small")
        self._data = data
        self._offset = offset
        self._end = offset + chunk_size
        self._string_count = _u32(data, offset + 8)
        self._style_count = _u32(data, offset + 12)
        self._flags = _u32(data, offset + 16)
        self._strings_start = _u32(data, offset + 20)
        self._styles_start = _u32(data, offset + 24)
        offsets_start = offset + header_size
        offsets_end = offsets_start + (self._string_count * 4)
        style_offsets_end = offsets_end + (self._style_count * 4)
        if style_offsets_end > self._end:
            raise BinaryXmlError("string-pool offsets exceed chunk bounds")
        self._offsets = tuple(
            _u32(data, offsets_start + index * 4)
            for index in range(self._string_count)
        )
        strings_absolute = offset + self._strings_start
        if strings_absolute > self._end:
            raise BinaryXmlError("string-pool string data starts outside chunk")
        self._strings_absolute = strings_absolute

    def get(self, index: int) -> str | None:
        if index == NO_INDEX:
            return None
        if index < 0 or index >= self._string_count:
            raise BinaryXmlError(f"string index {index} is outside pool")
        cursor = self._strings_absolute + self._offsets[index]
        if cursor >= self._end:
            raise BinaryXmlError("string offset exceeds pool bounds")
        if self._flags & UTF8_FLAG:
            _, consumed = _read_length8(self._data, cursor, self._end)
            cursor += consumed
            byte_length, consumed = _read_length8(self._data, cursor, self._end)
            cursor += consumed
            end = cursor + byte_length
            if end >= self._end:
                raise BinaryXmlError("UTF-8 string exceeds pool bounds")
            raw = self._data[cursor:end]
            if self._data[end] != 0:
                raise BinaryXmlError("UTF-8 string lacks NUL terminator")
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise BinaryXmlError("invalid UTF-8 string in pool") from error

        utf16_length, consumed = _read_length16(self._data, cursor, self._end)
        cursor += consumed
        end = cursor + utf16_length * 2
        if end + 2 > self._end:
            raise BinaryXmlError("UTF-16 string exceeds pool bounds")
        if self._data[end:end + 2] != b"\x00\x00":
            raise BinaryXmlError("UTF-16 string lacks NUL terminator")
        try:
            return self._data[cursor:end].decode("utf-16le")
        except UnicodeDecodeError as error:
            raise BinaryXmlError("invalid UTF-16 string in pool") from error


def _iter_chunks(data: bytes, start: int, end: int) -> Iterator[tuple[int, int, int, int]]:
    cursor = start
    while cursor < end:
        if cursor + 8 > end:
            raise BinaryXmlError("truncated chunk header")
        chunk_type = _u16(data, cursor)
        header_size = _u16(data, cursor + 2)
        chunk_size = _u32(data, cursor + 4)
        if header_size < 8 or chunk_size < header_size:
            raise BinaryXmlError(f"invalid chunk size at offset {cursor}")
        chunk_end = cursor + chunk_size
        if chunk_end > end:
            raise BinaryXmlError(f"chunk at offset {cursor} exceeds document")
        yield chunk_type, cursor, header_size, chunk_size
        cursor = chunk_end
    if cursor != end:
        raise BinaryXmlError("chunk stream does not end at document boundary")


def _typed_attribute_value(data: bytes, offset: int, strings: StringPool) -> str | None:
    value_size = _u16(data, offset)
    if value_size < 8:
        raise BinaryXmlError("attribute typed value is too small")
    data_type = data[offset + 3]
    value_data = _u32(data, offset + 4)
    if data_type == TYPE_STRING:
        return strings.get(value_data)
    return None


def parse_manifest(data: bytes) -> ManifestSummary:
    if len(data) < 8:
        raise BinaryXmlError("document is shorter than an XML header")
    file_type = _u16(data, 0)
    header_size = _u16(data, 2)
    file_size = _u32(data, 4)
    if file_type != RES_XML_TYPE:
        raise BinaryXmlError(
            f"expected Android binary XML type 0x{RES_XML_TYPE:04x}, got 0x{file_type:04x}"
        )
    if header_size < 8 or file_size < header_size or file_size > len(data):
        raise BinaryXmlError("invalid binary XML file header")

    chunks = list(_iter_chunks(data, header_size, file_size))
    string_chunk = next((chunk for chunk in chunks if chunk[0] == RES_STRING_POOL_TYPE), None)
    if string_chunk is None:
        raise BinaryXmlError("binary XML has no string pool")
    _, string_offset, string_header_size, string_chunk_size = string_chunk
    strings = StringPool(data, string_offset, string_header_size, string_chunk_size)

    package_name: str | None = None
    permissions: list[str] = []
    seen_permissions: set[str] = set()

    for chunk_type, offset, node_header_size, chunk_size in chunks:
        if chunk_type != RES_XML_START_ELEMENT_TYPE:
            continue
        if node_header_size < 16 or node_header_size + 20 > chunk_size:
            raise BinaryXmlError("start-element node header is malformed")
        extension = offset + node_header_size
        element_name = strings.get(_u32(data, extension + 4))
        attribute_start = _u16(data, extension + 8)
        attribute_size = _u16(data, extension + 10)
        attribute_count = _u16(data, extension + 12)
        if attribute_size < 20:
            raise BinaryXmlError("start-element attribute size is too small")
        attributes = extension + attribute_start
        if attributes < extension + 20:
            raise BinaryXmlError("start-element attributes overlap header")
        if attributes + attribute_count * attribute_size > offset + chunk_size:
            raise BinaryXmlError("start-element attributes exceed chunk bounds")

        values: dict[str, str] = {}
        for index in range(attribute_count):
            attribute = attributes + index * attribute_size
            name = strings.get(_u32(data, attribute + 4))
            raw_value_index = _u32(data, attribute + 8)
            value = strings.get(raw_value_index)
            if value is None:
                value = _typed_attribute_value(data, attribute + 12, strings)
            if name is not None and value is not None:
                values[name] = value

        if element_name == "manifest" and package_name is None:
            package_name = values.get("package")
        elif element_name in {"uses-permission", "uses-permission-sdk-23"}:
            permission = values.get("name")
            if permission and permission not in seen_permissions:
                seen_permissions.add(permission)
                permissions.append(permission)

    return ManifestSummary(package_name, tuple(permissions))


def read_manifest_input(path: str | Path) -> tuple[bytes, str]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            try:
                return archive.read("AndroidManifest.xml"), "apk"
            except KeyError as error:
                raise BinaryXmlError("APK contains no AndroidManifest.xml") from error
    return source.read_bytes(), "binary-xml"
