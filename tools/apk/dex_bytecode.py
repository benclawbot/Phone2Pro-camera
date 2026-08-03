#!/usr/bin/env python3
"""Minimal bounds-checked Android DEX structures used by local analyzers."""
from __future__ import annotations
import dataclasses
import struct
from typing import Iterator, Sequence

class DexFormatError(ValueError):
    pass

@dataclasses.dataclass(frozen=True)
class MethodRef:
    class_descriptor: str
    name: str
    descriptor: str

    @property
    def key(self) -> str:
        return f'{self.class_descriptor}->{self.name}{self.descriptor}'

    def to_json(self) -> dict[str, str]:
        return {'classDescriptor': self.class_descriptor, 'name': self.name, 'descriptor': self.descriptor, 'key': self.key}

@dataclasses.dataclass
class DefinedMethod:
    dex_name: str
    method_index: int
    ref: MethodRef
    access_flags: int
    code_offset: int
    string_indexes: list[int]
    invoked_method_indexes: list[int]

class DexReader:

    def __init__(self, data: bytes, name: str) -> None:
        self.data = data
        self.name = name
        if len(data) < 112 or not data.startswith(b'dex\n'):
            raise DexFormatError(f'{name}: not a DEX file')
        self.file_size = self.u32(32)
        self.header_size = self.u32(36)
        if self.header_size != 112:
            raise DexFormatError(f'{name}: unsupported header size {self.header_size}')
        if self.file_size > len(data):
            raise DexFormatError(f'{name}: declared file size {self.file_size} exceeds input {len(data)}')
        self.string_ids_size = self.u32(56)
        self.string_ids_off = self.u32(60)
        self.type_ids_size = self.u32(64)
        self.type_ids_off = self.u32(68)
        self.proto_ids_size = self.u32(72)
        self.proto_ids_off = self.u32(76)
        self.method_ids_size = self.u32(88)
        self.method_ids_off = self.u32(92)
        self.class_defs_size = self.u32(96)
        self.class_defs_off = self.u32(100)
        self._check_table(self.string_ids_off, self.string_ids_size, 4, 'string_ids')
        self._check_table(self.type_ids_off, self.type_ids_size, 4, 'type_ids')
        self._check_table(self.proto_ids_off, self.proto_ids_size, 12, 'proto_ids')
        self._check_table(self.method_ids_off, self.method_ids_size, 8, 'method_ids')
        self._check_table(self.class_defs_off, self.class_defs_size, 32, 'class_defs')
        self.strings = [self._read_string(index) for index in range(self.string_ids_size)]
        self.types = [self._read_type(index) for index in range(self.type_ids_size)]
        self.protos = [self._read_proto(index) for index in range(self.proto_ids_size)]
        self.methods = [self._read_method(index) for index in range(self.method_ids_size)]

    def _check_range(self, offset: int, size: int, label: str) -> None:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise DexFormatError(f'{self.name}: {label} range {offset:#x}+{size:#x} is out of bounds')

    def _check_table(self, offset: int, count: int, item_size: int, label: str) -> None:
        if count == 0:
            return
        if offset == 0:
            raise DexFormatError(f'{self.name}: {label} has items but a zero offset')
        self._check_range(offset, count * item_size, label)

    def u16(self, offset: int) -> int:
        self._check_range(offset, 2, 'u16')
        return struct.unpack_from('<H', self.data, offset)[0]

    def u32(self, offset: int) -> int:
        self._check_range(offset, 4, 'u32')
        return struct.unpack_from('<I', self.data, offset)[0]

    def uleb128(self, offset: int) -> tuple[int, int]:
        result = 0
        shift = 0
        cursor = offset
        for _ in range(5):
            self._check_range(cursor, 1, 'uleb128')
            byte = self.data[cursor]
            cursor += 1
            result |= (byte & 127) << shift
            if byte & 128 == 0:
                return (result, cursor)
            shift += 7
        raise DexFormatError(f'{self.name}: malformed uleb128 at {offset:#x}')

    def _read_string(self, index: int) -> str:
        if not 0 <= index < self.string_ids_size:
            raise DexFormatError(f'{self.name}: invalid string index {index}')
        data_offset = self.u32(self.string_ids_off + index * 4)
        _, cursor = self.uleb128(data_offset)
        end = self.data.find(b'\x00', cursor)
        if end < 0:
            raise DexFormatError(f'{self.name}: unterminated string at {data_offset:#x}')
        encoded = self.data[cursor:end].replace(b'\xc0\x80', b'\x00')
        return encoded.decode('utf-8', errors='replace')

    def _read_type(self, index: int) -> str:
        descriptor_index = self.u32(self.type_ids_off + index * 4)
        if not 0 <= descriptor_index < len(self.strings):
            raise DexFormatError(f'{self.name}: invalid type descriptor index')
        return self.strings[descriptor_index]

    def _read_type_list(self, offset: int) -> list[str]:
        if offset == 0:
            return []
        size = self.u32(offset)
        self._check_range(offset + 4, size * 2, 'type_list')
        result: list[str] = []
        for item in range(size):
            type_index = self.u16(offset + 4 + item * 2)
            if not 0 <= type_index < len(self.types):
                raise DexFormatError(f'{self.name}: invalid type_list index')
            result.append(self.types[type_index])
        return result

    def _read_proto(self, index: int) -> str:
        offset = self.proto_ids_off + index * 12
        return_type_index = self.u32(offset + 4)
        parameters_offset = self.u32(offset + 8)
        if not 0 <= return_type_index < len(self.types):
            raise DexFormatError(f'{self.name}: invalid proto return type')
        parameters = ''.join(self._read_type_list(parameters_offset))
        return f'({parameters}){self.types[return_type_index]}'

    def _read_method(self, index: int) -> MethodRef:
        offset = self.method_ids_off + index * 8
        class_index = self.u16(offset)
        proto_index = self.u16(offset + 2)
        name_index = self.u32(offset + 4)
        if not 0 <= class_index < len(self.types):
            raise DexFormatError(f'{self.name}: invalid method class index')
        if not 0 <= proto_index < len(self.protos):
            raise DexFormatError(f'{self.name}: invalid method proto index')
        if not 0 <= name_index < len(self.strings):
            raise DexFormatError(f'{self.name}: invalid method name index')
        return MethodRef(self.types[class_index], self.strings[name_index], self.protos[proto_index])

    def defined_methods(self) -> Iterator[DefinedMethod]:
        for class_number in range(self.class_defs_size):
            class_offset = self.class_defs_off + class_number * 32
            class_data_offset = self.u32(class_offset + 24)
            if class_data_offset == 0:
                continue
            yield from self._class_data_methods(class_data_offset)

    def _class_data_methods(self, offset: int) -> Iterator[DefinedMethod]:
        static_fields_size, cursor = self.uleb128(offset)
        instance_fields_size, cursor = self.uleb128(cursor)
        direct_methods_size, cursor = self.uleb128(cursor)
        virtual_methods_size, cursor = self.uleb128(cursor)
        for _ in range(static_fields_size + instance_fields_size):
            _, cursor = self.uleb128(cursor)
            _, cursor = self.uleb128(cursor)
        for method_count in (direct_methods_size, virtual_methods_size):
            method_index = 0
            for _ in range(method_count):
                method_diff, cursor = self.uleb128(cursor)
                access_flags, cursor = self.uleb128(cursor)
                code_offset, cursor = self.uleb128(cursor)
                method_index += method_diff
                if not 0 <= method_index < len(self.methods):
                    raise DexFormatError(f'{self.name}: encoded method index out of range')
                string_indexes: list[int] = []
                invoked_indexes: list[int] = []
                if code_offset:
                    string_indexes, invoked_indexes = self._code_references(code_offset)
                yield DefinedMethod(dex_name=self.name, method_index=method_index, ref=self.methods[method_index], access_flags=access_flags, code_offset=code_offset, string_indexes=string_indexes, invoked_method_indexes=invoked_indexes)

    def _code_references(self, offset: int) -> tuple[list[int], list[int]]:
        self._check_range(offset, 16, 'code_item')
        instruction_count = self.u32(offset + 12)
        instruction_offset = offset + 16
        self._check_range(instruction_offset, instruction_count * 2, 'code instructions')
        instructions = list(struct.unpack_from(f'<{instruction_count}H', self.data, instruction_offset))
        return decode_code_references(instructions, string_count=len(self.strings), method_count=len(self.methods))

