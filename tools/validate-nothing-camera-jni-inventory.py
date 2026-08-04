#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, pathlib, zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_APK_SHA256 = "f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea"


def inventory_dir(root: pathlib.Path = ROOT) -> pathlib.Path:
    return root / "data" / "apk" / "nothing-camera-jni"


def load(root: pathlib.Path = ROOT):
    base = inventory_dir(root)
    index = json.loads((base / "index.v1.json").read_text(encoding="utf-8"))
    encoded = "".join(
        (base / item["path"]).read_text(encoding="ascii").strip()
        for item in index["encoding"]["chunks"]
    )
    raw = zlib.decompress(base64.b64decode(encoded, validate=True))
    return index, json.loads(raw), raw


def validate(data, root: pathlib.Path = ROOT):
    index, obj, raw = data
    base = inventory_dir(root)
    summary = index["summary"]

    if index.get("issue") != 36 or index.get("status") != "STATIC_APK_JNI_AND_LIBRARY_INVENTORY":
        raise ValueError("issue/status drift")
    if index["apk"]["sha256"] != EXPECTED_APK_SHA256:
        raise ValueError("APK hash drift")

    encoding = index["encoding"]
    character_count = 0
    for item in encoding["chunks"]:
        payload = (base / item["path"]).read_bytes()
        if len(payload) != item["sizeBytes"]:
            raise ValueError(f"chunk size drift: {item['path']}")
        if hashlib.sha256(payload).hexdigest() != item["sha256"]:
            raise ValueError(f"chunk hash drift: {item['path']}")
        text = payload.decode("ascii").strip()
        if len(text) != item["characters"]:
            raise ValueError(f"chunk character drift: {item['path']}")
        character_count += len(text)
    if character_count != encoding["concatenatedCharacters"]:
        raise ValueError("encoded inventory length drift")
    if len(raw) != encoding["decodedSizeBytes"] or hashlib.sha256(raw).hexdigest() != encoding["decodedSha256"]:
        raise ValueError("decoded inventory integrity drift")

    for item in index["supplementalIntegrity"]:
        payload = (base / item["path"]).read_bytes()
        if len(payload) != item["sizeBytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
            raise ValueError(f"supplemental integrity drift: {item['path']}")
        rows = max(0, len(payload.decode("utf-8").splitlines()) - 1)
        if rows != item["rows"]:
            raise ValueError(f"supplemental row-count drift: {item['path']}")

    embedded = obj["index"]
    if embedded["summary"] != summary:
        raise ValueError("embedded summary drift")

    methods = obj["nativeMethods"]
    load_sites = obj["loadSites"]
    libraries = obj["libraries"]
    handles = obj["candidateNativeHandleFields"]
    callbacks = obj["candidateCallbackSurfaces"]

    if len(methods) != 794 or summary["nativeMethodCount"] != len(methods):
        raise ValueError("native method count drift")
    if len({item["javaClass"] for item in methods}) != 90 or summary["nativeOwningClassCount"] != 90:
        raise ValueError("native class count drift")
    if len(load_sites) != 69 or summary["loadSiteCount"] != 69:
        raise ValueError("load site count drift")
    if len(libraries) != 77 or summary["packagedArm64LibraryCount"] != 77:
        raise ValueError("library count drift")
    if sum(item["exportedJniSymbolCount"] for item in libraries) != 524 or summary["exportedJniSymbolCount"] != 524:
        raise ValueError("JNI export count drift")

    exact = sum(bool(item["exactLibraryMatches"]) for item in methods)
    if exact != summary["exactExportMatchedMethodCount"] or exact != 501:
        raise ValueError("exact ownership count drift")
    if summary["unresolvedNativeMethodCount"] != len(methods) - exact:
        raise ValueError("unresolved count drift")
    if len(handles) != summary["candidateNativeHandleFieldCount"] or len(callbacks) != summary["candidateCallbackSurfaceCount"]:
        raise ValueError("hook candidate count drift")
    if summary["parseErrorCount"] or index.get("parseErrors") or embedded.get("parseErrors"):
        raise ValueError("DEX parse errors present")

    if not any(item["priority"] == "HIGH_CAMERA_ROUTING_OR_ISP" for item in methods):
        raise ValueError("missing routing/ISP priority")
    if not any(item["registrationStatus"] == "DYNAMIC_REGISTRATION_CANDIDATE" for item in libraries):
        raise ValueError("missing dynamic registration candidates")

    for method in methods:
        if method["ownershipStatus"] == "EXACT_EXPORTED_JNI_SYMBOL_MATCH" and not method["exactLibraryMatches"]:
            raise ValueError("exact ownership without symbol evidence")
        for match in method["exactLibraryMatches"]:
            if not match["offset"].startswith("0x") or not match["symbol"].startswith("Java_"):
                raise ValueError("bad JNI symbol linkage")

    packaged = {item["path"] for item in libraries}
    for site in load_sites:
        for match in site["packagedMatches"]:
            if match["packagedLibrary"] not in packaged:
                raise ValueError("load-site library not packaged")

    if index["firmwareIssueLinks"] != {
        "libraryInventoryIssue": 48,
        "symbolRecoveryIssue": 49,
        "nativeHookIssue": 41,
    }:
        raise ValueError("firmware issue links drift")
    return True


def main() -> None:
    validate(load())
    print("validated Nothing Camera JNI inventory: 794 methods, 69 load sites, 77 libraries")


if __name__ == "__main__":
    main()
