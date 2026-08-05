#!/usr/bin/env python3
"""Run an interactive Frida CLI observer with durable cross-platform logging."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import queue
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from typing import Any, TextIO


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def build_command(
    frida_command: str,
    device_arg: str,
    package: str,
    script: pathlib.Path,
) -> list[str]:
    if not frida_command.strip():
        raise ValueError("Frida command must be non-empty")
    if not device_arg.strip():
        raise ValueError("Frida device argument must be non-empty")
    if not package.strip():
        raise ValueError("package must be non-empty")
    if not script.is_file():
        raise ValueError(f"Frida script not found: {script}")
    return [frida_command, device_arg, "-f", package, "-l", str(script)]


def _reader_thread(
    stream: TextIO,
    output: TextIO,
    mirror: TextIO | None,
    counters: dict[str, int],
) -> None:
    try:
        for line in iter(stream.readline, ""):
            output.write(line)
            output.flush()
            counters["lineCount"] += 1
            counters["outputBytes"] += len(line.encode("utf-8", errors="replace"))
            if mirror is not None:
                mirror.write(line)
                mirror.flush()
    finally:
        stream.close()


def _input_thread(done: queue.Queue[str], input_stream: TextIO) -> None:
    try:
        value = input_stream.readline()
    except (OSError, ValueError):
        value = ""
    done.put("eof" if value == "" else "enter")


def run_observer(
    command: Sequence[str],
    output_path: pathlib.Path,
    status_path: pathlib.Path,
    *,
    input_stream: TextIO = sys.stdin,
    mirror: TextIO | None = sys.stderr,
    popen: type[subprocess.Popen[str]] = subprocess.Popen,
    graceful_timeout_seconds: float = 15.0,
) -> int:
    if graceful_timeout_seconds <= 0:
        raise ValueError("graceful timeout must be positive")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    started_monotonic = time.monotonic()
    counters = {"lineCount": 0, "outputBytes": 0}
    completion_mode = "process-exited"
    forced_termination = False
    process: subprocess.Popen[str] | None = None
    reader: threading.Thread | None = None

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        with output_path.open("w", encoding="utf-8", newline="") as output:
            process = popen(
                list(command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                creationflags=creationflags,
            )
            if process.stdout is None or process.stdin is None:
                raise RuntimeError("Frida subprocess pipes were not created")
            reader = threading.Thread(
                target=_reader_thread,
                args=(process.stdout, output, mirror, counters),
                daemon=True,
            )
            reader.start()
            if mirror is not None:
                mirror.write(
                    "\nFrida observer started. Complete the assigned camera interaction, "
                    "exit Nothing Camera, then press Enter here to detach cleanly.\n\n"
                )
                mirror.flush()

            completion: queue.Queue[str] = queue.Queue(maxsize=1)
            input_reader = threading.Thread(
                target=_input_thread,
                args=(completion, input_stream),
                daemon=True,
            )
            input_reader.start()

            while process.poll() is None:
                try:
                    completion_mode = completion.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass
                break

            if process.poll() is None:
                try:
                    exit_status = process.wait(timeout=graceful_timeout_seconds)
                except subprocess.TimeoutExpired:
                    forced_termination = True
                    completion_mode += "-terminate-timeout"
                    process.terminate()
                    try:
                        exit_status = process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        completion_mode += "-kill-timeout"
                        process.kill()
                        exit_status = process.wait(timeout=5)
            else:
                exit_status = process.returncode

            if reader is not None:
                reader.join(timeout=5)
    except KeyboardInterrupt:
        completion_mode = "keyboard-interrupt"
        if process is not None and process.poll() is None:
            try:
                if process.stdin is not None:
                    process.stdin.close()
                exit_status = process.wait(timeout=graceful_timeout_seconds)
            except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                forced_termination = True
                process.terminate()
                exit_status = process.wait(timeout=5)
        else:
            exit_status = 130
    except OSError as error:
        completion_mode = "launch-error"
        exit_status = 127
        output_path.write_text(f"observer-launch-error: {error}\n", encoding="utf-8")
        counters["lineCount"] = 1
        counters["outputBytes"] = output_path.stat().st_size

    status: dict[str, Any] = {
        "schemaVersion": 1,
        "startedAtUtc": started_at,
        "completedAtUtc": utc_now(),
        "durationSeconds": round(time.monotonic() - started_monotonic, 3),
        "command": list(command),
        "processExitStatus": exit_status,
        "completionMode": completion_mode,
        "forcedTermination": forced_termination,
        **counters,
    }
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return int(exit_status)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frida-command", default="frida")
    parser.add_argument("--device-arg", default="-U")
    parser.add_argument("--package", required=True)
    parser.add_argument("--script", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--status", type=pathlib.Path, required=True)
    parser.add_argument("--graceful-timeout-seconds", type=float, default=15.0)
    args = parser.parse_args()

    try:
        command = build_command(
            args.frida_command, args.device_arg, args.package, args.script
        )
        return run_observer(
            command,
            args.output,
            args.status,
            graceful_timeout_seconds=args.graceful_timeout_seconds,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
