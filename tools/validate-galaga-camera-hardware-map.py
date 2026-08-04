#!/usr/bin/env python3
"""Validate the source-backed Galaga camera hardware map."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

MAP_PATH = pathlib.Path("data/hardware/galaga-camera-hardware-map.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/GALAGA_CAMERA_HARDWARE_MAP.md")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
HEX_ADDR = re.compile(r"^0x[0-9a-f]{2}$")
ROUTES = {"front", "main", "ultrawide", "telephoto"}
POWER_COMPONENTS = {
    "camera-common-dovdd",
    "camera-tele-avdd",
    "camera-regulator-i2c3",
    "camera-regulator-i2c11",
}
INTERFACES = {
    "imgsensor-v4l2-subdev",
    "main-vcm-v4l2-subdev",
    "tele-vcm-v4l2-subdev",
    "camera-eeprom-char-dev",
    "flash-v4l2-subdev",
}
REQUIRED_SENSOR_IOCTLS = {
    "VIDIOC_MTK_G_SENSOR_INFO",
    "VIDIOC_MTK_G_CROP_BY_SCENARIO",
    "VIDIOC_MTK_G_PDAF_INFO_BY_SCENARIO",
    "VIDIOC_MTK_G_HDR_CAP",
    "VIDIOC_MTK_G_SEAMLESS_SCENARIO",
    "VIDIOC_MTK_S_VIDEO_FRAMERATE",
}


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def text_list(value: Any, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(text(item) for item in value)
        and len(value) == len(set(value))
    )


def load_map(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / MAP_PATH).read_text(encoding="utf-8"))


def validate(
    root: pathlib.Path,
    hardware_map: dict[str, Any] | None = None,
    document: str | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        hardware_map = hardware_map if hardware_map is not None else load_map(root)
        document = document if document is not None else (root / DOCUMENT_PATH).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot load hardware map: {error}"]

    if hardware_map.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    version = hardware_map.get("indexVersion")
    if not text(version):
        errors.append("indexVersion must be non-empty")
    elif f"**Index version:** {version}" not in document:
        errors.append("document index version does not match")
    if hardware_map.get("issue") != 52:
        errors.append("issue must be 52")

    device = hardware_map.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        if (device.get("model"), device.get("codename"), device.get("soc")) != ("A001", "Galaga", "MT6878"):
            errors.append("device identity is invalid")
        if device.get("observedBuild") != "2606151653":
            errors.append("observed build is invalid")
        evidence = device.get("fingerprintEvidence")
        if not text(evidence) or not (root / str(evidence)).is_file():
            errors.append("fingerprint evidence must exist")

    scope = hardware_map.get("sourceScope")
    if not isinstance(scope, dict):
        errors.append("sourceScope must be an object")
        scope = {}
    if scope.get("freshness") != "BUILD_MISMATCH" or not text(scope.get("mismatchNotes")):
        errors.append("sourceScope must preserve the build mismatch")
    repositories = scope.get("repositories")
    if not isinstance(repositories, list) or len(repositories) != 3:
        errors.append("sourceScope must contain three repositories")
        repositories = []
    repo_ids: set[str] = set()
    for index, repository in enumerate(repositories):
        prefix = f"sourceScope.repositories[{index}]"
        if not isinstance(repository, dict):
            errors.append(f"{prefix} must be an object")
            continue
        repo_id = repository.get("id")
        if not text(repo_id) or repo_id in repo_ids:
            errors.append(f"{prefix}.id must be unique")
        else:
            repo_ids.add(str(repo_id))
        if not text(repository.get("repository")):
            errors.append(f"{prefix}.repository must be non-empty")
        if not isinstance(repository.get("commit"), str) or not SHA40.fullmatch(repository["commit"]):
            errors.append(f"{prefix}.commit must be a full SHA")
    confidence = hardware_map.get("confidenceVocabulary")
    if not text_list(confidence):
        errors.append("confidenceVocabulary must be unique and non-empty")
        confidence = []

    route_records = hardware_map.get("routes")
    route_ids: set[str] = set()
    csi_ports: set[int] = set()
    sensor_addresses: set[tuple[str, str]] = set()
    referenced_rails: set[str] = set()
    if not isinstance(route_records, list) or len(route_records) != 4:
        errors.append("routes must contain four records")
        route_records = []
    for index, route in enumerate(route_records):
        prefix = f"routes[{index}]"
        if not isinstance(route, dict):
            errors.append(f"{prefix} must be an object")
            continue
        route_id = route.get("id")
        if route_id not in ROUTES or route_id in route_ids:
            errors.append(f"{prefix}.id is invalid")
            continue
        route_ids.add(str(route_id))
        if f"`{route_id}`" not in document:
            errors.append(f"document is missing route {route_id}")
        if route.get("status") != "okay" or route.get("topologyConfidence") != "SOURCE_CONFIRMED_TOPOLOGY":
            errors.append(f"{prefix} topology status is invalid")

        i2c = route.get("i2c")
        if not isinstance(i2c, dict):
            errors.append(f"{prefix}.i2c must be an object")
        else:
            controller = i2c.get("controller")
            address = i2c.get("address7bitHex")
            if not text(controller) or not isinstance(address, str) or not HEX_ADDR.fullmatch(address):
                errors.append(f"{prefix}.i2c is invalid")
            else:
                key = (str(controller), address)
                if key in sensor_addresses:
                    errors.append(f"duplicate sensor address {key}")
                sensor_addresses.add(key)
            if i2c.get("clockHz") != 1000000:
                errors.append(f"{prefix}.i2c clock must be 1 MHz")

        candidates = route.get("sensorCandidates")
        if not isinstance(candidates, list) or not candidates:
            errors.append(f"{prefix}.sensorCandidates must be non-empty")
            candidates = []
        for candidate in candidates:
            if not isinstance(candidate, dict) or not text(candidate.get("name")) or not text(candidate.get("sourcePath")):
                errors.append(f"{prefix} contains an invalid sensor candidate")
            elif candidate.get("confidence") != "SOURCE_CANDIDATE_DRIVER":
                errors.append(f"{prefix} sensor candidates must remain candidate-only")

        identity = route.get("shippedModuleIdentity")
        if not isinstance(identity, dict) or not text(identity.get("status")) or identity.get("status") == "CONFIRMED":
            errors.append(f"{prefix}.shippedModuleIdentity must remain unresolved")

        csi = route.get("csi")
        if not isinstance(csi, dict):
            errors.append(f"{prefix}.csi must be an object")
        else:
            port = csi.get("port")
            if not isinstance(port, int) or port not in range(4) or port in csi_ports:
                errors.append(f"{prefix}.csi.port must be unique from 0 to 3")
            else:
                csi_ports.add(port)
            for field in ("endpoint", "remoteEndpoint", "nvmemCell"):
                if not text(csi.get(field)):
                    errors.append(f"{prefix}.csi.{field} must be non-empty")

        for object_field in ("clock", "reset"):
            if not isinstance(route.get(object_field), dict):
                errors.append(f"{prefix}.{object_field} must be an object")
        power = route.get("power")
        if not isinstance(power, dict):
            errors.append(f"{prefix}.power must be an object")
        else:
            if power.get("sequenceStatus") != "CANDIDATE_DRIVER_DEFINED":
                errors.append(f"{prefix}.power sequence status is invalid")
            if not text_list(power.get("sequenceSourcePaths")) or not text_list(power.get("knownSequenceInputs")):
                errors.append(f"{prefix}.power sequence evidence is incomplete")
            if not text(power.get("unknowns")):
                errors.append(f"{prefix}.power unknowns must be explicit")
            for field in ("avdd", "dvdd", "dovdd", "afvdd"):
                rail = power.get(field)
                if rail is not None:
                    if not text(rail):
                        errors.append(f"{prefix}.power.{field} must be null or non-empty")
                    else:
                        referenced_rails.add(str(rail))

        eeprom = route.get("eeprom")
        if not isinstance(eeprom, dict) or not HEX_ADDR.fullmatch(str(eeprom.get("address7bitHex", ""))):
            errors.append(f"{prefix}.eeprom is invalid")
        elif eeprom.get("runtimeNodePattern") != "/dev/camera_eeprom*":
            errors.append(f"{prefix}.eeprom node pattern is invalid")

        ois = route.get("ois")
        if not isinstance(ois, dict) or ois.get("confidence") != "NOT_EVIDENCED":
            errors.append(f"{prefix}.ois must remain not evidenced")

        if route_id in {"main", "ultrawide", "telephoto"}:
            optical = route.get("opticalRouteEvidence")
            if not isinstance(optical, dict) or optical.get("confidence") != "RUNTIME_OBSERVED_OPTICAL_ROUTE":
                errors.append(f"{prefix}.opticalRouteEvidence is required")
            elif not (root / str(optical.get("evidence", ""))).is_file():
                errors.append(f"{prefix}.optical evidence file is missing")
        elif route.get("opticalRouteEvidence") is not None:
            errors.append("front optical evidence must remain null")
    if route_ids != ROUTES:
        errors.append(f"missing routes: {sorted(ROUTES - route_ids)}")

    components = hardware_map.get("powerComponents")
    component_ids: set[str] = set()
    provided_rails: set[str] = set()
    if not isinstance(components, list) or len(components) != 4:
        errors.append("powerComponents must contain four records")
        components = []
    for component in components:
        if not isinstance(component, dict) or component.get("id") not in POWER_COMPONENTS:
            errors.append("powerComponents contains an invalid record")
            continue
        component_ids.add(str(component["id"]))
        if component.get("type") == "FIXED_REGULATOR":
            provided_rails.add(str(component["id"]))
        elif component.get("type") == "ET5924_OR_DIO8016":
            outputs = component.get("outputs")
            if not isinstance(outputs, list) or len(outputs) != 4:
                errors.append(f"{component['id']} must contain four outputs")
                outputs = []
            for output in outputs:
                if isinstance(output, dict) and text(output.get("rail")):
                    provided_rails.add(str(output["rail"]))
                else:
                    errors.append(f"{component['id']} contains an invalid rail")
        else:
            errors.append(f"{component['id']} has an invalid type")
    if component_ids != POWER_COMPONENTS:
        errors.append(f"missing power components: {sorted(POWER_COMPONENTS - component_ids)}")
    if referenced_rails - provided_rails:
        errors.append(f"routes reference unmapped rails: {sorted(referenced_rails - provided_rails)}")

    flash = hardware_map.get("flash")
    if not isinstance(flash, dict):
        errors.append("flash must be an object")
    else:
        expected = ("i2c6", "0x63", 2, 39, 2)
        actual = (
            flash.get("controller"),
            flash.get("address7bitHex"),
            flash.get("channels"),
            flash.get("hwenGpio"),
            flash.get("coolingCells"),
        )
        if actual != expected:
            errors.append("flash topology is invalid")
        if not text_list(flash.get("compatibleCandidates")) or not text_list(flash.get("driverPaths")):
            errors.append("flash source candidates are incomplete")
        if flash.get("shippedControllerIdentity") != "UNKNOWN":
            errors.append("flash shipped identity must remain unknown")

    interfaces = hardware_map.get("kernelInterfaces")
    interface_ids: set[str] = set()
    if not isinstance(interfaces, list) or len(interfaces) != 5:
        errors.append("kernelInterfaces must contain five records")
        interfaces = []
    for interface in interfaces:
        if not isinstance(interface, dict) or interface.get("id") not in INTERFACES:
            errors.append("kernelInterfaces contains an invalid record")
            continue
        interface_id = str(interface["id"])
        interface_ids.add(interface_id)
        if interface.get("nodeStability") not in {"DYNAMIC_ENUMERATION_REQUIRED", "INSTANCE_INDEX_DYNAMIC"}:
            errors.append(f"{interface_id} must retain dynamic node enumeration")
        if not text(interface.get("accessBoundary")):
            errors.append(f"{interface_id} must state its access boundary")
        if not isinstance(interface.get("sourcePaths"), list):
            errors.append(f"{interface_id}.sourcePaths must be a list")
        if not isinstance(interface.get("standardControls"), list) or not isinstance(interface.get("privateIoctls"), list):
            errors.append(f"{interface_id} controls must be lists")
        if interface_id == "imgsensor-v4l2-subdev":
            missing = REQUIRED_SENSOR_IOCTLS - set(interface.get("privateIoctls", []))
            if missing:
                errors.append(f"sensor interface is missing ioctls: {sorted(missing)}")
        if interface_id == "main-vcm-v4l2-subdev":
            if "V4L2_CID_FOCUS_ABSOLUTE" not in interface.get("standardControls", []):
                errors.append("main VCM focus control is missing")
            if set(interface.get("privateIoctls", [])) != {"VCM_IOC_POWER_ON", "VCM_IOC_POWER_OFF"}:
                errors.append("main VCM power commands are invalid")
        if interface_id == "camera-eeprom-char-dev":
            if interface.get("nodePattern") != "/dev/camera_eeprom*" or "CAM_CALIOC_S_SENSOR_INFO" not in interface.get("privateIoctls", []):
                errors.append("EEPROM interface is invalid")
    if interface_ids != INTERFACES:
        errors.append(f"missing kernel interfaces: {sorted(INTERFACES - interface_ids)}")

    consequences = hardware_map.get("replacementAppConsequences")
    if not text_list(consequences) or len(consequences) < 5:
        errors.append("replacementAppConsequences must contain at least five items")

    gaps = hardware_map.get("knownGaps")
    if not isinstance(gaps, list) or len(gaps) < 4:
        errors.append("knownGaps must contain at least four records")
        gaps = []
    for gap in gaps:
        if not isinstance(gap, dict) or not text(gap.get("id")):
            errors.append("knownGaps contains an invalid record")
            continue
        if f"`{gap['id']}`" not in document:
            errors.append(f"document is missing gap {gap['id']}")
        if gap.get("status") != "OPEN" or not text(gap.get("description")):
            errors.append(f"{gap['id']} must remain an open described gap")

    non_claims = hardware_map.get("nonClaims")
    if not isinstance(non_claims, list) or len(non_claims) < 6 or not all(text(item) for item in non_claims):
        errors.append("nonClaims must contain six explicit limitations")

    maintenance = hardware_map.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        if maintenance.get("document") != str(DOCUMENT_PATH):
            errors.append("maintenance.document is incorrect")
        if maintenance.get("validationTool") != "tools/validate-galaga-camera-hardware-map.py":
            errors.append("maintenance.validationTool is incorrect")
        if not text_list(maintenance.get("updateTriggers")):
            errors.append("maintenance.updateTriggers must be unique and non-empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Galaga camera hardware map is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
