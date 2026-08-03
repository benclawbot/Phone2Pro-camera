#!/usr/bin/env python3
"""Narrow constant-flow decoder for selected Dalvik methods."""
from __future__ import annotations
import dataclasses
import struct
from typing import Any
import dex_bytecode as DEX

@dataclasses.dataclass(frozen=True)
class RegisterValue:
    kind: str
    value: Any = None

    def to_json(self) -> dict[str, Any]:
        return {'kind': self.kind, 'value': self.value}
UNKNOWN = RegisterValue('unknown', None)

@dataclasses.dataclass(frozen=True)
class Invocation:
    offset_code_units: int
    target: str
    arguments: tuple[RegisterValue, ...]

    def to_json(self) -> dict[str, Any]:
        return {'offsetCodeUnits': self.offset_code_units, 'target': self.target, 'arguments': [argument.to_json() for argument in self.arguments]}

def code_units(reader: Any, method: Any) -> tuple[int, int, list[int]]:
    if method.code_offset == 0:
        return (0, 0, [])
    offset = method.code_offset
    register_count = reader.u16(offset)
    incoming_count = reader.u16(offset + 2)
    instruction_count = reader.u32(offset + 12)
    reader._check_range(offset + 16, instruction_count * 2, 'code instructions')
    instructions = list(struct.unpack_from(f'<{instruction_count}H', reader.data, offset + 16))
    return (register_count, incoming_count, instructions)

def _signed4(value: int) -> int:
    return value - 16 if value & 8 else value

def _signed16(value: int) -> int:
    return value - 65536 if value & 32768 else value

def _signed32(value: int) -> int:
    value &= 4294967295
    return value - (1 << 32) if value & 1 << 31 else value

def _invoke_registers35(unit: int, third: int) -> list[int]:
    count = unit >> 12 & 15
    fifth = unit >> 8 & 15
    values = [third & 15, third >> 4 & 15, third >> 8 & 15, third >> 12 & 15, fifth]
    return values[:count]

def _method_return_descriptor(target: Any) -> str:
    descriptor = target.descriptor
    return descriptor[descriptor.rfind(')') + 1:]

def decode_invocations(reader: Any, method: Any) -> list[Invocation]:
    register_count, _incoming_count, instructions = code_units(reader, method)
    registers = [UNKNOWN for _ in range(register_count)]
    last_result = UNKNOWN
    invocations: list[Invocation] = []
    cursor = 0
    while cursor < len(instructions):
        unit = instructions[cursor]
        opcode = unit & 255
        width = DEX.instruction_width(instructions, cursor)
        if width <= 0 or cursor + width > len(instructions):
            break
        if opcode in {1, 4, 7}:
            destination = unit >> 8 & 15
            source = unit >> 12 & 15
            registers[destination] = registers[source]
        elif opcode in {2, 5, 8}:
            destination = unit >> 8 & 255
            source = instructions[cursor + 1]
            registers[destination] = registers[source]
        elif opcode in {3, 6, 9}:
            destination = instructions[cursor + 1]
            source = instructions[cursor + 2]
            registers[destination] = registers[source]
        elif opcode in {10, 11, 12}:
            registers[unit >> 8 & 255] = last_result
            last_result = UNKNOWN
        elif opcode == 18:
            registers[unit >> 8 & 15] = RegisterValue('int', _signed4(unit >> 12 & 15))
        elif opcode == 19:
            registers[unit >> 8 & 255] = RegisterValue('int', _signed16(instructions[cursor + 1]))
        elif opcode == 20:
            raw = instructions[cursor + 1] | instructions[cursor + 2] << 16
            registers[unit >> 8 & 255] = RegisterValue('int', _signed32(raw))
        elif opcode == 26:
            registers[unit >> 8 & 255] = RegisterValue('string', reader.strings[instructions[cursor + 1]])
        elif opcode == 27:
            string_index = instructions[cursor + 1] | instructions[cursor + 2] << 16
            registers[unit >> 8 & 255] = RegisterValue('string', reader.strings[string_index])
        elif opcode == 34:
            registers[unit >> 8 & 255] = RegisterValue('object', reader.types[instructions[cursor + 1]])
        elif opcode in {*range(110, 115), *range(116, 121)}:
            target = reader.methods[instructions[cursor + 1]]
            if 110 <= opcode <= 114:
                register_indexes = _invoke_registers35(unit, instructions[cursor + 2])
            else:
                count = unit >> 8 & 255
                start = instructions[cursor + 2]
                register_indexes = list(range(start, start + count))
            arguments = tuple((registers[index] for index in register_indexes))
            invocations.append(Invocation(cursor, target.key, arguments))
            return_descriptor = _method_return_descriptor(target)
            if target.key == 'Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;' and arguments:
                last_result = arguments[0]
            elif return_descriptor.startswith('L') and arguments:
                last_result = arguments[0]
            else:
                last_result = UNKNOWN
        cursor += width
    return invocations
