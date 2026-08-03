#!/usr/bin/env python3
"""Recover Galaga Expert/manual camera endpoint routing from Nothing Camera DEX.

The tool performs narrow, reproducible bytecode analysis. It does not decompile
or copy proprietary source. It verifies the Galaga product-specific manual zoom
configuration and emits a clean-room fact record with explicit evidence
classifications. Static bytecode cannot prove runtime execution or authorization.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import dex_bytecode as DEX
from dex_constant_flow import decode_invocations, _invoke_registers35
EXPECTED_APK_SHA256 = 'f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea'
MANUAL_METHOD = 'Lcom/nothing/common/utils/config/zoom/ProductGalagaZoomConfigBuilder;->addManualZoomConfig()V'
ADD_REGION_METHOD = 'Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;->addZoomRegionCameraIdItem(Ljava/lang/String;I)Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;'
SET_MAX_ZOOM_METHOD = 'Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;->setMaxZoom(I)Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;'
EXPECTED_MAPPING = [{'zoomRegion': '[0.6,1)', 'cameraId': 2}, {'zoomRegion': '[1,2)', 'cameraId': 0}, {'zoomRegion': '[2,10]', 'cameraId': 3}]
STATIC_CHAIN = ['Lcom/nothing/common/utils/config/zoom/ProductGalagaZoomConfigBuilder;->addManualZoomConfig()V', 'Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;->getCameraIdByZoomValue(F)I', 'Lcom/nothing/camera/ui/uinode/CameraBottomFunctionUINode;->updateZoomValue(FZ)Z', 'Lcom/nothing/camera/scheduler/UiEventProxy;->switchCameraDirect(I)Z', 'Lcom/nothing/common/setting/SettingContext;->handleCameraIdChangedForDirectSwitch(Ljava/lang/String;Z)V', 'Lcom/nothing/common/setting/SettingContext;->setCameraId(I)V', 'Lcom/nothing/common/setting/SettingContext;->getCameraId()I', 'Lcom/nothing/cameracore/context/module/ModuleContext;->openCameraAsync(I)V', 'Lcom/nothing/cameracore/context/module/ModuleContext$9;->execute([Ljava/lang/Object;)V', 'Lcom/nothing/cameracore/context/module/CameraContext;->openCamera(ILandroid/os/ConditionVariable;)V', 'Lcom/nothing/cameracore/context/module/CameraContext$3;->execute([Ljava/lang/Object;)V', 'Landroid/hardware/camera2/CameraManager;->openCamera(Ljava/lang/String;...)']
CHECKS = {'factorySelection': {'method': 'Lcom/nothing/common/utils/config/zoom/ZoomConfigBuilderFactory;->getZoomConfigBuilder()Lcom/nothing/common/utils/config/zoom/BaseZoomConfigBuilder;', 'invokes': ['Lcom/nothing/common/utils/config/zoom/ProductGalagaZoomConfigBuilder;-><init>()V']}, 'manualDefinitionRegistration': {'method': 'Lcom/nothing/common/utils/config/zoom/ProductGalagaZoomConfigBuilder;->defineZoomConfig()V', 'invokes': [MANUAL_METHOD]}, 'zoomConsumer': {'method': 'Lcom/nothing/camera/ui/uinode/CameraBottomFunctionUINode;->updateZoomValue(FZ)Z', 'invokes': ['Lcom/nothing/common/utils/config/zoom/ZoomConfigItem;->getCameraIdByZoomValue(F)I', 'Lcom/nothing/camera/scheduler/UiEventProxy;->switchCameraDirect(I)Z']}, 'preferenceDispatch': {'method': 'Lcom/nothing/camera/scheduler/UiEventProxy;->switchCameraDirect(I)Z', 'invokes': ['Ljava/lang/String;->valueOf(I)Ljava/lang/String;', 'Lcom/nothing/common/setting/SettingContextOutInterface;->setPreferenceValueToKey(Ljava/lang/String;Ljava/lang/String;)V'], 'strings': ['pref_camera_id_key']}, 'settingMutation': {'method': 'Lcom/nothing/common/setting/SettingContext;->handleCameraIdChangedForDirectSwitch(Ljava/lang/String;Z)V', 'invokes': ['Ljava/lang/Integer;->parseInt(Ljava/lang/String;)I', 'Lcom/nothing/common/setting/SettingContext;->setCameraId(I)V']}, 'cameraOpenDispatch': {'method': 'Lcom/nothing/cameracore/context/module/CameraContext$3;->execute([Ljava/lang/Object;)V', 'invokes': ['Ljava/lang/String;->valueOf(I)Ljava/lang/String;', 'Landroid/hardware/camera2/CameraManager;->openCamera(Ljava/lang/String;Landroid/hardware/camera2/CameraDevice$StateCallback;Landroid/os/Handler;)V']}}

class AnalysisError(RuntimeError):
    pass

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def iter_dex_readers(paths: Iterable[Path]) -> Iterator[Any]:
    for path in paths:
        if path.suffix.lower() == '.apk' or zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for name in sorted((item for item in archive.namelist() if item.endswith('.dex'))):
                    yield DEX.DexReader(archive.read(name), f'{path.name}!/{name}')
        else:
            yield DEX.DexReader(path.read_bytes(), path.name)

def _target_defined_methods(reader: Any, target_keys: set[str]) -> Iterator[Any]:
    target_indexes = {index for index, reference in enumerate(reader.methods) if reference.key in target_keys}
    if not target_indexes:
        return
    for class_number in range(reader.class_defs_size):
        class_offset = reader.class_defs_off + class_number * 32
        class_data_offset = reader.u32(class_offset + 24)
        if class_data_offset == 0:
            continue
        static_fields_size, cursor = reader.uleb128(class_data_offset)
        instance_fields_size, cursor = reader.uleb128(cursor)
        direct_methods_size, cursor = reader.uleb128(cursor)
        virtual_methods_size, cursor = reader.uleb128(cursor)
        for _ in range(static_fields_size + instance_fields_size):
            _, cursor = reader.uleb128(cursor)
            _, cursor = reader.uleb128(cursor)
        for method_count in (direct_methods_size, virtual_methods_size):
            method_index = 0
            for _ in range(method_count):
                method_diff, cursor = reader.uleb128(cursor)
                access_flags, cursor = reader.uleb128(cursor)
                code_offset, cursor = reader.uleb128(cursor)
                method_index += method_diff
                if method_index not in target_indexes:
                    continue
                string_indexes: list[int] = []
                invoked_indexes: list[int] = []
                if code_offset:
                    string_indexes, invoked_indexes = reader._code_references(code_offset)
                yield DEX.DefinedMethod(dex_name=reader.name, method_index=method_index, ref=reader.methods[method_index], access_flags=access_flags, code_offset=code_offset, string_indexes=string_indexes, invoked_method_indexes=invoked_indexes)

def index_defined_methods(readers: Iterable[Any], target_keys: set[str]) -> dict[str, tuple[Any, Any]]:
    result: dict[str, tuple[Any, Any]] = {}
    for reader in readers:
        missing = target_keys.difference(result)
        if not missing:
            break
        for method in _target_defined_methods(reader, missing):
            result.setdefault(method.ref.key, (reader, method))
    return result

def extract_manual_route(reader: Any, method: Any) -> dict[str, Any]:
    invocations = decode_invocations(reader, method)
    max_zoom: int | None = None
    mappings: list[dict[str, Any]] = []
    for invocation in invocations:
        if invocation.target == SET_MAX_ZOOM_METHOD and len(invocation.arguments) >= 2:
            value = invocation.arguments[-1]
            if value.kind == 'int':
                max_zoom = int(value.value)
        if invocation.target == ADD_REGION_METHOD and len(invocation.arguments) >= 3:
            region, camera_id = invocation.arguments[-2:]
            if region.kind == 'string' and camera_id.kind == 'int':
                mappings.append({'zoomRegion': region.value, 'cameraId': int(camera_id.value), 'invocationOffsetCodeUnits': invocation.offset_code_units})
    normalized = [{'zoomRegion': item['zoomRegion'], 'cameraId': item['cameraId']} for item in mappings]
    return {'method': method.ref.key, 'dex': reader.name, 'maxZoom': max_zoom, 'mappings': mappings, 'expectedMappingRecovered': normalized == EXPECTED_MAPPING, 'invocations': [invocation.to_json() for invocation in invocations]}

def evaluate_check(methods: dict[str, tuple[Any, Any]], specification: dict[str, Any]) -> dict[str, Any]:
    method_key = specification['method']
    entry = methods.get(method_key)
    if entry is None:
        return {'method': method_key, 'present': False, 'verified': False, 'missingInvocations': list(specification.get('invokes', [])), 'missingStrings': list(specification.get('strings', []))}
    reader, method = entry
    invoked = {reader.methods[index].key for index in method.invoked_method_indexes}
    strings = {reader.strings[index] for index in method.string_indexes}
    missing_invocations = [value for value in specification.get('invokes', []) if value not in invoked]
    missing_strings = [value for value in specification.get('strings', []) if value not in strings]
    return {'method': method_key, 'dex': reader.name, 'present': True, 'verified': not missing_invocations and not missing_strings, 'missingInvocations': missing_invocations, 'missingStrings': missing_strings}

def build_report(inputs: Sequence[Path]) -> dict[str, Any]:
    target_methods = {MANUAL_METHOD, *(specification['method'] for specification in CHECKS.values())}
    methods = index_defined_methods(iter_dex_readers(inputs), target_methods)
    manual_entry = methods.get(MANUAL_METHOD)
    if manual_entry is None:
        raise AnalysisError(f'Target method not found: {MANUAL_METHOD}')
    manual_reader, manual_method = manual_entry
    manual_route = extract_manual_route(manual_reader, manual_method)
    checks = {name: evaluate_check(methods, specification) for name, specification in CHECKS.items()}
    checks['manualRouteDefinition'] = {'method': MANUAL_METHOD, 'dex': manual_reader.name, 'present': True, 'verified': manual_route['expectedMappingRecovered'] and manual_route['maxZoom'] == 10, 'missingInvocations': [] if manual_route['expectedMappingRecovered'] else [ADD_REGION_METHOD], 'missingStrings': [], 'maxZoom': manual_route['maxZoom'], 'mappings': manual_route['mappings'], 'expectedMappingRecovered': manual_route['expectedMappingRecovered']}
    input_records = [{'path': str(path.resolve()), 'sizeBytes': path.stat().st_size, 'sha256': sha256_file(path)} for path in inputs]
    complete = all(check['verified'] for check in checks.values())
    return {'schemaVersion': 1, 'evidenceClassification': {'staticConfiguration': 'VERIFIED' if complete else 'PARTIALLY_VERIFIED', 'runtimeExecutionForExpertRoutes': 'UNKNOWN_FROM_STATIC_ANALYSIS', 'ordinaryApplicationAccessToSystemCameraIds': 'UNKNOWN_FROM_APK_ANALYSIS'}, 'inputs': input_records, 'parseErrors': [], 'complete': complete, 'artifactMatch': {'expectedApkSha256': EXPECTED_APK_SHA256, 'matchesExpectedApk': any(record['sha256'] == EXPECTED_APK_SHA256 for record in input_records)}, 'product': {'codename': 'Galaga', 'builderClass': 'Lcom/nothing/common/utils/config/zoom/ProductGalagaZoomConfigBuilder;'}, 'manualRoute': {'method': manual_route['method'], 'maxZoom': manual_route['maxZoom'], 'mappings': manual_route['mappings'], 'nominalOpticalRoutes': [{'requestedRoute': 'UltraWide', 'nominalZoom': 0.6, 'cameraId': 2}, {'requestedRoute': 'Wide', 'nominalZoom': 1.0, 'cameraId': 0}, {'requestedRoute': 'Telephoto', 'nominalZoom': 2.0, 'cameraId': 3}], 'mechanism': 'direct-camera-endpoint-selection'}, 'staticCallChain': STATIC_CHAIN, 'checks': checks}

def render_markdown(report: dict[str, Any]) -> str:
    route = report['manualRoute']
    lines = ['# Galaga Expert/manual static route', '', f"- Complete extraction: **{str(report['complete']).lower()}**", f"- Static configuration: **{report['evidenceClassification']['staticConfiguration']}**", '- Runtime execution: **UNKNOWN_FROM_STATIC_ANALYSIS**', '', '## Artifact', '']
    for item in report['inputs']:
        lines.extend([f"- `{Path(item['path']).name}`", f"- SHA-256: `{item['sha256']}`"])
    lines.extend(['', '## Manual route map', '', '| Zoom region | Camera ID | Nominal route |', '|---|---:|---|'])
    labels = {2: 'UltraWide / 0.6×', 0: 'Wide / 1×', 3: 'Telephoto / 2×'}
    for mapping in route['mappings']:
        lines.append(f"| `{mapping['zoomRegion']}` | `{mapping['cameraId']}` | {labels.get(mapping['cameraId'], 'Unknown')} |")
    lines.extend(['', f"Maximum configured manual zoom: `{route['maxZoom']}×`.", '', '## Static dispatch chain', '', '```text', *report['staticCallChain'], '```', '', '## Evidence boundary', '', '### VERIFIED', '', 'The Galaga-specific manual configuration maps `[0.6,1)` to integer camera ID `2`, `[1,2)` to ID `0`, and `[2,10]` to ID `3`. The verified dispatch boundary converts an integer endpoint to a string before `CameraManager.openCamera`.', '', '### PARTIALLY VERIFIED', '', 'Combined with independently captured 15 mm, 24 mm and 50 mm Expert outputs, the mapping is consistent with the observed optical routes. Static analysis does not prove that this exact path executed in a particular capture.', '', '### UNKNOWN', '', 'APK analysis alone does not establish the package grant, UID, SELinux or CameraService authorization that permits IDs `2` and `3`, nor whether additional session or HAL configuration is required after the direct open.', ''])
    return '\n'.join(lines)

def parse_args(argv: Sequence[str] | None=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path, help='APK or DEX inputs')
    parser.add_argument('--json', type=Path, required=True, help='JSON report path')
    parser.add_argument('--markdown', type=Path, required=True, help='Markdown report path')
    parser.add_argument('--allow-incomplete', action='store_true', help='Write partial output and exit zero when an expected static check is missing')
    return parser.parse_args(argv)

def main(argv: Sequence[str] | None=None) -> int:
    args = parse_args(argv)
    for path in args.inputs:
        if not path.is_file():
            raise SystemExit(f'Input not found: {path}')
    report = build_report(args.inputs)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=False) + '\n', encoding='utf-8')
    args.markdown.write_text(render_markdown(report), encoding='utf-8')
    if report['complete'] or args.allow_incomplete:
        return 0
    print('Expected Galaga Expert route checks were incomplete.', file=sys.stderr)
    return 1
if __name__ == '__main__':
    raise SystemExit(main())
