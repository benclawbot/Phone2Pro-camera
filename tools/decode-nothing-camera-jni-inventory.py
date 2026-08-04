#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, json, pathlib, zlib


def decode(index_path: pathlib.Path):
    index = json.loads(index_path.read_text(encoding="utf-8"))
    base = index_path.parent
    encoded = "".join(
        (base / item["path"]).read_text(encoding="ascii").strip()
        for item in index["encoding"]["chunks"]
    )
    return json.loads(zlib.decompress(base64.b64decode(encoded, validate=True)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "index",
        type=pathlib.Path,
        nargs="?",
        default=pathlib.Path("data/apk/nothing-camera-jni/index.v1.json"),
    )
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    text = json.dumps(decode(args.index), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