def instruction_width(instructions: Sequence[int], index: int) -> int:
    unit = instructions[index]
    opcode = unit & 255
    if opcode == 0:
        payload_type = unit >> 8
        if payload_type == 1:
            if index + 1 >= len(instructions):
                return 1
            return 4 + instructions[index + 1] * 2
        if payload_type == 2:
            if index + 1 >= len(instructions):
                return 1
            return 2 + instructions[index + 1] * 4
        if payload_type == 3:
            if index + 3 >= len(instructions):
                return 1
            element_width = instructions[index + 1]
            element_count = instructions[index + 2] | instructions[index + 3] << 16
            return 4 + (element_width * element_count + 1) // 2
        return 1
    if opcode == 24:
        return 5
    if opcode in {250, 251}:
        return 4
    if opcode in {3, 6, 9, 20, 23, 27, 36, 37, 38, 42, 43, 44, *range(110, 115), *range(116, 121), 252, 253}:
        return 3
    if opcode in {2, 5, 8, 19, 21, 22, 25, 26, 28, 31, 32, 34, 35, 41, *range(45, 62), *range(68, 110), *range(144, 176), *range(208, 227), 254, 255}:
        return 2
    return 1

def decode_code_references(instructions: Sequence[int], *, string_count: int, method_count: int) -> tuple[list[int], list[int]]:
    strings: list[int] = []
    methods: list[int] = []
    cursor = 0
    while cursor < len(instructions):
        unit = instructions[cursor]
        opcode = unit & 255
        width = instruction_width(instructions, cursor)
        if width <= 0 or cursor + width > len(instructions):
            break
        if opcode == 26 and width >= 2:
            string_index = instructions[cursor + 1]
            if 0 <= string_index < string_count:
                strings.append(string_index)
        elif opcode == 27 and width >= 3:
            string_index = instructions[cursor + 1] | instructions[cursor + 2] << 16
            if 0 <= string_index < string_count:
                strings.append(string_index)
        elif opcode in {*range(110, 115), *range(116, 121), 250, 251}:
            if width >= 2:
                method_index = instructions[cursor + 1]
                if 0 <= method_index < method_count:
                    methods.append(method_index)
        cursor += width
    return (list(dict.fromkeys(strings)), list(dict.fromkeys(methods)))
