#!/usr/bin/env python3
"""Compatibility shim for the repository's existing Frida CLI invocation."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
from collections.abc import Sequence


def load_runner():
    configured = os.environ.get("P2P_FRIDA_RUNNER")
    path = pathlib.Path(configured) if configured else pathlib.Path(__file__).with_name(
        "run-frida-cli-observer.py"
    )
    spec = importlib.util.spec_from_file_location("p2p_frida_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load durable Frida runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_existing_invocation(arguments: Sequence[str]) -> dict[str, object]:
    if not arguments:
        raise ValueError("missing Frida device selector")
    device_arg = arguments[0]
    package: str | None = None
    script: pathlib.Path | None = None
    output: pathlib.Path | None = None
    passthrough: list[str] = []
    index = 1
    while index < len(arguments):
        value = arguments[index]
        if value in {"-f", "--file"}:
            if index + 1 >= len(arguments):
                raise ValueError(f"{value} requires a package")
            package = arguments[index + 1]
            index += 2
        elif value in {"-l", "--load"}:
            if index + 1 >= len(arguments):
                raise ValueError(f"{value} requires a script")
            script = pathlib.Path(arguments[index + 1])
            index += 2
        elif value in {"-o", "--output"}:
            if index + 1 >= len(arguments):
                raise ValueError(f"{value} requires a path")
            output = pathlib.Path(arguments[index + 1])
            index += 2
        else:
            passthrough.append(value)
            index += 1
    if package is None or not package.strip():
        raise ValueError("Frida invocation is missing -f PACKAGE")
    if script is None:
        raise ValueError("Frida invocation is missing -l SCRIPT")
    if output is None:
        raise ValueError("Frida invocation is missing -o OUTPUT")
    return {
        "deviceArg": device_arg,
        "package": package,
        "script": script,
        "output": output,
        "passthrough": passthrough,
    }


def main() -> int:
    try:
        parsed = parse_existing_invocation(sys.argv[1:])
        runner = load_runner()
        real_frida = os.environ.get("P2P_REAL_FRIDA")
        if not real_frida:
            raise ValueError("P2P_REAL_FRIDA is not set")
        script = parsed["script"]
        output = parsed["output"]
        assert isinstance(script, pathlib.Path)
        assert isinstance(output, pathlib.Path)
        command = runner.build_command(
            real_frida,
            str(parsed["deviceArg"]),
            str(parsed["package"]),
            script,
        )
        command.extend(str(value) for value in parsed["passthrough"])
        status = output.with_name("frida-runner-status.json")
        return runner.run_observer(command, output, status)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
